"""The client's data: customers, products and feedback in SQLite.

Rules that keep this safe and simple:
- Every query is fixed SQL with `?` placeholders. User text only ever fills a placeholder, so it
  can never change the query (ADR-004). The model never writes SQL.
- Money is whole paise (integers), never floats (ADR-010).
- The schema's CHECK rules reject impossible rows (rating 6, negative stock) even if a bug in the
  code above tried to write one.
"""

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SCHEMA = """
CREATE TABLE IF NOT EXISTS customers (
    customer_id        TEXT PRIMARY KEY,
    name               TEXT NOT NULL,
    email              TEXT NOT NULL UNIQUE COLLATE NOCASE,
    city               TEXT NOT NULL,
    age_group          TEXT NOT NULL,
    preferred_category TEXT NOT NULL,
    total_spend_paise  INTEGER NOT NULL CHECK (total_spend_paise >= 0),
    name_key           TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS products (
    product_id   TEXT PRIMARY KEY,
    code         TEXT NOT NULL UNIQUE,
    name         TEXT NOT NULL,
    brand        TEXT NOT NULL,
    category     TEXT NOT NULL,
    price_paise  INTEGER NOT NULL CHECK (price_paise > 0),
    stock_qty    INTEGER NOT NULL CHECK (stock_qty >= 0),
    search_key   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS feedback (
    feedback_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     TEXT REFERENCES customers (customer_id),
    conversation_id TEXT,
    rating          INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment         TEXT NOT NULL DEFAULT '',
    submitted_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS escalations (
    escalation_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id     TEXT REFERENCES customers (customer_id),
    conversation_id TEXT,
    reason          TEXT NOT NULL CHECK (reason IN ('user_request', 'refund_or_complaint',
                                                    'tool_failure', 'out_of_scope')),
    summary         TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
"""

ESCALATION_REASONS = ["user_request", "refund_or_complaint", "tool_failure", "out_of_scope"]

AgeGroup = Literal["18-24", "25-34", "35-44", "45-54", "55+"]

MAX_SEARCH_WORDS = 6  # longer queries are cut to their first six words


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Customer(Strict):
    customer_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    email: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
    city: str = Field(min_length=1)
    age_group: AgeGroup
    preferred_category: str = Field(min_length=1)
    total_spend_paise: int = Field(ge=0)


class Product(Strict):
    product_id: str = Field(min_length=1)
    code: str = Field(min_length=1)
    name: str = Field(min_length=1)
    brand: str = Field(min_length=1)
    category: str = Field(min_length=1)
    price_paise: int = Field(gt=0)
    stock_qty: int = Field(ge=0)


# ---- connection and schema ------------------------------------------------------------------


