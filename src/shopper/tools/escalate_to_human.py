"""escalate_to_human: hand the conversation to a person and give the user a ticket number."""

from google.genai import types

from shopper.db import ESCALATION_REASONS, add_escalation
from shopper.errors import ToolError
from shopper.tools.base import ToolContext

DECLARATION = types.FunctionDeclaration(
    name="escalate_to_human",
    description=(
        "Hand the conversation to a human. Use it when the user asks for a person, for refunds, "
        "payments or complaints, for anything outside shopping help, or after a tool fails twice. "
        "Give the user the ticket number it returns."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "reason": {"type": "string", "enum": ESCALATION_REASONS, "description": "Why"},
            "summary": {"type": "string", "description": "One or two sentences for the human agent"},
        },
        "required": ["reason", "summary"],
    },
)


def escalate_to_human(ctx: ToolContext, reason: str, summary: str) -> dict:
    reason = str(reason).strip()
    summary = str(summary).strip()
    if reason not in ESCALATION_REASONS:
        raise ToolError(f"reason must be one of: {', '.join(ESCALATION_REASONS)}")
    if not summary:
        raise ToolError("summary is required: say in a sentence what the user needs")

    escalation_id = add_escalation(
        ctx.conn, reason, summary, customer_id=ctx.customer_id, conversation_id=ctx.conversation_id
    )
    return {
        "escalated": True,
        "ticket": f"ESC-{escalation_id:04d}",
        "note": "Tell the user a person will follow up, and give them the ticket number.",
    }
