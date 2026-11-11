"""Every file and folder the project reads or writes, defined once.

ROOT is found from this file's own location, so it works from any working directory.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ENV_FILE = ROOT / ".env"  # secrets, git-ignored; .env.example lists the names

CLIENTS = ROOT / "clients"  # one folder per client: client.yaml, prompt.md, seed/ (ADR-007)

DATA = ROOT / "data"  # databases and data drops (git-ignored)

EVALS = ROOT / "evals"
EVAL_RUNS = EVALS / "runs"  # raw event logs from eval runs (git-ignored)
EVAL_REPORTS = EVALS / "reports"  # summarised reports (committed)


def client_dir(name: str) -> Path:
    return CLIENTS / name


def client_config_file(name: str) -> Path:
    return client_dir(name) / "client.yaml"


def client_prompt_file(name: str) -> Path:
    return client_dir(name) / "prompt.md"


def client_seed_dir(name: str) -> Path:
    return client_dir(name) / "seed"  # fake data CSVs, committed (ADR-011)


def client_db_file(name: str) -> Path:
    return DATA / f"{name}.db"  # one SQLite database per client, git-ignored