def connect(path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row  # read columns by name: row["price_paise"]
    conn.execute("PRAGMA foreign_keys = ON")  # SQLite leaves foreign keys off unless asked
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def normalise(text: str) -> str:
    """Lowercase and keep only letters and digits: "T-Shirt", "t shirt" and "TSHIRT" all give "tshirt".

    Dropping everything else also removes `%` and `_`, so search text can never act as a LIKE
    wildcard.
    """
    kept = []
    for char in text.lower():
        if char.isalnum():
            kept.append(char)
    return "".join(kept)


def count_rows(conn: sqlite3.Connection) -> dict[str, int]:
    counts = {}
    for table in ["customers", "products", "feedback"]:  # fixed names, never user input
        counts[table] = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    return counts


# ---- writing ---------------------------------------------------------------------------------


def upsert_customers(conn: sqlite3.Connection, customers: list[Customer]) -> None:
    """Insert each customer, or update it if the ID exists, so loading twice never duplicates."""
    sql = """
        INSERT INTO customers (customer_id, name, email, city, age_group, preferred_category,
                               total_spend_paise, name_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (customer_id) DO UPDATE SET
            name = excluded.name, email = excluded.email, city = excluded.city,
            age_group = excluded.age_group, preferred_category = excluded.preferred_category,
            total_spend_paise = excluded.total_spend_paise, name_key = excluded.name_key
    """
    for c in customers:
        name_key = normalise(c.name)
        values = (c.customer_id, c.name, c.email, c.city, c.age_group, c.preferred_category)
        conn.execute(sql, values + (c.total_spend_paise, name_key))
    conn.commit()


def upsert_products(conn: sqlite3.Connection, products: list[Product]) -> None:
    sql = """
        INSERT INTO products (product_id, code, name, brand, category, price_paise, stock_qty,
                              search_key)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (product_id) DO UPDATE SET
            code = excluded.code, name = excluded.name, brand = excluded.brand,
            category = excluded.category, price_paise = excluded.price_paise,
            stock_qty = excluded.stock_qty, search_key = excluded.search_key
    """
    for p in products:
        # One string with everything a shopper might type: code, name, brand and category.
        search_key = " ".join(
            [normalise(p.code), normalise(p.name), normalise(p.brand), normalise(p.category)]
        )
        values = (p.product_id, p.code, p.name, p.brand, p.category, p.price_paise, p.stock_qty, search_key)
        conn.execute(sql, values)
    conn.commit()


def add_feedback(
    conn: sqlite3.Connection,
    rating: int,
    comment: str = "",
    customer_id: str | None = None,
    conversation_id: str | None = None,
) -> int:
    """Save one feedback row with who and when, and return its ID."""
    submitted_at = datetime.now(UTC).isoformat(timespec="seconds")
    cursor = conn.execute(
        "INSERT INTO feedback (customer_id, conversation_id, rating, comment, submitted_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (customer_id, conversation_id, rating, comment, submitted_at),
    )
    conn.commit()
    return cursor.lastrowid


def add_escalation(
    conn: sqlite3.Connection,
    reason: str,
    summary: str,
    customer_id: str | None = None,
    conversation_id: str | None = None,
) -> int:
    """Save a handover to a human, and return its ID. `reason` must be one of ESCALATION_REASONS."""
    created_at = datetime.now(UTC).isoformat(timespec="seconds")
    cursor = conn.execute(
        "INSERT INTO escalations (customer_id, conversation_id, reason, summary, created_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (customer_id, conversation_id, reason, summary, created_at),
    )
    conn.commit()
    return cursor.lastrowid


# ---- reading ---------------------------------------------------------------------------------


def row_to_product(row: sqlite3.Row) -> Product:
    return Product(**{field: row[field] for field in Product.model_fields})


def row_to_customer(row: sqlite3.Row) -> Customer:
    return Customer(**{field: row[field] for field in Customer.model_fields})


def product_rank(product: Product, query_key: str) -> int:
    """Lower is better: exact code, then name starts with the query, then contains it, then the rest."""
    name_key = normalise(product.name)
    if normalise(product.code) == query_key:
        return 0
    if name_key.startswith(query_key):
        return 1
    if query_key in name_key:
        return 2
    return 3


def find_products(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[Product]:
    """Find products whose code, name, brand or category contain every word of the query.

    SQL does the broad filter (every word must appear); Python then ranks the matches.
    """
    words = []
    for word in query.split()[:MAX_SEARCH_WORDS]:
        key = normalise(word)
        if key:
            words.append(key)
    if not words:
        return []

    # One "search_key LIKE ?" per word. Only placeholders are added to the SQL text, never the words.
    conditions = " AND ".join(["search_key LIKE ?"] * len(words))
    params = [f"%{word}%" for word in words]
    rows = conn.execute(f"SELECT * FROM products WHERE {conditions} LIMIT 500", params).fetchall()

    query_key = "".join(words)
    matches = [row_to_product(row) for row in rows]
    matches.sort(key=lambda product: (product_rank(product, query_key), product.name))
    return matches[:limit]


def get_customer(conn: sqlite3.Connection, customer_id: str) -> Customer | None:
    """Exact lookup by ID (any case), used once a search has narrowed several matches to one."""
    row = conn.execute(
        "SELECT * FROM customers WHERE customer_id = ? COLLATE NOCASE", (customer_id.strip(),)
    ).fetchone()
    return row_to_customer(row) if row else None


def find_customers(conn: sqlite3.Connection, query: str, limit: int = 5) -> list[Customer]:
    """An exact email match (any case) wins; otherwise return customers whose name contains the query."""
    query = query.strip()
    if query == "":
        return []

    if "@" in query:
        row = conn.execute("SELECT * FROM customers WHERE email = ?", (query,)).fetchone()
        return [row_to_customer(row)] if row else []

    name_key = normalise(query)
    if name_key == "":
        return []
    rows = conn.execute(
        "SELECT * FROM customers WHERE name_key LIKE ? ORDER BY name LIMIT ?",
        (f"%{name_key}%", limit),
    ).fetchall()
    return [row_to_customer(row) for row in rows]
