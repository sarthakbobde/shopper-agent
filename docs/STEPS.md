# Roadmap

Legend: 🧑 = you do it · 🤖 = Claude does it (after explaining the plan and getting your OK) · 🤝 = together

How each step is built and what "done" means: [PLAN.md](PLAN.md).

Stopping after Phase 2 still leaves a complete project; voice and the second client add to it.

## Phase 0 — Foundations
- [x] 🤖 **00 Scaffold** — uv package, `shopper` CLI, `shopper doctor`, paths, config, tests, ruff, CI.
- [x] 🧑 **01 Gemini key and first call** — create the key in Google AI Studio, put it in `.env`, pick the model (ADR-009), one test call.

## Phase 1 — Text agent (the Copilot Studio rebuild)
- [x] 🤝 **02 Data and seed** — SQLite schema, fake Indian retail seed data, fuzzy product search.
- [ ] 🤝 **03 Tools and business rules** — four tools, spend tiers, stock flag, ₹ formatting, rating validation.
- [ ] 🤝 **04 Agent loop and terminal chat** — hand-written Gemini function-calling loop, event log, `shopper chat`.
- [ ] 🤝 **05 Eval harness** — 40 scripted conversations, tool-call accuracy, answer facts, containment.

## Phase 2 — Integrations (the FDE part)
- [ ] 🤝 **06 Batch ingestion** — CSV from a folder, S3 or SFTP; validate, upsert, reject report.
- [ ] 🤝 **07 API, auth and webhooks** — FastAPI with bearer tokens; HMAC-signed, retried webhooks to a mock CRM.
- [ ] 🤝 **08 Web chat** — browser chat page with a feedback form.

## Phase 3 — Voice
- [ ] 🤝 **09 Speech in** — Silero VAD + faster-whisper; WER on English, Hindi and Hinglish clips.
- [ ] 🤝 **10 Speech out and the voice loop** — TTS streamed by sentence over a WebSocket; time to first audio.
- [ ] 🤝 **11 Gemini Live comparison** — same tools on native audio; accuracy, latency and cost side by side.

## Phase 4 — Operate and ship
- [ ] 🤝 **12 Conversation analytics** — containment, escalation, errors, latency, cost; one improvement made from it.
- [ ] 🤝 **13 Second client** — NBFC payment-reminder agent from config, prompt and new tools only.
- [ ] 🤝 **14 Deploy and write-up** — Docker, GCP Cloud Run, Secret Manager, README, demo video.
