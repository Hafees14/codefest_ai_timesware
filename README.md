# Ashen Era Archive — Iterative Document Search Assistant

**SLIIT Codefest 2026 AI Competition — Sub-track 1C: Searching the Way a Human Does**
**Team: Timesware**

An AI assistant that answers questions over the Ashen Era Archive by iteratively
searching, evaluating what it has learned, and refining its own queries until it
has enough evidence to answer — or until it can honestly report that the archive
doesn't contain an answer.

## How it works

```
corpus/  ->  ingest.py  ->  data/chunks.jsonl  ->  embed.py  ->  data/chroma_db/
                                                                       |
                                                                       v
                                                            orchestrator.py
                                                  (retrieve -> judge -> refine -> repeat)
                                                                       |
                                                                       v
                                                              cited final answer
```

See [docs/architecture.md](docs/architecture.md) for the full pipeline
explanation and [docs/decisions.md](docs/decisions.md) for why it's built this way.

## Setup

### 1. Install system dependencies (Windows)
- Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
- Poppler: https://github.com/oschwartz10612/poppler-windows/releases
  (add the bin folder to PATH — verify with `tesseract --version` and `pdftoppm -h`)

### 2. Install Python dependencies
```powershell
pip install pypdf pdf2image pytesseract python-docx Pillow --break-system-packages
pip install sentence-transformers chromadb --break-system-packages
pip install openai python-dotenv --break-system-packages
```

### 3. Get a free OpenRouter API key
Sign up at openrouter.ai (no card required). Create an API key.

### 4. Configure environment
Copy `.env.example` to `.env` and fill in your key. `.env` is git-ignored.

### 5. Get the corpus
Extract the Ashen Era Archive into `corpus/`. Update `CORPUS_DIR` in
`src/ingest.py` to point at the innermost folder containing chronicles/,
codex/, ephemera/, wiki/, images/.

## Running the pipeline

```powershell
python ingest.py                  # corpus -> chunks.jsonl
python embed.py                   # chunks.jsonl -> Chroma vector store
python orchestrator.py            # test a single question
python run_sample_questions.py    # batch test official 1C sample questions
python stress_test.py             # hand-written multi-hop stress tests
python stress_test_round2.py      # adversarial robustness tests
```

Each script is resumable — ingest.py and embed.py won't redo completed work
if interrupted.

## Project structure

```
codefest-ai/
├── corpus/              # Ashen Era Archive (read-only)
├── data/                # generated: chunks.jsonl, chroma_db/ (git-ignored)
├── output/               # generated: test results (git-ignored)
├── src/                  # ingest.py, embed.py, orchestrator.py, test scripts
├── docs/                 # architecture, decisions, limitations, diagrams, demo script
├── ai_usage/             # disclosure, chat logs, context, skills
├── configuration-example/
├── .env.example
├── .gitignore
└── README.md
```

## Known limitations

See [docs/limitations.md](docs/limitations.md).
