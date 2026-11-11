"""Tests for the four tools and run_tool, on a small in-memory database. No model, no network."""

import inspect

import pytest

from shopper.config import ClientConfig
from shopper.db import Customer, Product, connect, create_schema, upsert_customers, upsert_products
from shopper.errors import UserError
from shopper.tools import TOOLS, ToolContext, run_tool, tools_for
from shopper.tools.customer_insights import mask_email


def product(pid, code, name, price=129900, stock=10):
    return Product(product_id=pid, code=code, name=name, brand="Urbano", category="Men's Wear",
                   price_paise=price, stock_qty=stock)  # fmt: skip


def customer(cid, name, email, spend):
    return Customer(customer_id=cid, name=name, email=email, city="Pune", age_group="25-34",
                    preferred_category="Footwear", total_spend_paise=spend)  # fmt: skip


CONFIG = ClientConfig.model_validate(
    {
        "name": "Test Store",
        "languages": ["en"],
        "spend_tiers": {"medium_from": 3000, "high_above": 10000},
        "tools": list(TOOLS),
        "llm": {"model": "test-model"},
    }
)


@pytest.fixture
def ctx():
    conn = connect(":memory:")
    create_schema(conn)
    upsert_products(
        conn,
        [
            product("P1", "SS-MEN-0001", "Black Linen Kurta", price=139900),
            product("P2", "SS-MEN-0002", "Red Cotton Kurta", stock=0),
            product("P3", "SS-MEN-0003", "Blue Denim Jeans", stock=3),
        ],
    )
    upsert_customers(
        conn,
        [
            customer("C1", "Priya Sharma", "priya.sharma@example.com", 300000),
            customer("C2", "Priya Patel", "priya.patel@example.com", 1000100),
            customer("C3", "Arjun Iyer", "arjun.iyer@example.com", 299900),
        ],
    )
    yield ToolContext(conn=conn, config=CONFIG, conversation_id="conv-1")
    conn.close()


# ---- search_products ----------------------------------------------------------------------------


def test_search_exact(ctx):
    result = run_tool("search_products", {"query": "blue jeans"}, ctx)
    assert result["near_match"] is False
    assert result["count"] == 1
    jeans = result["results"][0]
    assert jeans["price"] == "₹1,299"
    assert jeans["price_paise"] == 129900
    assert jeans["in_stock"] is True
    assert jeans["stock"] == "only 3 left"


def test_search_out_of_stock_is_flagged(ctx):
    kurta = run_tool("search_products", {"query": "red kurta"}, ctx)["results"][0]
    assert kurta["in_stock"] is False
    assert kurta["stock"] == "out of stock"


def test_search_near_match(ctx):
    result = run_tool("search_products", {"query": "red linen kurta"}, ctx)
    assert result["near_match"] is True
    # "linen kurta" is tried first (leave out "red"), then "red kurta".
    assert [r["name"] for r in result["results"]] == ["Black Linen Kurta", "Red Cotton Kurta"]


def test_search_nothing(ctx):
    result = run_tool("search_products", {"query": "lehenga"}, ctx)
    assert result["count"] == 0
    assert result["near_match"] is False
    assert "note" in result


def test_search_limit_is_clamped(ctx):
    result = run_tool("search_products", {"query": "kurta", "limit": 50}, ctx)
    assert result["count"] == 2  # only two kurtas exist; a limit of 50 is cut to 10, not an error


# ---- customer_insights --------------------------------------------------------------------------


def test_customer_one(ctx):
    result = run_tool("customer_insights", {"query": "arjun"}, ctx)
    profile = result["customer"]
    assert profile["total_spend"] == "₹2,999"
    assert profile["spend_tier"] == "Low"
    assert profile["email"] == "a***@example.com"
    assert ctx.customer_id == "C3"  # remembered for feedback later in the conversation


def test_customer_by_id_any_case(ctx):
    result = run_tool("customer_insights", {"query": "c1"}, ctx)
    assert result["customer"]["name"] == "Priya Sharma"
    assert result["customer"]["spend_tier"] == "Medium"  # exactly ₹3,000


