# Submission Report — Sub-track 1C: Searching the Way a Human Does

**Team:** [TEAM NAME]
**YouTube demo link:** [PASTE UNLISTED LINK HERE]

---

## 1. Problem Statement and Chosen Sub-track

We chose **Sub-track 1C**: build an assistant that answers questions over
the Ashen Era Archive by searching iteratively — deciding where to look,
checking whether it has enough information, and refining its search when
it doesn't, rather than answering from a single retrieval pass.

This matters for the corpus specifically because it is deliberately
interconnected and unreliable: the same entities appear across novels,
wiki articles, codexes, and ephemera, but sources disagree (a tavern
ballad vs. an official codex entry), and no single document tells the
whole story. A single-shot retrieval system cannot reliably surface
conflicting sources or chase a multi-hop fact chain; ours is built
specifically to do both.

## 2. Solution Overview and Architecture

[INSERT DIAGRAM FROM docs/diagrams/ HERE]

Three-stage pipeline:

1. **Ingestion** (src/ingest.py) — parses all 415 documents across five
   formats (PDF, DOCX, Markdown, plain text, scanned images), with OCR for
   scanned content, format deduplication, and a fix for a mojibake
   encoding bug present in the source corpus. Produces ~5,900 text chunks.
2. **Embedding** (src/embed.py) — embeds all chunks with a local
   sentence-transformers model (BAAI/bge-large-en-v1.5) into a local
   Chroma vector store.
3. **Orchestration** (src/orchestrator.py) — the core 1C loop: retrieve
   relevant chunks, have an LLM judge whether they're sufficient to
   answer, refine the query if not, repeat (capped at 5 iterations), then
   synthesize a final cited answer that explicitly flags source conflicts.

Full detail in docs/architecture.md.

## 3. Key Technical Decisions and Why

- **Local embeddings instead of Voyage AI**: Voyage's free tier requires
  a payment card for usable rate limits; we chose a local model to avoid
  this entirely, at the cost of slower one-time embedding throughput.
- **openrouter/free auto-router instead of a pinned model**: specific
  free model IDs went stale (404) within the same day during development;
  the auto-router avoids hardcoding a slug that expires.
- **Format deduplication**: many ephemera documents exist as duplicate
  content across .docx/.pdf/.txt; ingesting all copies would let the
  system mistake one document counted twice for two independent
  corroborating sources.

Full reasoning and trade-offs in docs/decisions.md.

## 4. What Works, What Doesn't, and Limitations

**What works well** (verified by manual spot-checks against raw corpus
files, not just accepted on the system's own word):

- Correctly identifies and reports genuine multi-source conflicts (e.g.
  Gloamreach's founding year: codex says 246 AS, an ephemera contract
  says 286 AS, the wiki says the matter is unresolved — the system
  surfaced all three rather than picking one).
- **Resists fabrication under pressure**: when asked what happened to a
  named individual after a specific in-world event, and the corpus
  genuinely doesn't say, the system iterated the full 5-search cap trying
  different angles and then honestly reported "the record doesn't say"
  rather than inventing a plausible-sounding narrative.
- **Distinguishes correlation from causation**: when asked whether a
  historical event was connected to a location's founding, the system
  noticed the two were merely thematically/physically associated (an
  artifact tied to the event happens to be housed at that location) and
  correctly declined to infer a causal/historical link neither source
  supports.
- Correctly caught a false premise in the framing of one test question,
  refusing to accept the question's built-in assumption once evidence
  contradicted it.

**What doesn't work / known limitations** (full detail in
docs/limitations.md):

- The free LLM router occasionally returns a non-JSON response (observed:
  a stray "User Safety: safe" string) — mitigated with automatic retry,
  which succeeded in every observed case, but the underlying
  inconsistency is a property of the free-tier model pool, not something
  we can fully control.
- Some questions resolve in a single search iteration when the first
  retrieval happens to surface everything needed; this is not a flaw,
  but the system has no mechanism to force a second cross-verifying
  search, so single-iteration answers rely on retrieval luck rather than
  a guaranteed multi-source check.
- Text-only — cannot handle 1A-style questions requiring diagram/image
  reading.
- No automated scoring against a ground-truth answer key; quality
  assessment relied on manual verification against corpus source files.

**Approaches tried and changed:**
- Originally planned to use Voyage AI for embeddings per the challenge
  document's appendix; switched to a local model after hitting the
  payment-card requirement.
- Originally hardcoded a specific free OpenRouter model; switched to the
  openrouter/free router after repeated 404s from a rotating free-tier
  lineup.

## 5. AI Usage Disclosure

See ai_usage/ai-usage-disclosure.md for full detail. Summary: Claude was
used as a coding assistant for drafting skeleton code, debugging, and
documentation; OpenRouter and a local embedding model are runtime
components of the submitted system itself, not development tools.
Architectural trade-off decisions were made by the team; full chat logs
are included in ai_usage/claude.md.

## 6. Team Members, Roles, and Contributions

| Name | Role | Contribution |
|---|---|---|
| [NAME] | [ROLE] | [CONTRIBUTION] |
| [NAME] | [ROLE] | [CONTRIBUTION] |
| [NAME] | [ROLE] | [CONTRIBUTION] |
| [NAME] | [ROLE] | [CONTRIBUTION] |

---

Fill in bracketed placeholders before converting to PDF. Target: 5 pages
max, so trim section 4's examples if space is tight. Keep the
fabrication-resistance and conflict-detection examples, as these are the
strongest evidence for the rubric's "problem understanding & insight" and
"technical execution" criteria.
