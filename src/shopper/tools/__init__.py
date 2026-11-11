"""The agent's tools: a registry, and one function that runs any of them safely.

The model chooses which tool to call and with what words; the code decides every fact (ADR-005).
`run_tool` always returns a dict. A problem the model can fix comes back as {"error": "..."}
instead of an exception, so the model can read it and try again (ADR-012).
"""

import inspect
import logging

from shopper.config import ClientConfig
from shopper.errors import ToolError, UserError
from shopper.tools import customer_insights, escalate_to_human, record_feedback, search_products
from shopper.tools.base import Tool, ToolContext

log = logging.getLogger(__name__)

TOOLS: dict[str, Tool] = {}
for module, function in [
    (search_products, search_products.search_products),
    (customer_insights, customer_insights.customer_insights),
    (record_feedback, record_feedback.record_feedback),
    (escalate_to_human, escalate_to_human.escalate_to_human),
]:
    TOOLS[module.DECLARATION.name] = Tool(module.DECLARATION.name, module.DECLARATION, function)


def tools_for(config: ClientConfig) -> list[Tool]:
    """The tools this client enables, in config order. An unknown name stops start-up."""
    unknown = [name for name in config.tools if name not in TOOLS]
    if unknown:
        raise UserError(f"unknown tools in client.yaml: {', '.join(unknown)}; known: {', '.join(TOOLS)}")
    return [TOOLS[name] for name in config.tools]


def run_tool(name: str, args: dict, ctx: ToolContext) -> dict:
    tool = TOOLS.get(name)
    if tool is None:
        return {"error": f"no tool called {name}"}

    try:
        inspect.signature(tool.function).bind(ctx, **args)  # wrong or missing arguments
    except TypeError as error:
        return {"error": f"bad arguments for {name}: {error}"}

    try:
        return tool.function(ctx, **args)
    except ToolError as error:
        return {"error": str(error)}
    except Exception as error:
        # A bug or a database problem must not end the conversation: report it as a tool failure,
        # which the prompt treats as a reason to escalate after two in a row.
        log.exception(f"tool {name} failed")
        return {"error": f"{name} failed: {type(error).__name__}"}


__all__ = ["TOOLS", "Tool", "ToolContext", "run_tool", "tools_for"]