def test_customer_many(ctx):
    result = run_tool("customer_insights", {"query": "priya"}, ctx)
    assert result["count"] == 2
    assert {m["customer_id"] for m in result["matches"]} == {"C1", "C2"}
    assert "email" not in str(result["matches"])
    assert ctx.customer_id is None  # not chosen yet


def test_customer_none(ctx):
    assert run_tool("customer_insights", {"query": "nobody"}, ctx)["found"] is False


def test_mask_email():
    assert mask_email("sneha.desai@example.com") == "s***@example.com"


# ---- record_feedback ----------------------------------------------------------------------------


def test_feedback_saved_with_customer_and_conversation(ctx):
    run_tool("customer_insights", {"query": "arjun"}, ctx)
    result = run_tool("record_feedback", {"rating": 5, "comment": "  quick help  "}, ctx)
    assert result["saved"] is True
    row = ctx.conn.execute("SELECT * FROM feedback").fetchone()
    assert (row["rating"], row["comment"], row["customer_id"], row["conversation_id"]) == (
        5,
        "quick help",
        "C3",
        "conv-1",
    )


def test_feedback_rating_6_not_saved(ctx):
    result = run_tool("record_feedback", {"rating": 6}, ctx)
    assert "1 to 5" in result["error"]
    assert ctx.conn.execute("SELECT COUNT(*) FROM feedback").fetchone()[0] == 0


# ---- escalate_to_human --------------------------------------------------------------------------


def test_escalation_ticket(ctx):
    args = {"reason": "refund_or_complaint", "summary": "Wants a refund"}
    assert run_tool("escalate_to_human", args, ctx)["ticket"] == "ESC-0001"
    assert run_tool("escalate_to_human", args, ctx)["ticket"] == "ESC-0002"
    row = ctx.conn.execute("SELECT * FROM escalations").fetchone()
    assert (row["reason"], row["conversation_id"]) == ("refund_or_complaint", "conv-1")


def test_escalation_bad_reason(ctx):
    result = run_tool("escalate_to_human", {"reason": "bored", "summary": "x"}, ctx)
    assert "reason must be one of" in result["error"]


def test_escalation_needs_summary(ctx):
    result = run_tool("escalate_to_human", {"reason": "user_request", "summary": "  "}, ctx)
    assert "summary is required" in result["error"]


# ---- run_tool and the registry ------------------------------------------------------------------


def test_run_tool_unknown_tool(ctx):
    assert run_tool("delete_everything", {}, ctx) == {"error": "no tool called delete_everything"}


def test_run_tool_bad_arguments(ctx):
    assert "bad arguments" in run_tool("search_products", {"qeury": "kurta"}, ctx)["error"]
    assert "bad arguments" in run_tool("search_products", {}, ctx)["error"]


def test_run_tool_unexpected_failure_becomes_an_error(ctx):
    ctx.conn.close()  # any database call now raises
    result = run_tool("search_products", {"query": "kurta"}, ctx)
    assert result == {"error": "search_products failed: ProgrammingError"}


def test_declarations_match_functions():
    for name, tool in TOOLS.items():
        assert tool.declaration.name == name
        schema = tool.declaration.parameters_json_schema
        params = list(inspect.signature(tool.function).parameters.values())[1:]  # skip ctx
        assert set(schema["properties"]) == {p.name for p in params}, name
        required = {p.name for p in params if p.default is inspect.Parameter.empty}
        assert set(schema["required"]) == required, name


def test_tools_for_follows_config_order():
    config = CONFIG.model_copy(update={"tools": ["record_feedback", "search_products"]})
    assert [t.name for t in tools_for(config)] == ["record_feedback", "search_products"]


def test_tools_for_unknown_name():
    config = CONFIG.model_copy(update={"tools": ["search_product"]})
    with pytest.raises(UserError, match="unknown tools in client.yaml: search_product"):
        tools_for(config)


def test_shoppers_stop_config_names_only_known_tools():
    from shopper.config import load_client

    assert len(tools_for(load_client("shoppers_stop"))) == 4
