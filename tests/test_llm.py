"""Tests for the Gemini layer. A fake client stands in for Google, so nothing here uses the network."""

from types import SimpleNamespace

import pytest

from shopper.cli import build_parser
from shopper.errors import UserError
from shopper.llm import chat_models, explain_api_error, make_client, ping


def fake_model(name, actions=("generateContent",), limit=1_000_000):
    return SimpleNamespace(
        name=f"models/{name}", display_name=name, supported_actions=list(actions), input_token_limit=limit
    )


class FakeClient:
    """Looks like genai.Client for the one method ping uses, and records what it was sent."""

    def __init__(self, response):
        self.response = response
        self.sent = None
        self.models = self

    def generate_content(self, model, contents, config):
        self.sent = {"model": model, "contents": contents, "config": config}
        return self.response


def fake_response(text="pong", prompt=7, output=1, thoughts=None, calls=None):
    usage = SimpleNamespace(
        prompt_token_count=prompt, candidates_token_count=output, thoughts_token_count=thoughts
    )
    return SimpleNamespace(text=text, usage_metadata=usage, function_calls=calls)


# ---- models ----------------------------------------------------------------------------------


def test_chat_models_keeps_chat_models_and_drops_others():
    models = [
        fake_model("gemini-b-flash"),
        fake_model("gemini-a-pro"),
        fake_model("gemini-embedding-001", actions=["embedContent"]),
        fake_model("gemini-b-flash-image"),
        fake_model("gemini-b-flash-preview-tts"),
        fake_model("imagen-4", actions=["predict"]),
        fake_model("gemma-3-4b-it"),
        fake_model("gemini-nano-banana-2.1", limit=65_536),  # image model without "image" in the name
    ]
    names = [model.name for model in chat_models(models)]
    assert names == ["gemini-a-pro", "gemini-b-flash"]  # sorted, prefix removed


# ---- errors ----------------------------------------------------------------------------------


def test_explain_api_error_messages():
    assert "key" in explain_api_error(400, "API key not valid")
    assert "shopper models" in explain_api_error(404, "not found")
    assert "rate limit" in explain_api_error(429, "quota")
    assert "Details: quota" in explain_api_error(429, "quota")


def test_make_client_without_key_is_a_user_error(tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=\n", encoding="utf-8")
    with pytest.raises(UserError, match="not set"):
        make_client(env_file)


def test_make_client_without_env_file_is_a_user_error(tmp_path):
    with pytest.raises(UserError, match="not set"):
        make_client(tmp_path / "missing.env")


# ---- ping --------------------------------------------------------------------------------------


def test_ping_reads_tokens_and_time():
    client = FakeClient(fake_response(text=" pong\n", prompt=7, output=1, thoughts=20))
    result = ping(client, "gemini-test")
    assert result.reply == "pong"
    assert result.input_tokens == 7
    assert result.output_tokens == 21  # thinking tokens count as output
    assert result.seconds >= 0
    assert result.made_tool_call is None
    assert client.sent["config"] is None


def test_ping_detects_a_tool_call():
    call = SimpleNamespace(name="get_store_hours", args={"city": "Mumbai"})
    client = FakeClient(fake_response(text=None, calls=[call]))
    result = ping(client, "gemini-test", with_tool=True)
    assert result.made_tool_call is True
    assert "get_store_hours" in result.reply
    assert "Mumbai" in result.reply
    # the SDK must not run tools for us (ADR-002)
    assert client.sent["config"].automatic_function_calling.disable is True


def test_ping_reports_when_the_model_ignores_the_tool():
    client = FakeClient(fake_response(text="It opens at 11 am.", calls=None))
    result = ping(client, "gemini-test", with_tool=True)
    assert result.made_tool_call is False
    assert result.reply == "It opens at 11 am."


def test_ping_handles_missing_usage_numbers():
    response = SimpleNamespace(text="pong", usage_metadata=None, function_calls=None)
    result = ping(FakeClient(response), "gemini-test")
    assert (result.input_tokens, result.output_tokens) == (0, 0)


# ---- cli -------------------------------------------------------------------------------------


def test_cli_parses_models_and_ping():
    parser = build_parser()
    assert parser.parse_args(["models"]).command == "models"

    args = parser.parse_args(["ping", "--model", "x", "--tool"])
    assert (args.model, args.tool, args.client) == ("x", True, "shoppers_stop")

    args = parser.parse_args(["ping"])
    assert (args.model, args.tool) == (None, False)
