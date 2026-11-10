"""Tests for the shared pieces: paths, client config loading, the doctor's verdicts, CLI parsing."""

import pytest

from shopper import paths
from shopper.cli import build_parser
from shopper.config import list_clients, load_client, load_client_file
from shopper.doctor import client_verdict, env_file_verdict, key_verdict, python_verdict
from shopper.errors import UserError

VALID_CONFIG = """
name: Test Store
languages: [en]
spend_tiers: {medium_from: 3000, high_above: 10000}
tools: [search_products]
llm: {model: "", max_tool_rounds: 5}
"""


def write_config(tmp_path, text):
    path = tmp_path / "client.yaml"
    path.write_text(text, encoding="utf-8")
    return path


# ---- paths -----------------------------------------------------------------------------------


def test_client_paths_live_under_the_clients_folder():
    assert paths.client_config_file("abc") == paths.CLIENTS / "abc" / "client.yaml"
    assert paths.client_prompt_file("abc") == paths.CLIENTS / "abc" / "prompt.md"


# ---- config ----------------------------------------------------------------------------------


def test_shoppers_stop_config_loads_with_the_adr_005_tiers():
    client = load_client("shoppers_stop")
    assert client.name == "Shoppers Stop"
    assert client.spend_tiers.medium_from == 3000
    assert client.spend_tiers.high_above == 10000


def test_every_client_has_a_prompt_file():
    for name in list_clients():
        assert paths.client_prompt_file(name).is_file(), name


def test_valid_config_file_loads(tmp_path):
    client = load_client_file(write_config(tmp_path, VALID_CONFIG))
    assert client.tools == ["search_products"]
    assert client.webhook_url is None


def test_tiers_in_the_wrong_order_are_rejected(tmp_path):
    text = VALID_CONFIG.replace("medium_from: 3000", "medium_from: 20000")
    with pytest.raises(UserError, match="medium_from must be lower"):
        load_client_file(write_config(tmp_path, text))


def test_a_misspelt_key_is_rejected_not_ignored(tmp_path):
    text = VALID_CONFIG.replace("tools:", "tool:")
    with pytest.raises(UserError):
        load_client_file(write_config(tmp_path, text))


def test_an_empty_tool_list_is_rejected(tmp_path):
    text = VALID_CONFIG.replace("tools: [search_products]", "tools: []")
    with pytest.raises(UserError):
        load_client_file(write_config(tmp_path, text))


def test_a_missing_config_file_is_a_user_error(tmp_path):
    with pytest.raises(UserError, match="no client config"):
        load_client_file(tmp_path / "nope.yaml")


# ---- doctor ----------------------------------------------------------------------------------


def test_python_verdict():
    assert python_verdict((3, 12)).startswith("ok")
    assert python_verdict((3, 13)).startswith("ok")
    assert python_verdict((3, 11)).startswith("too old")


def test_env_file_verdict():
    assert env_file_verdict(True) == "ok"
    assert "copy .env.example" in env_file_verdict(False)


def test_key_verdict_never_prints_the_key():
    verdict = key_verdict({"GEMINI_API_KEY": "secret-value-123"})
    assert verdict.startswith("ok")
    assert "secret-value-123" not in verdict


def test_key_verdict_when_missing_or_blank():
    assert key_verdict({}).startswith("not set")
    assert key_verdict({"GEMINI_API_KEY": None}).startswith("not set")
    assert key_verdict({"GEMINI_API_KEY": "   "}).startswith("not set")


def test_client_verdict_for_a_real_and_a_missing_client():
    assert client_verdict("shoppers_stop").startswith("ok")
    assert client_verdict("no_such_client").startswith("invalid")


# ---- cli -------------------------------------------------------------------------------------


def test_cli_parses_doctor():
    args = build_parser().parse_args(["doctor"])
    assert args.command == "doctor"


def test_cli_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
