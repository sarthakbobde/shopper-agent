"""`shopper doctor`: checks this machine and the project's settings before anything else runs.

Each check is split in two: a small *verdict* function that takes plain values and returns a
message, and `run_doctor`, which gathers the real values (Python version, the .env file, the
client configs). The verdicts are what the tests cover, so tests never need a real key.

A verdict starts with "ok" when the check passes. The key itself is never printed.
"""

import sqlite3
import sys
from pathlib import Path

from dotenv import dotenv_values

from shopper import paths
from shopper.config import list_clients, load_client
from shopper.db import connect, count_rows
from shopper.errors import UserError

KEY_NAME = "GEMINI_API_KEY"


def python_verdict(version: tuple[int, int]) -> str:
    if version >= (3, 12):
        return f"ok ({version[0]}.{version[1]})"
    return f"too old ({version[0]}.{version[1]}); this project needs Python 3.12 or newer"


def env_file_verdict(exists: bool) -> str:
    if exists:
        return "ok"
    return "missing; copy .env.example to .env"


def key_verdict(env: dict[str, str | None]) -> str:
    key = env.get(KEY_NAME) or ""
    if key.strip() == "":
        return f"not set; add {KEY_NAME} to .env (Step 01)"
    return "ok (set)"


def client_verdict(name: str) -> str:
    try:
        client = load_client(name)
    except UserError as error:
        return f"invalid: {error}"
    model = client.llm.model or "no model chosen yet (Step 01)"
    return f"ok ({client.name}, {len(client.tools)} tools, {model})"


def db_verdict(counts: dict[str, int] | None, client: str) -> str:
    if counts is None:
        return f"not created; run `shopper seed --client {client}`"
    parts = [f"{counts[table]} {table}" for table in ["customers", "products", "feedback"]]
    return f"ok ({', '.join(parts)})"


def read_db_counts(client: str) -> dict[str, int] | None:
    db_file = paths.client_db_file(client)
    if not db_file.is_file():
        return None
    conn = connect(db_file)
    try:
        return count_rows(conn)
    finally:
        conn.close()


def run_doctor(env_file: Path = paths.ENV_FILE) -> list[tuple[str, str]]:
    results = []
    results.append(("python", python_verdict(sys.version_info[:2])))

    results.append((".env", env_file_verdict(env_file.is_file())))
    env = dotenv_values(env_file) if env_file.is_file() else {}
    results.append(("gemini key", key_verdict(env)))

    clients = list_clients()
    if not clients:
        results.append(("clients", "none found in clients/"))
    for name in clients:
        results.append((f"client {name}", client_verdict(name)))
        try:
            counts = read_db_counts(name)
            results.append((f"database {name}", db_verdict(counts, name)))
        except sqlite3.Error as error:
            results.append((f"database {name}", f"unreadable: {error}"))

    return results
