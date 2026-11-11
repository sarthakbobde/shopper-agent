"""Tests for seed.py and for the committed Shoppers Stop seed files."""

import pytest

from shopper import paths
from shopper.db import Customer, Product
from shopper.errors import UserError
from shopper.seed import load_seed, read_csv_rows

SEED = paths.client_seed_dir("shoppers_stop")


def test_seed_csvs_are_valid():
    customers = read_csv_rows(SEED / "customers.csv", Customer)
    products = read_csv_rows(SEED / "products.csv", Product)
    assert len(customers) == 50
    assert len(products) == 200


def test_seed_has_tier_boundaries_and_out_of_stock():
    spends = {c.total_spend_paise for c in read_csv_rows(SEED / "customers.csv", Customer)}
    for rupees in [2999, 3000, 10000, 10001]:
        assert rupees * 100 in spends, rupees
    stocks = [p.stock_qty for p in read_csv_rows(SEED / "products.csv", Product)]
    assert stocks.count(0) > 0


def test_seed_emails_are_unique_and_example_dot_com():
    emails = [c.email for c in read_csv_rows(SEED / "customers.csv", Customer)]
    assert len(emails) == len(set(emails))
    assert all(email.endswith("@example.com") for email in emails)


def test_read_csv_rows_reports_line_numbers(tmp_path):
    bad = tmp_path / "products.csv"
    bad.write_text(
        "product_id,code,name,brand,category,price_paise,stock_qty\n"
        "P1,SS-1,Good Shirt,Urbano,Men's Wear,129900,5\n"
        "P2,SS-2,Free Shirt,Urbano,Men's Wear,0,5\n"
        "P3,SS-3,Odd Shirt,Urbano,Men's Wear,129900,-1\n",
        encoding="utf-8",
    )
    with pytest.raises(UserError) as caught:
        read_csv_rows(bad, Product)
    message = str(caught.value)
    assert "2 bad rows" in message
    assert "line 3: price_paise" in message
    assert "line 4: stock_qty" in message


def test_read_csv_rows_missing_file(tmp_path):
    with pytest.raises(UserError, match="not found"):
        read_csv_rows(tmp_path / "nope.csv", Product)


def test_load_seed_into_a_temp_database(tmp_path):
    db_file = tmp_path / "test.db"
    expected = {"customers": 50, "products": 200, "feedback": 0}
    assert load_seed("shoppers_stop", db_path=db_file) == expected
    assert load_seed("shoppers_stop", db_path=db_file) == expected  # second run: no duplicates
    assert load_seed("shoppers_stop", db_path=db_file, fresh=True) == expected
