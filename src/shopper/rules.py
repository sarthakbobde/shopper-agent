"""Business rules: exact answers that must never depend on what the model decides (ADR-005).

The Copilot Studio version kept these in its prompt, where two versions of the spend tiers
disagreed. Here each rule is one small function with tests for its edges.
"""

from shopper.config import SpendTiers
from shopper.errors import ToolError

LOW_STOCK_MAX = 5  # at or below this, the agent says "only N left"


def spend_tier(total_spend_paise: int, tiers: SpendTiers) -> str:
    """Low below medium_from; Medium from medium_from up to and including high_above; High above it.

    Thresholds are in rupees in client.yaml, so they are converted to paise before comparing.
    """
    if total_spend_paise < tiers.medium_from * 100:
        return "Low"
    if total_spend_paise <= tiers.high_above * 100:
        return "Medium"
    return "High"


def stock_label(stock_qty: int) -> str:
    if stock_qty <= 0:
        return "out of stock"
    if stock_qty <= LOW_STOCK_MAX:
        return f"only {stock_qty} left"
    return "in stock"


def check_rating(value: object) -> int:
    """Accept a whole number from 1 to 5, given as a number or as text like "4". Raise ToolError otherwise."""
    message = "rating must be a whole number from 1 to 5"
    if isinstance(value, bool):  # True is an int in Python; it is not a rating
        raise ToolError(message)
    if isinstance(value, float):
        if not value.is_integer():
            raise ToolError(message)
        value = int(value)  # Gemini sends JSON numbers, so 4 can arrive as 4.0
    if isinstance(value, str):
        text = value.strip()
        if not text.isdigit():
            raise ToolError(message)
        value = int(text)
    if not isinstance(value, int) or not 1 <= value <= 5:
        raise ToolError(message)
    return value
