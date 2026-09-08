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
