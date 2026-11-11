"""customer_insights: a customer's profile and spend tier, found by name, email or customer ID."""

from google.genai import types

from shopper.db import Customer, find_customers, get_customer
from shopper.money import format_inr
from shopper.rules import spend_tier
from shopper.tools.base import ToolContext

DECLARATION = types.FunctionDeclaration(
    name="customer_insights",
    description=(
        "Look up a customer by name, email or customer ID (like C0007). Returns city, age group, "
        "preferred category, total spend and spend tier (Low, Medium or High). If several "
        "customers match, it returns their names, cities and IDs: ask the user which one, then "
        "call again with that customer ID."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Name, email or customer ID"},
        },
        "required": ["query"],
    },
)


def mask_email(email: str) -> str:
    """sneha.desai@example.com -> s***@example.com. The model never needs the full address."""
    local, _, domain = email.partition("@")
    return f"{local[:1]}***@{domain}"


def profile(c: Customer, ctx: ToolContext) -> dict:
    return {
        "customer_id": c.customer_id,
        "name": c.name,
        "email": mask_email(c.email),
        "city": c.city,
        "age_group": c.age_group,
        "preferred_category": c.preferred_category,
        "total_spend": format_inr(c.total_spend_paise),
        "spend_tier": spend_tier(c.total_spend_paise, ctx.config.spend_tiers),
    }


def customer_insights(ctx: ToolContext, query: str) -> dict:
    query = str(query).strip()

    by_id = get_customer(ctx.conn, query) if query else None
    matches = [by_id] if by_id else find_customers(ctx.conn, query)

    if not matches:
        return {"found": False, "note": "No customer matches. Ask for the full name or email."}

    if len(matches) > 1:
        return {
            "found": True,
            "count": len(matches),
            "matches": [{"customer_id": c.customer_id, "name": c.name, "city": c.city} for c in matches],
            "note": "Several customers match. Ask which one, then call again with the customer ID.",
        }

    ctx.customer_id = matches[0].customer_id  # later feedback in this conversation is linked to them
    return {"found": True, "customer": profile(matches[0], ctx)}
