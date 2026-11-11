import pytest

from shopper.config import SpendTiers
from shopper.errors import ToolError
from shopper.rules import check_rating, spend_tier, stock_label

TIERS = SpendTiers(medium_from=3000, high_above=10000)


@pytest.mark.parametrize(
    ("rupees", "tier"),
    [(0, "Low"), (2999, "Low"), (3000, "Medium"), (10000, "Medium"), (10001, "High")],
)
def test_spend_tier_boundaries(rupees, tier):
    assert spend_tier(rupees * 100, TIERS) == tier


def test_spend_tier_one_paisa_below_medium_is_low():
    assert spend_tier(3000 * 100 - 1, TIERS) == "Low"


@pytest.mark.parametrize(
    ("qty", "label"), [(0, "out of stock"), (1, "only 1 left"), (5, "only 5 left"), (6, "in stock")]
)
def test_stock_label(qty, label):
    assert stock_label(qty) == label


@pytest.mark.parametrize(("value", "rating"), [(1, 1), (5, 5), ("4", 4), (" 3 ", 3), (4.0, 4)])
def test_check_rating_accepts(value, rating):
    assert check_rating(value) == rating


@pytest.mark.parametrize("value", [0, 6, -1, 4.5, "great", "", None, True])
def test_check_rating_rejects(value):
    with pytest.raises(ToolError, match="1 to 5"):
        check_rating(value)
