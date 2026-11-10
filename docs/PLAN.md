# Development Plan

How shopper-agent gets built: architecture, the work in each step, what "done" means, and the risks.
The checklist lives in [STEPS.md](STEPS.md); decisions live in [DECISIONS.md](DECISIONS.md).
This file is the *how*. Update it when a step teaches us something.

**Goal:** rebuild the Copilot Studio "Shopping agent" for Shoppers Stop as plain Python on Gemini,
add voice, and surround it with the integration and operations work of a forward-deployed
engineer: ingestion, an authenticated API, webhooks, analytics, deployment, and a second client
configured from the same engine (ADR-001, ADR-007).

**Showcase target:** the GreyLabs AI Forward Deployed Engineer role. It asks for Python, REST
APIs, webhooks, OAuth/token auth, SFTP/S3 batch ingestion, CRM/ticketing/dialer integrations,
AWS or GCP, prompt engineering, routing and fallback handling, multilingual voice, and improving
accuracy and containment from conversation logs. Every phase below maps to part of that list.

**Constraints:** Gemini free-tier key, so low rate limits and fake data only (ADR-008). Voice
models run on the laptop (GTX 1650, 4 GB; benchmark only when plugged in). Time estimates are
guesses until Phase 1 is done.

---

## 1. Architecture

```
 channels                         engine                                    data
 ────────                         ──────                                    ────
 shopper chat (terminal) ─┐
 web chat  (HTTP + token) ├──►  agent turn loop  ──► tools ──────────────►  SQLite
 web voice (WebSocket)  ──┘     (Gemini function     search_products        customers
   VAD → ASR ──► text            calling, ≤ 5 tool   customer_insights      products
   text ──► TTS ◄── reply        rounds per turn)    record_feedback        feedback
                                       │             escalate_to_human      conversations
                                       ▼                    │
                                 event log (JSONL)          └──► webhook out (HMAC-signed,
                                       │                         retried) → mock CRM
                                       ▼
                                 analytics report         ingest: S3 / SFTP / folder CSV
                                                                 → validate → upsert
```

### The agent turn loop

One function, written out by hand (no framework, automatic function calling turned off; ADR-002):

1. Send the system prompt, the conversation so far and the tool declarations to Gemini.
2. If the reply contains function calls, run each tool, append the results, and go back to 1.
3. Stop when the reply is plain text, or after 5 tool rounds (then apologise and escalate).
4. Log an event for every step: `user_message`, `llm_request`, `tool_call`, `tool_result`,
   `tool_error`, `agent_reply`, `escalation`, with timestamps and token counts.

The LLM sits behind a small interface (`generate(messages, tools) -> reply`). Tests use a
`ScriptedLLM` that replays canned replies, so CI never calls Gemini.

### Tools hold the rules, the prompt holds the tone

Everything the Copilot Studio version left to the prompt that must be exact moves into code
(ADR-005):

| Rule | Copilot Studio | Here |
|---|---|---|
| Spend tier | Two conflicting versions (₹3,000/₹10,000 in the instructions, 500/1,500 in the topic) | One function, thresholds in the client config |
| Out of stock | Prompt asks the model to flag it | Tool returns `in_stock: false`; the reply template shows it |
| Price format | "Strictly format in ₹" in the prompt | Tool returns paise as an integer; one formatter prints `₹1,299` |
| Product search | Model writes SQL with `LIKE` | Fixed parameterized queries; the model only passes a search string (ADR-004) |
| Feedback | Rating and comment only | Rating validated 1–5, plus customer ID, conversation ID and timestamp |
| When to ask for feedback | Instructions say "always", ProductSearch says "never" | One rule: ask once, at the end of a conversation that completed a task |
| Environment URL | Hardcoded Dataverse org URL | Config and environment variables only |

### Client config: engine vs deployment

```
clients/
  shoppers_stop/
    client.yaml      name, language list, voice, spend tiers, enabled tools, webhook URL
    prompt.md        system prompt: persona, tone, when to escalate
    seed/            fake customers.csv, products.csv
  nbfc_reminders/    Phase 4: same engine, different prompt, tools and data
```

`shopper chat --client shoppers_stop`. The engine never names a client.

### Planned package layout

```
src/shopper/
  cli.py          parses options and calls a function, nothing else
  paths.py        every path
  config.py       load and validate client.yaml (Pydantic)
  db.py           schema, connection, queries
  tools/          one module per tool; plain functions + their Gemini declarations
  llm.py          LLM interface, GeminiLLM, ScriptedLLM
  agent.py        the turn loop
  events.py       event types and the JSONL writer
  ingest.py       Phase 2: sources (folder, S3, SFTP), validation, upsert, reject report
  api.py          Phase 2: FastAPI app, token auth
  webhooks.py     Phase 2: signing, sending, retries
  voice/          Phase 3: vad.py, asr.py, tts.py, session.py (WebSocket loop)
  evals/          scripted conversations, scoring, report
web/              chat page, voice page
```

---

## 2. Measurement (built in Phase 1, extended by every phase)

| Metric | Definition | First target |
|---|---|---|
| Tool-call accuracy | Right tool with the right key arguments, per eval turn | ≥ 90 % |
| Answer facts | Expected facts (price, stock, tier) present in the reply | ≥ 90 % |
| Containment rate | Conversations finished without `escalate_to_human` when the case did not need it | ≥ 85 % |
| Correct escalation | Cases that *should* escalate, and did | ≥ 90 % |
| Text response time | `user_message` → `agent_reply`, p50 / p95 | measured |
| Voice time to first audio | end of user speech → first agent audio, p50 / p95 | p50 ≤ 2.0 s |
| ASR WER | Word error rate on recorded English, Hindi and Hinglish clips | measured per language |
| Cost per conversation | Tokens × list price (₹0 on the free tier, but reported) | measured |

