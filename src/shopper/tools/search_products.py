"""search_products: find items by what a shopper says, with near matches when nothing fits exactly."""

from google.genai import types

from shopper.db import MAX_SEARCH_WORDS, Product, find_products, normalise
from shopper.money import format_inr
from shopper.rules import stock_label
from shopper.tools.base import ToolContext

MAX_LIMIT = 10

DECLARATION = types.FunctionDeclaration(
    name="search_products",
    description=(
        "Search the store's catalogue by item type, colour, brand or product code, for example "
        "'blue sneakers', 'Kesari saree' or 'SS-FTW-0001'. Returns price, stock and product code. "
        "The catalogue is in English: translate Hindi or Hinglish words before searching "
        "(joote -> shoes, kurti -> kurta). If near_match is true, tell the user these are close "
        "matches, not exactly what they asked for."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search words in English, e.g. 'red kurta'"},
            "limit": {"type": "integer", "description": "How many results, 1 to 10 (default 5)"},
        },
        "required": ["query"],
    },
)


def product_result(p: Product) -> dict:
    """The shape the model sees: ready-to-say text (price, stock) plus the raw numbers for code."""
    return {
        "code": p.code,
        "name": p.name,
        "brand": p.brand,
        "category": p.category,
        "price": format_inr(p.price_paise),
        "price_paise": p.price_paise,
        "in_stock": p.stock_qty > 0,
        "stock": stock_label(p.stock_qty),
    }


def near_matches(conn, words: list[str], limit: int) -> list[Product]:
    """Retry the search leaving out one word at a time.

    Earlier words are left out first because in English the item usually comes last: for
    "red linen kurta" we try "linen kurta", then "red kurta", and only then "red linen".
    """
    found = []
    seen = set()
    for skip in range(len(words)):
        fewer = words[:skip] + words[skip + 1 :]
        for product in find_products(conn, " ".join(fewer), limit=limit):
            if product.product_id not in seen:
                seen.add(product.product_id)
                found.append(product)
    return found[:limit]


def search_products(ctx: ToolContext, query: str, limit: int = 5) -> dict:
    query = str(query)
    limit = max(1, min(int(limit), MAX_LIMIT))

    products = find_products(ctx.conn, query, limit=limit)
    near_match = False

    words = [w for w in query.split()[:MAX_SEARCH_WORDS] if normalise(w)]
    if not products and len(words) > 1:
        products = near_matches(ctx.conn, words, limit)
        near_match = bool(products)

    result = {
        "query": query,
        "near_match": near_match,
        "count": len(products),
        "results": [product_result(p) for p in products],
    }
    if not products:
        result["note"] = "Nothing found. Ask the user for a different item, colour or brand."
    return result
