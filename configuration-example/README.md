# Configuration Example

This folder shows the configuration a fresh clone of this repo needs to
run, without any real secrets committed.

## Required environment variables

See .env.example in the project root — copy it to .env and fill in your
own free OpenRouter API key (https://openrouter.ai, no card required).

## Required local paths

The following scripts have hardcoded Windows paths near the top that must
be updated to match your own machine's project location before running:

- src/ingest.py — CORPUS_DIR, OUTPUT_FILE
- src/embed.py — CHUNKS_FILE, CHROMA_DIR
- src/orchestrator.py — none (reads via embed.py's search())
- src/run_sample_questions.py — SAMPLE_QUESTIONS_FILE, OUTPUT_FILE
- src/stress_test.py — OUTPUT_FILE

## Model configuration

- Embedding model: BAAI/bge-large-en-v1.5 (downloaded automatically on
  first run of embed.py, no configuration needed — swap to
  BAAI/bge-small-en-v1.5 in embed.py if running on a slower machine).
- LLM: OpenRouter's openrouter/free auto-router (no model ID
  configuration needed — see docs/decisions.md for why).

## System dependencies

- Tesseract OCR (must be on PATH — verify with `tesseract --version`)
- Poppler (must be on PATH — verify with `pdftoppm -h`)
