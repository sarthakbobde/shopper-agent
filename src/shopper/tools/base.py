"""The two types every tool shares. Kept apart from tools/__init__.py so tool modules can import
them without a circular import."""

import sqlite3
from collections.abc import Callable
from dataclasses import dataclass

from google.genai import types

from shopper.config import ClientConfig


@dataclass
class ToolContext:
    """What a tool may use, passed in rather than looked up, so tests can hand it an in-memory database.

    `customer_id` starts empty and is filled in when customer_insights finds exactly one customer,
    so later feedback in the same conversation is linked to them.
    """

    conn: sqlite3.Connection
    config: ClientConfig
    conversation_id: str | None = None
    customer_id: str | None = None


@dataclass(frozen=True)
class Tool:
    """A tool's Gemini declaration and the function it describes, kept side by side so they can't drift."""

    name: str
    declaration: types.FunctionDeclaration
    function: Callable[..., dict]
