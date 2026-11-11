"""Errors the user can fix themselves. The CLI prints these without a traceback."""


class UserError(Exception):
    pass


class ToolError(Exception):
    """A problem with a tool's input that the model can fix, such as a rating of 6.

    `run_tool` turns it into {"error": "..."} so the model reads the message and asks the user again.
    """
