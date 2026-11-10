"""Loads and checks clients/<name>/client.yaml.

Validation happens here, at startup, so a typo in a client's config stops the program with a clear
message instead of breaking halfway through a conversation. `extra="forbid"` turns an unknown or
misspelt key into an error rather than silently ignoring it.
"""

from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from shopper import paths
from shopper.errors import UserError


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SpendTiers(Strict):
    """Spend tier thresholds in rupees (ADR-005): Low < medium_from <= Medium <= high_above < High."""

    medium_from: int = Field(gt=0)
    high_above: int = Field(gt=0)

    @model_validator(mode="after")
    def medium_below_high(self) -> "SpendTiers":
        if self.medium_from >= self.high_above:
            raise ValueError("medium_from must be lower than high_above")
        return self


class LlmSettings(Strict):
    model: str = ""  # chosen in Step 01 (ADR-009); empty until then
    max_tool_rounds: int = Field(default=5, ge=1, le=10)


class ClientConfig(Strict):
    name: str
    languages: list[str] = Field(min_length=1)
    spend_tiers: SpendTiers
    tools: list[str] = Field(min_length=1)
    llm: LlmSettings
    webhook_url: str | None = None  # Step 07


def list_clients(clients_dir: Path = paths.CLIENTS) -> list[str]:
    names = []
    for folder in sorted(clients_dir.iterdir()):
        if (folder / "client.yaml").is_file():
            names.append(folder.name)
    return names


def load_client(name: str) -> ClientConfig:
    return load_client_file(paths.client_config_file(name))


def load_client_file(path: Path) -> ClientConfig:
    if not path.is_file():
        raise UserError(f"no client config at {path}")
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    try:
        return ClientConfig.model_validate(raw)
    except ValidationError as error:
        raise UserError(f"{path} is not valid:\n{error}") from error
