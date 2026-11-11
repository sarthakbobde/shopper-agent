"""record_feedback: save a 1-5 rating and an optional comment for this conversation."""

from google.genai import types

from shopper.db import add_feedback
from shopper.rules import check_rating
from shopper.tools.base import ToolContext

MAX_COMMENT = 500

DECLARATION = types.FunctionDeclaration(
    name="record_feedback",
    description=(
        "Save the user's rating of this conversation, a whole number from 1 to 5, with an optional "
        "comment. Call it only after the user gives a rating. If it returns an error, tell the user "
        "and ask again."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "rating": {"type": "integer", "description": "1 (poor) to 5 (excellent)"},
            "comment": {"type": "string", "description": "What the user said, if anything"},
        },
        "required": ["rating"],
    },
)


def record_feedback(ctx: ToolContext, rating: object, comment: str = "") -> dict:
    rating = check_rating(rating)  # raises ToolError for 0, 6, 4.5 or "great"; nothing is saved
    comment = str(comment).strip()[:MAX_COMMENT]
    feedback_id = add_feedback(
        ctx.conn, rating, comment, customer_id=ctx.customer_id, conversation_id=ctx.conversation_id
    )
    return {"saved": True, "feedback_id": feedback_id, "rating": rating}
