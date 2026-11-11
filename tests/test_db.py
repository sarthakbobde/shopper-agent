"""Tests for db.py on a small in-memory database, independent of the seed files."""

import sqlite3
from datetime import datetime

import pytest

from shopper.db import (
    Customer,
    Product,
    add_feedback,
    connect,
    count_rows,
    create_schema,
    find_customers,
    find_products,
    normalise,
    upsert_customers,
    upsert_products,
)
from shopper.doctor import db_verdict


def product(pid, code, name, brand="Urbano", category="Men's Wear", price=129900, stock=10):
    return Product(product_id=pid, code=code, name=name, brand=brand, category=category,
                   price_paise=price, stock_qty=stock)  # fmt: skip


def customer(cid, name, email, spend=500000):
    return Customer(customer_id=cid, name=name, email=email, city="Mumbai", age_group="25-34",
                    preferred_category="Footwear", total_spend_paise=spend)  # fmt: skip


PRODUCTS = [
    product("P1", "SS-MEN-0001", "Blue Cotton T-Shirt"),
    product("P2", "SS-MEN-0002", "Red Denim Jeans", stock=0),
    product("P3", "SS-MEN-0003", "Blue Denim Jeans"),
    product("P4", "SS-MEN-0004", "White Formal Shirt"),
    product("P5", "SS-FTW-0001", "Blue Sneakers", brand="Northline", category="Footwear"),
]
CUSTOMERS = [
    customer("C1", "Priya Sharma", "priya.sharma@example.com"),
    customer("C2", "Rahul Shah", "rahul.shah@example.com"),
    customer("C3", "Priya Patel", "priya.patel@example.com"),
    customer("C4", "Arjun Iyer", "arjun.iyer@example.com"),
]


@pytest.fixture
def conn():
    conn = connect(":memory:")
    create_schema(conn)
    upsert_products(conn, PRODUCTS)
    upsert_customers(conn, CUSTOMERS)
    yield conn
    conn.close()


def names(items):
    return [item.name for item in items]


# ---- normalise -------------------------------------------------------------------------------


def test_normalise():
    assert normalise("T-Shirt") == "tshirt"
    assert normalise("t shirt") == "tshirt"
    assert normalise("TSHIRT") == "tshirt"
    assert normalise("100% cotton_blend") == "100cottonblend"  # LIKE wildcards are removed


# ---- products --------------------------------------------------------------------------------


def test_find_products_ignores_case_spaces_and_hyphens(conn):
    for query in ["t shirt", "T-SHIRT", "tshirt"]:
        assert names(find_products(conn, query))[0] == "Blue Cotton T-Shirt", query


def test_find_products_exact_code_comes_first(conn):
    assert names(find_products(conn, "ss-men-0004"))[0] == "White Formal Shirt"
    assert names(find_products(conn, "SS MEN 0004"))[0] == "White Formal Shirt"


def test_find_products_needs_every_word(conn):
    assert names(find_products(conn, "blue jeans")) == ["Blue Denim Jeans"]


def test_find_products_matches_brand_and_category(conn):
    assert names(find_products(conn, "northline")) == ["Blue Sneakers"]
    assert names(find_products(conn, "footwear blue")) == ["Blue Sneakers"]


def test_find_products_no_match_returns_empty(conn):
    assert find_products(conn, "saree") == []
    assert find_products(conn, "   ") == []
    assert find_products(conn, "---") == []


def test_find_products_respects_limit(conn):
    assert len(find_products(conn, "ss", limit=2)) == 2


def test_search_text_is_never_sql(conn):
    assert find_products(conn, "'; DROP TABLE products;--") == []
    assert find_customers(conn, "'; DROP TABLE customers;--") == []
    assert count_rows(conn)["products"] == 5
    assert count_rows(conn)["customers"] == 4


# ---- customers -------------------------------------------------------------------------------


def test_find_customers_by_email_any_case(conn):
    assert names(find_customers(conn, "PRIYA.SHARMA@EXAMPLE.COM")) == ["Priya Sharma"]
    assert find_customers(conn, "nobody@example.com") == []


def test_find_customers_by_partial_name(conn):
    assert set(names(find_customers(conn, "sha"))) == {"Priya Sharma", "Rahul Shah"}
    assert names(find_customers(conn, "priya")) == ["Priya Patel", "Priya Sharma"]  # sorted by name


# ---- feedback --------------------------------------------------------------------------------


def test_add_feedback_saves_who_and_when(conn):
    feedback_id = add_feedback(conn, 4, "Quick answer", customer_id="C1", conversation_id="conv-1")
    row = conn.execute("SELECT * FROM feedback WHERE feedback_id = ?", (feedback_id,)).fetchone()
    assert (row["rating"], row["comment"], row["customer_id"], row["conversation_id"]) == (
        4,
        "Quick answer",
        "C1",
        "conv-1",
    )
    assert datetime.fromisoformat(row["submitted_at"]).tzinfo is not None  # stored in UTC


def test_database_rejects_rating_6(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_feedback(conn, 6)


def test_feedback_for_an_unknown_customer_is_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        add_feedback(conn, 5, customer_id="C999")


# ---- upsert ------------------------------------------------------------------------------------


def test_upsert_twice_does_not_duplicate_and_updates(conn):
    changed = PRODUCTS[0].model_copy(update={"stock_qty": 0})
    upsert_products(conn, [changed])
    upsert_customers(conn, CUSTOMERS)
    assert count_rows(conn) == {"customers": 4, "products": 5, "feedback": 0}
    assert find_products(conn, "SS-MEN-0001")[0].stock_qty == 0


# ---- doctor ------------------------------------------------------------------------------------


def test_db_verdict():
    assert "shopper seed --client x" in db_verdict(None, "x")
    verdict = db_verdict({"customers": 50, "products": 200, "feedback": 0}, "x")
    assert verdict == "ok (50 customers, 200 products, 0 feedback)"
