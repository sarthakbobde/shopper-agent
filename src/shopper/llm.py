"""Everything that talks to Gemini goes through this file.

Only `make_client` reads the API key, so the key cannot leak from anywhere else. The rest of the
project uses the small types defined here (`ModelInfo`, `PingResult`) instead of the SDK's own,
so the SDK can change without touching other files.

Step 01 adds only what is needed to prove the key, the model and function calling work. The agent
loop arrives in Step 04.
"""

import time
from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values
from google import genai
from google.genai import errors, types

from shopper import paths
from shopper.errors import UserError

KEY_NAME = "GEMINI_API_KEY"

# Model names containing any of these are not text chat models, so `shopper models` hides them.
# "nano-banana" is Google's image model family, whose names do not say "image".
NOT_CHAT = ["embedding", "image", "imagen", "nano-banana", "tts", "live", "native-audio", "veo", "aqa"]


def make_client(env_file: Path = paths.ENV_FILE) -> genai.Client:
    env = dotenv_values(env_file) if env_file.is_file() else {}
    key = (env.get(KEY_NAME) or "").strip()
    if key == "":
        raise UserError(f"{KEY_NAME} is not set in {env_file}; copy .env.example to .env and add it")
    return genai.Client(api_key=key)


def explain_api_error(status: int, message: str) -> str:
    if status == 400:
        hint = "the request was rejected; if it mentions the API key, the key in .env is wrong"
    elif status in (401, 403):
        hint = "the key is not allowed to use this; check it in Google AI Studio"
    elif status == 404:
        hint = "model not found; run `shopper models` to see the names your key can use"
    elif status == 429:
        hint = "rate limit or daily quota reached; wait a minute (or until tomorrow) and try again"
    elif status >= 500:
        hint = "Google's side failed; try again in a moment"
    else:
        hint = "unexpected error"
    return f"Gemini error {status}: {hint}. Details: {message}"


# ---- models ----------------------------------------------------------------------------------


@dataclass
class ModelInfo:
    name: str  # what goes in client.yaml, e.g. "gemini-x-flash" (without the "models/" prefix)
    display_name: str
    input_token_limit: int


def chat_models(models) -> list[ModelInfo]:
    """Keep the Gemini models that can chat (generateContent), drop the rest, sort by name.

    `models` is anything with the SDK Model fields, so tests can pass simple fake objects.
    """
    keep = []
    for model in models:
        name = (model.name or "").removeprefix("models/")
        actions = model.supported_actions or []
        if not name.startswith("gemini"):
            continue
        if "generateContent" not in actions:
            continue
        if any(word in name for word in NOT_CHAT):
            continue
        keep.append(ModelInfo(name, model.display_name or name, model.input_token_limit or 0))
    keep.sort(key=lambda info: info.name)
    return keep


def list_models(client: genai.Client) -> list[ModelInfo]:
    try:
        return chat_models(client.models.list())
    except errors.APIError as error:
        raise UserError(explain_api_error(error.code, error.message)) from error


# ---- ping --------------------------------------------------------------------------------------


@dataclass
class PingResult:
    model: str
    reply: str
    input_tokens: int
    output_tokens: int  # includes "thinking" tokens, because they are billed as output
    seconds: float
    made_tool_call: bool | None  # None when the tool was not offered


PING_TEXT = "Reply with exactly one word: pong"
TOOL_PING_TEXT = "When does the Shoppers Stop store in Mumbai open today?"

# A dummy tool. Gemini should ask to call it; we never actually run it.
STORE_HOURS_TOOL = types.FunctionDeclaration(
    name="get_store_hours",
    description="Get today's opening and closing time of the Shoppers Stop store in a city.",
    parameters_json_schema={
        "type": "object",
        "properties": {"city": {"type": "string", "description": "City name, e.g. Mumbai"}},
        "required": ["city"],
    },
)


def ping(client: genai.Client, model: str, with_tool: bool = False) -> PingResult:
    if with_tool:
        text = TOOL_PING_TEXT
        config = types.GenerateContentConfig(
            tools=[types.Tool(function_declarations=[STORE_HOURS_TOOL])],
            # We run tools ourselves (ADR-002), so the SDK must never call anything for us.
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )
    else:
        text = PING_TEXT
        config = None

    start = time.perf_counter()
    try:
        response = client.models.generate_content(model=model, contents=text, config=config)
    except errors.APIError as error:
        raise UserError(explain_api_error(error.code, error.message)) from error
    seconds = time.perf_counter() - start

    usage = response.usage_metadata
    input_tokens = 0
    output_tokens = 0
    if usage is not None:
        input_tokens = usage.prompt_token_count or 0
        output_tokens = (usage.candidates_token_count or 0) + (usage.thoughts_token_count or 0)

    made_tool_call = None
    reply = ""
    if with_tool:
        calls = response.function_calls or []
        made_tool_call = len(calls) > 0
        if made_tool_call:
            reply = f"asked to call {calls[0].name}({dict(calls[0].args or {})})"
    if reply == "":
        reply = (response.text or "").strip()

    return PingResult(model, reply, input_tokens, output_tokens, round(seconds, 2), made_tool_call)
