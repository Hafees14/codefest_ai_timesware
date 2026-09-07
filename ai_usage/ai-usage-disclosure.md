# AI Usage Disclosure

Per the competition's AI Usage Policy (section 4.1), this document
discloses which AI tools were used, for what purpose, and which decisions
were made by the team.

## Tools used

- **Claude (Anthropic)** — used as a coding assistant throughout
  development, via chat.
- **OpenRouter (`openrouter/free`)** — used as the LLM component *inside
  the submitted system itself* (not a development tool — this is part of
  the product's runtime architecture, powering `judge_sufficiency` and
  `synthesize_answer` in `orchestrator.py`).
- **BAAI/bge-large-en-v1.5** (via `sentence-transformers`) — the
  embedding model used at runtime for retrieval, not a development aid.

## What Claude was used for

- Drafting initial skeleton code for the ingestion pipeline, embedding
  pipeline, and orchestrator loop, based on the team's chosen sub-track
  (1C) and architecture direction.
- Debugging real runtime errors encountered during development, including:
  - a missing Dict import
  - Windows shell syntax confusion (cmd.exe vs. PowerShell environment
    variables)
  - a JSON parsing bug caused by unescaped backslashes in Windows file
    paths embedded in LLM responses
  - repeated 404 errors from hardcoded OpenRouter free-model IDs going
    stale, resolved by switching to the openrouter/free auto-router
  - a mojibake encoding bug discovered in the source corpus itself, fixed
    with a re-decoding pass
  - a non-JSON "User Safety: safe" response pattern from certain free
    models, resolved by adding retry logic
- Suggesting the file-format deduplication strategy after the team
  reported that many ephemera documents exist as duplicate content across
  .docx/.pdf/.txt.
- Drafting this documentation set (README, architecture, decisions,
  limitations, this disclosure) based on the team's actual development
  conversation and real test results, not generic template content.

## Decisions made by the team (not the AI)

- **Choice of sub-track (1C)**.
- **Choice to pivot away from Voyage AI to a local embedding model**,
  after encountering the payment-card requirement and deciding as a team
  that no member wanted to add a card for this.
- **Approval of the deduplication strategy** and the format preference
  order (docx/md > pdf > txt) after reviewing the actual corpus file
  listing.
- **Choice of stress-test questions** used to validate the system beyond
  the two officially-tagged 1C sample questions — these were designed by
  the team to specifically probe for fabrication and hallucination risk
  (e.g., asking about a possible causal link between two real corpus
  entities, to see whether the system would invent a connection that
  isn't actually documented).
- **Manual verification of results**: every reported "the system got this
  right" claim in docs/limitations.md and the submission report was
  checked by a team member directly against the raw corpus source files
  (e.g., wiki/crookgate_keep.md), not accepted on the AI's word alone.
- **All architectural trade-off decisions** documented in
  docs/decisions.md were discussed and approved by the team before
  implementation — Claude proposed options and explained trade-offs;
  the team chose the direction in each case.

## Chat logs

Full exported conversation logs are included in ai_usage/chat_logs/ as
plain text, per the competition's requirement.
