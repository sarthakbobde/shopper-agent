import pytest

from shopper.money import format_inr, group_indian


@pytest.mark.parametrize(
    ("paise", "text"),
    [
        (0, "₹0"),
        (9900, "₹99"),
        (100000, "₹1,000"),
        (409900, "₹4,099"),
        (10000000, "₹1,00,000"),
        (12345650, "₹1,23,456.50"),
        (1234567800, "₹1,23,45,678"),
        (5, "₹0.05"),
        (-150000, "-₹1,500"),
    ],
)
def test_format_inr(paise, text):
    assert format_inr(paise) == text


def test_group_indian_short_numbers_have_no_comma():
    assert group_indian(999) == "999"
    assert group_indian(1000) == "1,000"
