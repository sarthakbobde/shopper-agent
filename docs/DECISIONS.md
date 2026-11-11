# Decisions

Architecture Decision Records: what was decided, the options, and the consequences.

**Rules**
- Never delete or rewrite an accepted decision. If it changes, add a new ADR and mark the old one
  `Superseded by ADR-XXX`. The history is the point.
- Add new decisions at the bottom with the next number, and add a row to the index.
- Link to a decision as `docs/DECISIONS.md#adr-002`.

## Index

| ADR | Decision | Status | Date |
|---|---|---|---|
| [001](#adr-001) | Rebuild the Copilot Studio agent in plain Python, plus FDE integrations | Accepted | 2026-11-10 |
| [002](#adr-002) | Gemini through `google-genai`, with a hand-written function-calling loop | Accepted | 2026-11-10 |
| [003](#adr-003) | Project layout: uv, Pydantic, one CLI, tests, ruff, CI | Accepted | 2026-11-10 |
| [004](#adr-004) | SQLite with fixed parameterized queries; the model never writes SQL | Accepted | 2026-11-10 |
| [005](#adr-005) | Business rules live in code, one source per rule | Accepted | 2026-11-10 |
| [006](#adr-006) | Cascaded voice first; Gemini Live as a measured comparison | Accepted | 2026-11-10 |
| [007](#adr-007) | Engine separate from client config | Accepted | 2026-11-10 |
| [008](#adr-008) | Fake data only while on the Gemini free tier | Accepted | 2026-11-10 |
| [009](#adr-009) | Default model `gemini-3.5-flash-lite`; Step 05 keeps the fastest model that scores ≥ 90 % | Accepted | 2026-11-10 |
| [010](#adr-010) | Money is stored as whole paise (integers), never floats | Accepted | 2026-11-10 |
| [011](#adr-011) | Seed data: generated once by a fixed-seed script, committed as CSV, fully invented | Accepted | 2026-11-10 |
| [012](#adr-012) | Tools return errors as data, mask personal data, and use a fixed list of escalation reasons | Accepted | 2026-11-11 |

## Changes from the original plan

When reality forces a change, add a row: topic, original plan, now, why, ADR.

| Topic | Original plan | Now | Why | ADR |
|---|---|---|---|---|
| `conversations` table | Created in Step 02 with the other tables | Created in Step 04 | Nothing writes to it until the agent loop exists; an empty table now would only be guessed at | none |

## Project log

| Date | What |
|---|---|
| 2026-11-10 | Copilot Studio solution (ShoppingAgent 1.0.0.2) reviewed; six issues found (see PLAN.md §1). Repo created; README, PLAN, STEPS, DECISIONS and CLAUDE.md written. Nothing committed. |
| 2026-11-10 | Step 00 done: uv package, `shopper doctor`, paths, client config with validation (`clients/shoppers_stop`), 15 tests, ruff, CI workflow. `doctor` reports `.env` and the key missing, as expected before Step 01. Nothing committed. |
| 2026-11-10 | Step 00 committed (`78a3d3d`) and pushed to the public repo `sarthakbobde/shopper-agent`; first CI run passed. |
| 2026-11-10 | Step 01 done: `google-genai` 3.0.0, `llm.py` (client, model list, ping, error messages), `shopper models` and `shopper ping`, 9 new tests (24 total). Key works; 4 models latency-tested; `gemini-3.5-flash-lite` chosen (ADR-009). Not committed. |
| 2026-11-10 | Step 01 and two small fixes committed (`c0f1aab`) and pushed; CI passed. |
| 2026-11-10 | Step 02 done: `db.py` (schema with CHECK rules, word-by-word product search, customer lookup, feedback with who and when), `seed.py`, fixed-seed generator and CSVs (50 customers, 200 products, 21 out of stock), `shopper seed / products / customers`, database line in `doctor`; 21 new tests (45 total). ADR-010, ADR-011. Not committed. |
| 2026-11-11 | Step 02 committed (`a9ed961`) and pushed; CI passed. |
| 2026-11-11 | Step 03 done: `money.py` (₹ with Indian grouping), `rules.py` (spend tier, stock label, rating check), `tools/` with the four tools, a registry and `run_tool`, `escalations` table, `shopper tool` to run a tool by hand, UTF-8 console output for ₹ on Windows; 55 new tests (100 total). ADR-012. Not committed. |

## Template

```
<a id="adr-NNN"></a>
## ADR-NNN — Title
**Status:** Proposed | Accepted | Superseded by ADR-XXX · **Date:** YYYY-MM-DD · **Step:** NN

### Context
### Options
### Decision
### Consequences
```

<a id="adr-001"></a>
## ADR-001 — Rebuild the Copilot Studio agent in plain Python, plus FDE integrations
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 00

### Context
The original agent was built in Copilot Studio on Dataverse: three tables (customers, products,
feedback), three topics (product search, customer insights, feedback), and the Dataverse MCP
server. It works, but the logic is split between instructions and topics that contradict each
other, it cannot be tested outside the studio, and it shows little of the engineering a
forward-deployed role asks for.

### Options
1. Keep it in Copilot Studio and fix the issues — quick, but still not testable or portable.
2. Rebuild on an agent framework (LangChain, LangGraph) — less code to write, but the
   orchestration is hidden, and three tools do not need it.
3. **Rebuild in plain Python, then add ingestion, API, webhooks, voice, analytics and deployment.**

### Decision
Option 3. Same features as the original first (Phase 1), then the work around it (Phases 2–4).

### Consequences
- Everything is testable in CI and runs on the laptop.
- More code to write than option 2; kept readable on purpose (ADR-003).

<a id="adr-002"></a>
## ADR-002 — Gemini through `google-genai`, with a hand-written function-calling loop
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 04

### Context
The key available is a Gemini key. Gemini supports function calling. The `google-genai` SDK can
run Python functions automatically ("automatic function calling").

### Options
1. `google-generativeai` — the older SDK, deprecated.
2. `google-genai` with automatic function calling — shortest code, but the loop is hidden, and
   logging, the round limit and error handling happen inside the SDK.
3. **`google-genai` with automatic function calling off, and our own loop.**

### Decision
Option 3. The loop is about 50 lines; every step is logged as an event. The LLM sits behind a
small interface so tests use a scripted fake and another provider could be added later.

### Consequences
- Full control over retries, the 5-round limit, and what goes in the event log.
- We maintain the conversion between our message format and Gemini's.

<a id="adr-003"></a>
## ADR-003 — Project layout: uv, Pydantic, one CLI, tests, ruff, CI
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 00

### Context
The project has to be easy to install on a fresh machine, easy to check, and easy for a reviewer
to read quickly.

### Decision
- **uv** for the environment: one command installs exact, locked versions.
- **Pydantic** for config and tool inputs: bad values fail at load time with a clear message.
- One **`shopper` CLI** that only parses options and calls functions, so the logic is testable
  without the command line.
- **pytest** and **ruff** (line length 110), with **GitHub Actions** running lint, a format check
  and the tests on every push.
- Production structure, plain code: readable loops and small functions, no clever one-liners.

### Consequences
- A reviewer can clone, run `uv sync` and `uv run pytest`, and see it work.
- CI installs only the core dependencies; voice and cloud extras are optional.

<a id="adr-004"></a>
## ADR-004 — SQLite with fixed parameterized queries; the model never writes SQL
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 02

### Context
The Copilot Studio ProductSearch topic told the model to write SQL with `LIKE` wildcards. A
model writing queries can read tables it should not, or be talked into it by a user
(prompt injection).

### Options
1. Let the model write read-only SQL — flexible, but unsafe and hard to test.
2. **Fixed queries; the model passes only values (a search string, an email).**
3. Postgres from day one — more realistic, but a server to run for no gain at this size.

### Decision
Option 2 on SQLite, using the standard `sqlite3` module and `?` placeholders. Fuzzy matching is
done in Python on normalised text. Postgres can replace SQLite later behind `db.py`.

### Consequences
- A tool can only do what its query does; easy to test and to explain to a client's security team.
- New questions need a new tool, not a new prompt.

<a id="adr-005"></a>
## ADR-005 — Business rules live in code, one source per rule
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 03

### Context
The original had two different spend-tier rules (₹3,000/₹10,000 in the instructions, 500/1,500
in the topic) and two opposite feedback rules ("always ask", "never ask"). Rules written as
prompt text drift and cannot be tested.

### Decision
Spend tiers, the stock flag, price formatting and rating validation are functions with unit
tests. Thresholds come from `client.yaml`. For Shoppers Stop: Low below ₹3,000, Medium
₹3,000–₹10,000, High above ₹10,000 (the instructions' version, since the values are rupees).
Feedback is asked for once, at the end of a conversation that completed a task.

### Consequences
- The prompt only covers tone, scope and when to escalate.
- The eval checks that the reply repeats what the tool returned.

<a id="adr-006"></a>
## ADR-006 — Cascaded voice first; Gemini Live as a measured comparison
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 09

### Options
1. Gemini Live API only — natural, low latency, handles interruptions, but a second agent path,
   and every second of audio uses the key's quota.
2. **Cascade (VAD → faster-whisper → the same agent → TTS) first, Live later as Step 11.**

### Decision
Option 2. Text and voice share one agent and one eval set. Step 11 runs the same cases on Live and
compares accuracy, time to first audio and cost.

### Consequences
- Higher latency than Live (expected 1.5–3 s); reduced by streaming replies by sentence.
- ASR and TTS run locally, so they cost no quota.

<a id="adr-007"></a>
## ADR-007 — Engine separate from client config
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 00

### Context
A forward-deployed engineer configures one platform for many clients. Showing that a new client
is mostly config is the point of Step 13.

### Decision
`clients/<name>/` holds `client.yaml`, `prompt.md` and seed data. The engine reads whichever
client the CLI or API names and never mentions a client by name.

### Consequences
- Slight extra work up front (config loading and validation in Step 00).

<a id="adr-008"></a>
## ADR-008 — Fake data only while on the Gemini free tier
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 01

### Context
Google may use free-tier prompts to improve its products, and free-tier rate limits are low.

### Decision
All customers, products and feedback are generated fake data. CI never calls Gemini. Live evals
are throttled.

### Consequences
- No real personal data ever goes into prompts or logs.

<a id="adr-009"></a>
## ADR-009 — Default model `gemini-3.5-flash-lite`; Step 05 keeps the fastest model that scores ≥ 90 %
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 01

### Context
Model names and free-tier limits change often, so the choice was made from what the key can see
(`shopper models`: 12 chat models) and from measurements, not from memory.

- `gemini-2.5-flash` is listed but returns 404 "no longer available to new users". **Listed does
  not mean usable**; only a real call proves it.
- `shopper ping --tool` (one question, one dummy `get_store_hours` tool), 5 runs per model,
  2026-11-10, laptop on home network:

| Model | Median | Min | Max | Tool call | Output tokens | Paid $/call |
|---|---|---|---|---|---|---|
| gemini-3.8-flash | 2.76 s | 2.33 | 3.17 | 5/5 | 74 | 0.00034 |
| gemini-3.6-flash | 2.10 s | 1.84 | 2.57 | 5/5 | 106 | 0.00046 |
| **gemini-3.5-flash-lite** | **1.37 s** | 1.27 | 2.18 | 5/5 | 18 | 0.00007 |
| gemini-3.1-flash-lite | 0.94 s | 0.86 | 1.46 | 5/5 | 18 | 0.00005 |

Paid prices (USD per 1M tokens, input / output incl. thinking): 3.8 and 3.6 Flash $0.75 / $3.75
(doubling on 2027-01-01), 3.5 Flash-Lite $0.30 / $2.50, 3.1 Flash-Lite $0.25 / $1.50. We are on
the free tier, so the real cost is ₹0; the paid numbers feed the Step 12 cost report.

### Options
1. `gemini-3.8-flash` — newest, Google's suggested default, but it "thinks": ~4× the output
   tokens and ~2.8 s per call. A tool turn needs two calls (~5.5 s), too slow for voice.
2. **`gemini-3.5-flash-lite`** — 1.4 s, no visible thinking overhead, 5× cheaper; newer than 3.1.
3. `gemini-3.1-flash-lite` — fastest and cheapest, but an older generation; likely weaker on
   Hindi and multi-step requests (unverified).

### Decision
Option 2 as the default, in `clients/shoppers_stop/client.yaml`. In Step 05 the eval runs on
3.1-flash-lite, 3.5-flash-lite and 3.8-flash, and we keep **the fastest model that scores at least
90 % on tool-call accuracy and answer facts**. That result becomes a new ADR.

### Consequences
- The ping test is easy (one obvious tool); it proves speed and basic tool calling, not quality.
- Switching model is a one-line config change.
- Five calls from one place at one time are a rough guide; Step 05 measures p50/p95 properly.

<a id="adr-010"></a>
## ADR-010 — Money is stored as whole paise (integers), never floats
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 02

### Context
Floating-point numbers cannot store most decimal fractions exactly: in Python `0.1 + 0.2` is
`0.30000000000000004`. Prices, spends and tier thresholds must compare exactly (a customer at
exactly ₹3,000 must land in Medium every time).

### Options
1. Floats in rupees — simple, but inexact.
2. `Decimal` — exact, but every layer (SQLite, CSV, JSON to Gemini) needs care to keep it.
3. **Integers in paise** (₹1,299.00 = `129900`).

### Decision
Option 3. Columns and fields end in `_paise` so the unit is never in doubt. Conversion to rupees
happens only when text is shown to a person (Step 03's formatter).

### Consequences
- Exact comparisons and sums everywhere; SQLite stores them natively.
- Thresholds in `client.yaml` stay in rupees for readability and are converted once when used.

<a id="adr-011"></a>
## ADR-011 — Seed data: generated once by a fixed-seed script, committed as CSV, fully invented
**Status:** Accepted · **Date:** 2026-11-10 · **Step:** 02

### Context
The agent needs realistic data to search, and tests need the same data on every machine. The
free-tier key may send prompts to Google's training (ADR-008), so the data must be fake.

### Options
1. Copy real Shoppers Stop products — real brands and prices we have no right to publish.
2. Generate random data at test time — different on every run unless seeded, and invisible in review.
3. **A script with `random.Random(42)` that writes CSVs, which are committed.**

### Decision
Option 3: `clients/shoppers_stop/seed/generate.py`. Rerunning it gives byte-identical files
(checked with SHA-256). Names are common Indian names, emails use `example.com`, brands
(Urbano, Kesari, Tara Lane …) are made up. The data deliberately includes customers at ₹2,999,
₹3,000, ₹10,000 and ₹10,001, and about 10 % of products out of stock (21 of 200).

### Consequences
- Reviewers can read the data in the repo; tests check its properties.
- Changing the data means editing the script and regenerating, never hand-editing a CSV.

<a id="adr-012"></a>
## ADR-012 — Tools return errors as data, mask personal data, and use a fixed list of escalation reasons
**Status:** Accepted · **Date:** 2026-11-11 · **Step:** 03

### Context
The model calls tools with whatever it understood from the user: a rating of 6, a misspelt
argument, a reason we never planned for. A tool that raises an exception would end the
conversation; one that quietly accepts bad input would store wrong data. Tools also see customer
records, and whatever they return is sent to Gemini.

### Options
1. Raise exceptions and let the agent loop decide — every caller must know every error.
2. **`run_tool` always returns a dict; problems come back as `{"error": "..."}`.**
3. Validate only in the prompt — the Copilot Studio approach, which drifted.

### Decision
Option 2. `ToolError` marks a problem the model can fix ("rating must be a whole number from 1 to
5"); `run_tool` turns it, an unknown tool, wrong arguments, or an unexpected exception into an
error result, and nothing is written. Unexpected failures are logged with the traceback and
reported as `"<tool> failed: <ErrorType>"`, which the prompt counts toward "a tool failed twice".

Two related rules:
- **Personal data:** `customer_insights` returns the email masked (`s***@example.com`); several
  matches return only names, cities and IDs. The model gets what it needs to answer, no more.
- **Escalation reasons** are a fixed list (`user_request`, `refund_or_complaint`, `tool_failure`,
  `out_of_scope`), enforced in code and by a CHECK in the `escalations` table, so Step 12 can count
  *why* conversations were not contained.

### Consequences
- The agent loop in Step 04 never needs a try/except around a tool.
- Error text is written for the model to repeat, so it must stay short and plain.
- A new escalation reason needs a code change, a schema change and an ADR; that is intended.
