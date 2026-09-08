# AI Usage Disclosure

Team: Timesware
Members: M.K. Hafees Ahamed (Team Leader), M.F.M. Ayyash, M.A.M. Assadh, M.N. Aamir

Per the competition's AI Usage Policy (section 4.1), this document
discloses which AI tools were used, for what purpose, and which decisions
were made by the team.

## Tools used

- **Claude (Anthropic)** — used as a coding assistant throughout
  development, via chat, primarily by the team leader.
- **OpenRouter (openrouter/free)** — used as the LLM component inside the
  submitted system itself (a runtime component, not a development tool),
  powering judge_sufficiency and synthesize_answer in orchestrator.py.
- **BAAI/bge-large-en-v1.5** (via sentence-transformers) — the embedding
  model used at runtime for retrieval, not a development aid.

## What Claude was used for

- Drafting initial skeleton code for the ingestion pipeline, embedding
  pipeline, and orchestrator loop.
- Debugging real runtime errors encountered during development, including
  a missing import, Windows shell syntax issues, a JSON parsing bug from
  unescaped file-path backslashes, repeated 404s from stale free-model
  IDs (resolved via the openrouter/free auto-router), a mojibake encoding
  bug in the source corpus, and a non-JSON response pattern from certain
  free models (resolved with retry logic).
- Suggesting the file-format deduplication strategy after duplicate
  ephemera content across formats was identified.
- Drafting this documentation set based on the team's actual development
  conversation and real test results.

## Decisions made by the team (not the AI)

- Choice of sub-track (1C).
- Choice to pivot away from Voyage AI to a local embedding model, after
  encountering the payment-card requirement.
- Approval of the deduplication strategy and format preference order
  after reviewing the corpus file listing.
- Choice of stress-test questions used to validate the system, designed
  to probe for fabrication and hallucination risk.
- Manual verification of results: reported successes were checked by the
  team directly against raw corpus source files, not accepted on the
  AI's word alone.
- All architectural trade-off decisions in docs/decisions.md were
  discussed and approved by the team before implementation.

**Note on team contribution division**: role descriptions in
submission_report.docx were drafted to match the team's actual
structure but should be reviewed by all four members for accuracy
before final submission, since day-to-day task division may differ
from the summary given.

## Chat logs

Full exported conversation logs are included in ai_usage/claude.md.