**Eval set:** 40 scripted text conversations in `evals/cases/`: product lookups (exact, misspelt,
Hindi), customer insights, feedback, out-of-scope requests and cases that must escalate. Each
case lists the expected tool calls and facts, so scoring is a check, not a judgment. Voice
evals reuse the same cases as recorded audio.

Targets are first guesses; Step 05 replaces them with what the first version achieves.

---

## 3. Steps

Each step ends with tests passing, lint clean, and a line in the project log (DECISIONS.md).

### Phase 0 — Foundations
- **00 Scaffold.** uv project, `shopper` CLI, `shopper doctor` (Python version, `.env` present,
  key set, database reachable), paths, config loading, tests, ruff, GitHub Actions CI.
  *Done:* `uv run pytest` and CI green.
- **01 Gemini key and first call.** You create the key in Google AI Studio and put it in `.env`.
  We list the available models, pick one, record it in ADR-009, and make one call that prints
  the reply and token counts. *Done:* `shopper doctor` shows the key works.

### Phase 1 — Text agent (the Copilot Studio rebuild)
- **02 Data and seed.** Schema for customers, products, feedback and conversations. A seed
  script with fake Indian retail data (about 50 customers, 200 products, prices in paise).
  Fuzzy product search: normalise case, spaces and hyphens, then substring match.
  *Done:* query tests pass on the seed data.
- **03 Tools and business rules.** The four tools as plain functions with typed inputs and
  outputs, plus their Gemini declarations. Spend tiers, stock flag, price formatting, rating
  validation. *Done:* every rule unit-tested, including the edges (exactly ₹3,000, stock 0,
  rating 6).
- **04 Agent loop and terminal chat.** The turn loop, the event log, the system prompt from
  `prompt.md`, and `shopper chat`. *Done:* a scripted-LLM test covers a two-tool turn and the
  5-round limit; a live chat works by hand.
- **05 Eval harness.** The 40 cases, the scorer, and `shopper eval` (scripted in CI, live
  against Gemini with a delay between calls to stay under the rate limit).
  *Done:* first live report written; targets in §2 updated.

### Phase 2 — Integrations (the FDE part)
- **06 Batch ingestion.** `shopper ingest` reads a product or customer CSV from a local folder,
  an S3 bucket or an SFTP server, validates every row, upserts the good ones and writes a
  reject report. S3 is tested against a local fake (moto); SFTP against a local test server.
  *Done:* a file with 5 bad rows loads the rest and reports the 5.
- **07 API, auth and webhooks.** FastAPI `POST /chat` with bearer-token auth. After each
  conversation and each feedback row, a webhook posts a summary to a CRM URL, signed with
  HMAC-SHA256, retried with backoff, and logged. A tiny mock CRM receiver verifies signatures.
  *Done:* tests for a bad token, a bad signature and a receiver that fails twice.
- **08 Web chat.** A plain HTML/JS chat page served by FastAPI, with a feedback form.
  *Done:* a full conversation works in the browser.

### Phase 3 — Voice
- **09 Speech in.** Silero VAD and faster-whisper (multilingual) behind a thin wrapper.
  Record 30 short clips (English, Hindi, Hinglish) of real eval questions.
  *Done:* WER per language in a report; the model size picked from measured speed and VRAM.
- **10 Speech out and the voice loop.** TTS (choice recorded as an ADR after testing Hindi
  voices), replies streamed sentence by sentence, a WebSocket endpoint, browser mic capture and
  playback. Spoken feedback replaces the form: the agent asks for 1–5 and the tool rejects
  anything else. *Done:* time to first audio measured, p50 and p95.
- **11 Gemini Live comparison.** The same tools on the Gemini Live API (native audio).
  *Done:* a table comparing accuracy, time to first audio and cost against Step 10 (ADR-006).

### Phase 4 — Operate and ship
- **12 Conversation analytics.** `shopper report` reads the event logs and writes containment,
  escalation, tool success and errors, latency and cost per conversation, with the worst
  conversations listed for review. *Done:* one change made because of the report, and its
  before/after numbers.
- **13 Second client.** `clients/nbfc_reminders`: a payment-reminder agent (due amount, promise
  to pay, callback request) with its own prompt, two new tools and seed data.
  *Done:* the engine diff is empty or near it; the change list is written up.
- **14 Deploy and write-up.** Dockerfile, Cloud Run, the key in Secret Manager, README with
  architecture, results and a short demo video. *Ask before anything paid.*

---

## 4. Risks

| Risk | Effect | Plan |
|---|---|---|
| Free-tier rate limits | Live evals stall | Scripted LLM in CI; live evals throttled; run the full set rarely |
| Gemini model names change | Code breaks on retirement | Model name only in config; `doctor` checks it exists |
| Hindi TTS quality | Voice demo sounds poor | Test 2–3 options in Step 10 before choosing; a cloud TTS is allowed if free |
| 4 GB VRAM | Whisper medium may not fit with anything else | Start with small; measure; ASR on CPU int8 is the fallback |
| Model ignores tool results | Wrong prices or tiers | Rules live in tools; the eval checks facts in every reply |
| Scope | 15 steps is a lot | Phases 0–2 alone are a complete project; voice and the second client add to it |

---

## 5. What we learned

Filled in as steps finish.

- **Step 00:** strict config validation (`extra="forbid"`) earns its place immediately: a test shows a
  misspelt key (`tool:` for `tools:`) is rejected instead of silently ignored, which is exactly the
  kind of mistake that made the Copilot Studio version's rules drift.
