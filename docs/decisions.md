# Key Technical Decisions

This document records the significant technical choices made while building
this system, why they were made, and what alternatives were considered —
per the submission report's requirement to show "what works, what doesn't,
and why."

## 1. Local embeddings instead of Voyage AI

**Decision**: Use `sentence-transformers` with `BAAI/bge-large-en-v1.5`
running locally, instead of the Voyage AI API recommended in the
competition's appendix.

**Why**: Voyage AI's free tier requires a payment card on file to get
usable rate limits (3 requests/minute without one — embedding ~5,900
chunks at that rate would take well over an hour and risks exhausting
retries mid-run). No team member had a card they were comfortable adding
for this. A local model has no rate limit, no card requirement, and no
per-token cost, at the cost of a one-time ~1.3GB model download and
slower embedding throughput on CPU (took roughly 70 minutes for ~5,900
chunks on the development machine).

**Trade-off accepted**: `bge-large-en-v1.5` is a strong open-weight
retrieval model but likely slightly behind Voyage's current-generation
models on retrieval quality. Given the corpus size and question style,
this did not appear to bottleneck answer quality in testing — the
orchestrator successfully retrieved relevant cross-source evidence in
every test case.

## 2. `openrouter/free` router instead of a pinned free model

**Decision**: Call OpenRouter's `openrouter/free` auto-router rather than
hardcoding a specific free model ID (e.g. `meta-llama/llama-3.3-70b-
instruct:free`).

**Why**: During development, three different specific free model IDs
returned 404 errors within the same day as OpenRouter's free lineup
rotated. A hardcoded model slug is not robust to this. `openrouter/free`
automatically selects from whatever free models are currently live and
filters for ones that support the request's requirements (e.g. structured
output).

**Trade-off accepted**: because the router can land on a different
underlying model per call, behavior is less consistent than pinning one
model. Observed in testing: some models occasionally return a
non-JSON response (e.g. a raw safety-classifier verdict like `"User
Safety: safe"`) instead of following the "respond only in JSON"
instruction. Mitigated with automatic retry (see limitations.md) — in
every observed case, a retry succeeded on the next attempt, implying the
router landed on a different, more compliant model.

## 3. Deduplicating same-content files across formats

**Decision**: When the same logical document exists in multiple file
formats (e.g. `contract_concerning_x.docx` and `contract_concerning_x.pdf`
with identical content), keep only the cleanest format and skip the rest,
rather than ingesting all of them.

**Why**: The corpus intentionally varies source reliability as part of
its design (a tavern ballad vs. an official codex entry may disagree).
If the same document is ingested twice under two different filenames,
the orchestrator's sufficiency-judgment and synthesis steps could
mistake "the same document, counted twice" for "two independent sources
that corroborate each other" — undermining the exact source-reliability
reasoning the corpus is testing for.

**Format preference order**: `.docx`/`.md` > `.pdf` > `.txt` (cleanest
structured extraction first). A `.scan.pdf` is never deduped against a
plain `.pdf` sibling — these are treated as potentially distinct sources,
since a scanned facsimile and a clean transcript are not guaranteed to be
identical documents.

## 4. Forcing OCR by filename convention (`*.scan.pdf`)

**Decision**: Detect scanned PDFs by their `.scan.pdf` filename suffix and
force full-page OCR, rather than trying native text extraction first and
falling back to OCR only when extraction yields little text.

**Why**: The corpus creators used this naming convention deliberately.
Trusting it directly is faster (skips a wasted native-extraction attempt
on pages with no text layer) and more reliable than a length-based
heuristic, which could misfire on a page with sparse-but-real text.

## 5. Fixing a mojibake encoding bug present in the source corpus

**Decision**: Apply a `fix_mojibake()` re-decoding pass (encode as
Latin-1, decode as UTF-8) across every text extractor.

**Why**: The corpus's own source files contain double-encoded characters
(smart quotes and dashes rendered as garbled multi-character sequences).
This was verified by inspecting the raw `.md` source files directly — the
corruption exists in the corpus itself, not introduced by this pipeline.
Left unfixed, this would degrade embedding quality (garbled tokens embed
poorly) and make quoted evidence in final answers look unprofessional.

## 6. Sanitizing LLM JSON output before parsing

**Decision**: Before calling `json.loads`, strip markdown code fences and
escape any backslash that isn't part of a valid JSON escape sequence.

**Why**: The `judge_sufficiency` step requires the LLM to return
structured JSON. In testing, one model included a Windows-style file path
directly in its reasoning text (e.g. `ephemera\contract_concerning_x`),
which is invalid inside a JSON string (a lone backslash before a letter
is not a valid escape sequence) and crashed the parser. Since this
pipeline works with real Windows file paths throughout, this failure mode
was likely to recur, so it's handled generically rather than patched for
one specific case.

## 7. Iteration cap of 5 searches per question

**Decision**: `MAX_ITERATIONS = 5` in the orchestrator.

**Why**: Balances thoroughness against cost/latency. In stress testing,
questions that genuinely required multiple hops used the full 5
iterations and still correctly reported "the record doesn't say" rather
than fabricating an answer once the cap was hit — the cap acts as a
safety bound, not a forced-answer trigger. Questions answerable from a
single retrieval correctly stopped after 1 iteration.
