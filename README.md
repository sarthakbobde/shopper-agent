# shopper-agent

A Shoppers Stop retail assistant, rebuilt from a Copilot Studio agent as plain Python on Gemini:
text and voice (English, Hindi, Hinglish), product lookup, customer insights and feedback
capture, plus the work around it that a real deployment needs: batch data ingestion, an
authenticated API, signed webhooks to a CRM, conversation analytics, and a cloud deployment.

The engine is separate from the client. A second client (an NBFC payment-reminder agent) is
configured from the same engine to show that a new deployment is mostly config, prompts and tools.

**Status:** planning. See [docs/STEPS.md](docs/STEPS.md) for the roadmap,
[docs/PLAN.md](docs/PLAN.md) for how each step is built and
[docs/DECISIONS.md](docs/DECISIONS.md) for why.
