# Configuration Example

## Required environment variables
See .env.example in the project root — copy to .env and fill in a free
OpenRouter API key (https://openrouter.ai, no card required).

## Required local paths
Update hardcoded Windows paths near the top of these scripts to match
your machine:
- src/ingest.py — CORPUS_DIR, OUTPUT_FILE
- src/embed.py — CHUNKS_FILE, CHROMA_DIR
- src/run_sample_questions.py — SAMPLE_QUESTIONS_FILE, OUTPUT_FILE
- src/stress_test.py, src/stress_test_round2.py — OUTPUT_FILE

## Model configuration
- Embedding: BAAI/bge-large-en-v1.5 (auto-downloaded on first run)
- LLM: OpenRouter's openrouter/free auto-router (no model ID needed)

## System dependencies
- Tesseract OCR (verify: tesseract --version)
- Poppler (verify: pdftoppm -h)
