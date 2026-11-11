"""Loads a client's seed CSVs into its SQLite database: `shopper seed`.

Every row is validated before anything is written, so a bad file fails with the line numbers to
fix instead of leaving a half-loaded database.
"""

import csv
from pathlib import Path

from pydantic import BaseModel, ValidationError

from shopper import paths
from shopper.db import (
    Customer,
    Product,
    connect,
    count_rows,
    create_schema,
    upsert_customers,
    upsert_products,
)
from shopper.errors import UserError

MAX_ERRORS_SHOWN = 10


def read_csv_rows(path: Path, model: type[BaseModel]) -> list:
    """Read a CSV and validate every row with `model` (Customer or Product)."""
    if not path.is_file():
        raise UserError(f"seed file not found: {path}")

    rows = []
    problems = []
    with open(path, encoding="utf-8", newline="") as f:
        # Line 1 is the header, so the first data row is line 2.
        for line_number, raw in enumerate(csv.DictReader(f), start=2):
            try:
                rows.append(model.model_validate(raw))
            except ValidationError as error:
                first = error.errors()[0]
                field = ".".join(str(part) for part in first["loc"]) or "row"
                problems.append(f"  line {line_number}: {field}: {first['msg']}")

    if problems:
        shown = "\n".join(problems[:MAX_ERRORS_SHOWN])
        more = len(problems) - MAX_ERRORS_SHOWN
        if more > 0:
            shown += f"\n  ... and {more} more"
        raise UserError(f"{path.name} has {len(problems)} bad rows:\n{shown}")
    return rows


def load_seed(client: str, db_path: Path | None = None, fresh: bool = False) -> dict[str, int]:
    """Create the schema and load the client's customers.csv and products.csv. Returns row counts."""
    seed_dir = paths.client_seed_dir(client)
    if db_path is None:
        db_path = paths.client_db_file(client)

    # Read and validate both files before touching the database.
    customers = read_csv_rows(seed_dir / "customers.csv", Customer)
    products = read_csv_rows(seed_dir / "products.csv", Product)

    if fresh and db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect(db_path)
    try:
        create_schema(conn)
        upsert_customers(conn, customers)
        upsert_products(conn, products)
        return count_rows(conn)
    finally:
        conn.close()
