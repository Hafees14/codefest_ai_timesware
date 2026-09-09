# Key Technical Decisions

## 1. Local embeddings instead of Voyage AI
Voyage's free tier requires a payment card for usable rate limits (3 RPM
without one — embedding ~5,900 chunks would take over an hour and risk
exhausting retries). No team member wanted to add a card. Switched to
sentence-transformers (BAAI/bge-large-en-v1.5) running locally: no rate
limit, no card, no per-token cost, at the cost of a one-time ~1.3GB
download and slower CPU throughput (~70 minutes for the full corpus).

## 2. openrouter/free router instead of a pinned free model
Three different hardcoded free model IDs 404'd within the same day as
OpenRouter's free lineup rotated. Switched to openrouter/free, which
auto-selects a currently live free model per request. Trade-off: less
consistent behavior per call (occasionally a non-JSON response), mitigated
with automatic retry.

## 3. Deduplicating same-content files across formats
Many ephemera documents exist as duplicate content across .docx/.pdf/.txt.
Ingesting all copies would let the orchestrator mistake the same document
counted twice for two independent corroborating sources — directly
undermining the source-reliability reasoning the corpus is designed to
test. Kept the cleanest format per logical document (docx/md > pdf > txt).

## 4. Forcing OCR by filename convention (*.scan.pdf)
The corpus creators used this naming convention deliberately. Trusting it
directly is faster and more reliable than a length-based heuristic.

## 5. Fixing a mojibake encoding bug present in the source corpus
The corpus's own source files contain double-encoded characters. Verified
by inspecting raw .md source files directly. Fixed with a re-decoding
pass (encode Latin-1, decode UTF-8) across every extractor.

## 6. Sanitizing LLM JSON output before parsing
The judge_sufficiency step requires structured JSON. One model included a
Windows-style file path directly in its reasoning text, which is invalid
inside a JSON string (a lone backslash before a letter is not a valid
escape). Handled generically since this pipeline works with real Windows
paths throughout.

## 7. Iteration cap of 5 searches per question
Balances thoroughness against cost/latency. In stress testing, questions
requiring multiple hops used the full 5 iterations and still correctly
reported "the record doesn't say" rather than fabricating once the cap
was hit — the cap is a safety bound, not a forced-answer trigger.

## 8. Independent stopping signal alongside the LLM's sufficiency self-report

**Decision**: Add a code-level check (`chunks_are_near_duplicate`) that
compares each iteration's retrieved chunks against all prior iterations'
retrievals. If a reformulated query returns substantially the same
evidence as a previous search, the loop stops regardless of what the
LLM's `judge_sufficiency` call reports.

**Why**: Originally, the only stopping mechanism was the LLM's own
`"sufficient": true/false` self-report, plus the hard `MAX_ITERATIONS`
cap. This meant there was no independently verifiable signal for "this
search direction is exhausted" — an internal review of the codebase
correctly identified this as the single biggest gap between this system
and an "ideal" 1C implementation: every planning, analysis, and
stopping decision was delegated to one unstructured LLM JSON response.

**What this does and doesn't fix**: this is a narrow, honest
improvement — it catches the specific failure mode where a
reformulated query is semantically different in wording but retrieves
the same evidence (a real risk given the corpus's dense
cross-referencing). It does **not** add a full evidence-coverage
checklist, entity/relationship tracking, or a structured
missing-information representation — the sufficiency judgment itself is
still one LLM call. That remains an honest limitation, not something to
oversell in the report or demo.

## 9. Explicit query-planning step before the first search

**Decision**: Add `plan_initial_query()` — an LLM call that extracts key
named entities/concepts from the question and proposes a focused initial
search query, run once before the first retrieval. Replaces sending the
raw question verbatim as the very first search.

**Why**: A prior internal review correctly identified that this system
had no code answering "how do you decide where to look" for the first
search — it was always just the raw question. This is a direct,
minimal response to that specific gap.

**Honest scope**: this is still an LLM call, not a symbolic
entity-extraction pipeline or a structured plan format beyond a flat
list of entity strings. It should be described as "a real, separate
planning step" — not as solving query planning in general. If the LLM's
entity extraction is poor for a given question, the initial query may be
no better (or occasionally worse) than the raw question; a fallback to
the raw question on any planning failure is included specifically to
avoid this becoming a new single point of failure.

## 10. Hybrid dense + BM25 retrieval via reciprocal-rank fusion

**Decision**: `embed.py`'s `search()` now combines the existing dense
(semantic) search with a BM25 keyword search over the same chunks,
merging results via simple reciprocal-rank fusion (sum of 1/rank across
both lists). Pure dense search remains available via `use_hybrid=False`
for comparison.

**Why**: The corpus contains OCR'd scans, tables, and mixed-reliability
ephemera. Dense embeddings can miss exact matches on proper nouns,
dates, or unusual spellings that a keyword-based signal catches
reliably — a known weakness of embedding-only retrieval that a prior
review specifically flagged as unaddressed, given the corpus's stated
difficulty profile.

**Honest scope**: this is intentionally simple rank fusion, not a
trained reranker or a learned fusion weight — chosen deliberately as a
low-risk, cheaply-verifiable addition given limited remaining time,
rather than introducing a new ML component whose behavior would need
separate validation before submission. It has not been benchmarked
against the pure-dense baseline on real corpus queries to confirm it
improves answer quality; it is a reasonable, well-motivated addition,
not a proven one.
