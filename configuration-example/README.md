# Configuration Example

All paths default to sensible project-relative locations computed at
runtime — **no source file editing is required** for a standard setup
where `corpus/` sits at the project root alongside `src/`, `data/`, and
`output/`. Override any of these via `.env` only if your layout differs.

## Required environment variables

See `.env.example` in the project root — copy to `.env` and fill in a
free OpenRouter API key (https://openrouter.ai, no card required).

## Optional path overrides (only needed if your layout differs)

Each variable below has a working default; set it in `.env` only to
change that default.

| Variable | Used by | Default |
|---|---|---|
| `CORPUS_DIR` | src/ingest.py | `<project_root>/corpus/Ashen_Era_Archive/Ashen_Era_Archive` |
| `CHUNKS_FILE` | src/ingest.py, src/embed.py | `<project_root>/data/chunks.jsonl` |
| `CHROMA_DIR` | src/embed.py | `<project_root>/data/chroma_db` |
| `SAMPLE_QUESTIONS_FILE` | src/run_sample_questions.py | `<project_root>/corpus/Ashen_Era_Archive/Ashen_Era_Archive/sample_questions.json` |
| `SAMPLE_RESULTS_OUTPUT` | src/run_sample_questions.py | `<project_root>/output/sample_question_results.json` |
| `STRESS_TEST_OUTPUT` | src/stress_test.py | `<project_root>/output/stress_test_results.json` |
| `STRESS_TEST_ROUND2_OUTPUT` | src/stress_test_round2.py | `<project_root>/output/stress_test_round2_results.json` |

## Model configuration

- Embedding: BAAI/bge-large-en-v1.5 (auto-downloaded on first run of embed.py)
- LLM: OpenRouter's openrouter/free auto-router (no model ID needed)

## System dependencies

- Tesseract OCR (verify: `tesseract --version`)
- Poppler (verify: `pdftoppm -h`)
