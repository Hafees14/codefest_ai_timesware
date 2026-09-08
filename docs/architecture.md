# Architecture

## Overview

Three stages: ingest (parse corpus into chunks), embed (build a searchable
vector store), orchestrate (the sub-track 1C iterative search loop).

See docs/diagrams/architecture.png for the visual pipeline diagram.

## Stage 1: Ingestion (ingest.py)

- PDF: native text via pypdf. Files named *.scan.pdf are detected by filename
  and force full-page OCR (pdf2image + pytesseract) instead of native
  extraction, since these are genuine scanned images with no text layer.
- DOCX: paragraphs and tables via python-docx (tables included explicitly —
  the codex documents store structured data in tables).
- Markdown / plain text: read directly.
- Standalone images: OCR'd via pytesseract.

**Deduplication**: many ephemera documents exist in multiple formats
(.docx + .pdf, or .pdf + .txt) with identical content. Ingesting both would
let the system mistake one document counted twice for two independent
corroborating sources. Files are grouped by logical document name and only
the cleanest format is kept (docx/md > pdf > txt), with every skip logged.
A .scan.pdf is never deduped against its plain .pdf sibling — these may be
genuinely distinct sources.

**Chunking**: paragraph-aware sliding window (~800 chars, 150 char overlap).

**Encoding fix**: the source corpus files contain a baked-in mojibake bug
(UTF-8 text double-encoded via Latin-1, producing garbled character
sequences in place of apostrophes/dashes). A fix_mojibake() pass re-decodes
affected text across every extractor. Verified against the raw corpus files
directly — the corruption exists in the corpus itself, not introduced by
this pipeline.

**Output**: data/chunks.jsonl — chunk_id, doc_id, source_path, doc_type
(novel/wiki/codex/ephemera/image), text, page_or_section, is_ocr.

## Stage 2: Embedding (embed.py)

Each chunk is embedded using a local sentence-transformers model
(BAAI/bge-large-en-v1.5) and stored in a local Chroma vector store with
metadata attached. Chosen over Voyage AI (recommended in the challenge
appendix) specifically to avoid the payment-card requirement for usable
rate limits — see decisions.md. The build is resumable: chunks already
present are skipped on re-run.

## Stage 3: Orchestration (orchestrator.py) — the core 1C logic

- vector_search(): retrieves top-k relevant chunks for the current query.
- judge_sufficiency(): LLM call deciding if evidence is enough, or proposing
  a targeted follow-up query if not.
- synthesize_answer(): final LLM call answering strictly from accumulated
  evidence, citing sources and flagging conflicts explicitly.
- SearchTrace: every iteration's query, reasoning, and verdict is logged,
  giving a full audit trail for the "Human-AI collaboration quality" and
  "technical judgment" rubric criteria.

**LLM access**: OpenRouter's openrouter/free auto-router, which selects a
live free model per request rather than pinning one model ID (free model
availability rotates too frequently for a hardcoded slug to survive
development).

**Resilience**: JSON responses are sanitized (invalid backslash escapes
from embedded file paths) and retried if a response isn't JSON-shaped at
all (the free router occasionally returns a raw safety-classifier string
instead of following the prompt).

## Data flow summary

| File | Produced by | Consumed by |
|---|---|---|
| data/chunks.jsonl | ingest.py | embed.py |
| data/chroma_db/ | embed.py | orchestrator.py |
| output/*.json | test scripts | manual review, report evidence |
