# CLAUDE.md

shopper-agent: the Copilot Studio Shoppers Stop agent rebuilt in plain Python on Gemini, with voice
and the integration work of a forward-deployed engineer. Read these before changing anything:
[docs/PLAN.md](docs/PLAN.md) (how each step is built), [docs/STEPS.md](docs/STEPS.md) (roadmap
checklist), [docs/DECISIONS.md](docs/DECISIONS.md).

## Commands

Windows. Use `uv`, never bare `pip`. The shell may be PowerShell or Git Bash.
Set up in Step 00: `uv sync`, `uv run pytest -q`, `uv run ruff check src tests`,
`uv run ruff format --check src tests`. Run all three before saying a change is done.

## Conventions

- `src/shopper/cli.py` only parses options and calls a function. No logic in the CLI layer.
- Every path comes from `shopper.paths`.
- The engine never names a client; client specifics live in `clients/<name>/` (ADR-007).
- Business rules live in code with tests, not in prompts (ADR-005). The model never writes SQL (ADR-004).
- Production structure, plain code: readable loops and small functions. No agent frameworks.
- Tests never need the network, a microphone or a GPU. CI never calls Gemini.
- Add a test with each feature. Python 3.12, line length 110 (ruff).

## Rules

- **Before adding or changing any code, say what you plan to do and why, and wait for my OK.**
- Ask before anything paid, with the estimated cost. Ask before any download, with source and size.
- Never commit `.env`, keys, databases, audio, model weights or `data/`.
- Only fake data while on the free-tier key (ADR-008).
- Commit or push only when I ask. Never add a Co-Authored-By trailer or any Claude attribution.
- Decisions go in `docs/DECISIONS.md` as a new ADR. Never rewrite an accepted one.
- When a step finishes, tick `docs/STEPS.md`, add a project-log line, and note what was learned in `docs/PLAN.md`.

## How to work with me

I am learning, so teach as you go. Name the concept behind each step, show real output, verify
with a command, and when something fails twice, change approach or stop and ask.
