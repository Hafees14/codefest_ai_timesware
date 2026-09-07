# Architecture

## Overview

The system has three stages: **ingest** (parse the corpus into text chunks),
**embed** (turn chunks into a searchable vector store), and **orchestrate**
(the actual sub-track 1C iterative search loop).

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐     ┌────────────────┐
│   corpus/   │ ──> │  ingest.py   │ ──> │   embed.py    │ ──> │ orchestrator.py│
│ (415 docs,  │     │              │     │               │     │                │
│ mixed format│     │ parse, OCR,  │     │ local embed   │     │ iterative      │
│  and scans) │     │ dedupe,      │     │ model + Chroma│     │ retrieve/judge/│
│             │     │ fix encoding │     │ vector store  │     │ refine loop    │
└─────────────┘     └──────────────┘     └───────────────┘     └────────────────┘
                            │                    │                      │
                            ▼                    ▼                      ▼
                     data/chunks.jsonl    data/chroma_db/      cited final answer
```

## Stage 1: Ingestion (`ingest.py`)

Walks the corpus directory and processes every file by type:

- **PDF**: native text extraction via `pypdf`. Files named `*.scan.pdf` are
  detected by filename and force full-page OCR (via `pdf2image` +
  `pytesseract`) rather than attempting native extraction, since these are
  genuine scanned images with no embedded text layer.
- **DOCX**: paragraph and table text extracted via `python-docx`. Tables are
  included explicitly — the codex documents store a lot of structured data
  in tables that would otherwise be silently dropped.
- **Markdown / plain text**: read directly.
- **Standalone images**: OCR'd via `pytesseract`.

**Deduplication**: many ephemera documents exist in multiple formats
(`.docx` + `.pdf`, or `.pdf` + `.txt`) with identical content. Ingesting
both would double-count the same document as two independent sources,
which would corrupt cross-referencing in the orchestrator (an LLM might
treat "two documents agree" as corroboration when it's actually the same
document counted twice). The pipeline groups files by logical document
name and keeps only the cleanest format (docx/md > pdf > txt), logging
every skip for auditability. A `.scan.pdf` is *not* deduped against its
plain `.pdf` sibling if one exists — these can be genuinely different
sources (a clean transcript vs. a scanned facsimile).

**Chunking**: paragraph-aware sliding window (~800 chars, 150 char overlap)
to avoid splitting facts mid-sentence.

**Encoding fix**: the source corpus files contain a baked-in mojibake bug
(UTF-8 text that was double-encoded via Latin-1 at some point in the
corpus's own generation pipeline, producing sequences like `a e (tm)` in
place of a plain apostrophe). A `fix_mojibake()` pass re-decodes affected
text across every extractor. Verified against the raw corpus files
directly — the corruption is present in the original `.md`/`.docx` files
themselves, not introduced by this pipeline's extraction.

**Output**: `data/chunks.jsonl` — one JSON object per chunk, with
`chunk_id`, `doc_id`, `source_path`, `doc_type` (novel/wiki/codex/ephemera/
image), `text`, `page_or_section`, and `is_ocr` (flags text that came
through OCR rather than native extraction, since OCR text is noisier and
this matters for source-reliability reasoning downstream).

## Stage 2: Embedding (`embed.py`)

Each chunk is embedded using a local `sentence-transformers` model
(`BAAI/bge-large-en-v1.5`) and stored in a local Chroma vector store with
its metadata (`doc_type`, `is_ocr`, source path) attached.

Chosen over a hosted embedding API (Voyage AI, which the competition's
appendix recommends) specifically to avoid the payment-card requirement —
see decisions.md for the full reasoning.

The build process is resumable: chunks already present in the collection
(matched by `chunk_id`) are skipped on a re-run, so an interrupted embed
job doesn't need to restart from zero.

## Stage 3: Orchestration (`orchestrator.py`) — the core 1C logic

This is the sub-track's central requirement: an assistant that searches
iteratively, evaluates its own progress, and decides when to keep going or
stop.

```
question
   |
   v
vector_search()  <-----------------+
   |                                |
   v                                |
judge_sufficiency()  (LLM call)     |
   |                                |
   +-- sufficient? --No--> refine query --+
   |
  Yes (or max iterations reached)
   |
   v
synthesize_answer()  (LLM call)
   |
   v
final answer + full search trace
```

- **`vector_search`**: retrieves the top-k most relevant chunks for the
  current query from the Chroma store.
- **`judge_sufficiency`**: an LLM call that looks at the question and
  everything retrieved so far, and decides: is this enough to answer, or
  is there a specific gap? If there's a gap, it proposes a targeted
  follow-up query rather than just repeating the original question.
- **`synthesize_answer`**: once sufficient (or the iteration cap is hit),
  a final LLM call answers the question strictly from the accumulated
  evidence, citing sources and explicitly flagging any conflicts between
  sources rather than silently picking one.
- **`SearchTrace`**: every iteration's query, reasoning, and sufficiency
  verdict is logged, giving a full audit trail of why the system searched
  what it searched — this is also the evidence trail for the
  competition's "Human-AI collaboration quality" and "technical judgment"
  rubric criteria.

**LLM access**: OpenRouter's `openrouter/free` router, which automatically
selects a live free model per request rather than pinning one specific
model ID (see decisions.md — free model availability rotates too
frequently for a hardcoded slug to survive a two-week build).

**Resilience**: JSON responses are sanitized (LLMs occasionally emit
invalid escape sequences, e.g. quoting a Windows file path with a bare
backslash) and retried if a response doesn't look like JSON at all (the
free router occasionally lands on a model that returns something like a
raw safety-classifier verdict instead of following the prompt).

## Data flow summary

| File | Produced by | Consumed by |
|---|---|---|
| `data/chunks.jsonl` | `ingest.py` | `embed.py` |
| `data/chroma_db/` | `embed.py` | `orchestrator.py` (via `search()`) |
| `output/*.json` | `run_sample_questions.py`, `stress_test.py` | manual review, report evidence |
