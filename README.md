# Ashen Era Archive — Iterative Document Search Assistant

**SLIIT Codefest 2026 AI Competition — Sub-track 1C: Searching the Way a Human Does**

An AI assistant that answers questions over the Ashen Era Archive (a fictional
fantasy corpus of 415 documents, ~1,277 pages) by iteratively searching,
evaluating what it has learned, and refining its own queries until it has
enough evidence to answer — or until it can honestly report that the archive
doesn't contain an answer.

## How it works

```
corpus/  →  ingest.py  →  data/chunks.jsonl  →  embed.py  →  data/chroma_db/
                                                                     │
                                                                     ▼
                                                          orchestrator.py
                                                    (retrieve → judge → refine → repeat)
                                                                     │
                                                                     ▼
                                                            cited final answer
```

See [docs/architecture.md](docs/architecture.md) for the full pipeline
explanation and [docs/decisions.md](docs/decisions.md) for why it's built
this way.

## Setup

### 1. Install system dependencies (Windows)

- **Tesseract OCR**: https://github.com/UB-Mannheim/tesseract/wiki
- **Poppler**: https://github.com/oschwartz10612/poppler-windows/releases
  (add the `bin` folder to PATH, or both tools work automatically if already
  on PATH — verify with `tesseract --version` and `pdftoppm -h`)

### 2. Install Python dependencies

```powershell
pip install pypdf pdf2image pytesseract python-docx Pillow --break-system-packages
pip install sentence-transformers chromadb --break-system-packages
pip install openai python-dotenv --break-system-packages
```

### 3. Get a free OpenRouter API key

Sign up at [openrouter.ai](https://openrouter.ai) (no card required). Create
an API key from account settings.

### 4. Configure your environment

Copy `.env.example` to `.env` in the project root and fill in your key:

```
OPENROUTER_API_KEY=your-key-here
```

`.env` is git-ignored — never commit real keys.

### 5. Get the corpus

Download and extract the Ashen Era Archive corpus into `corpus/`. Confirm
the path in `CORPUS_DIR` at the top of `src/ingest.py` matches where it
landed (extraction sometimes creates a doubled nested folder — point at the
innermost folder containing `chronicles/`, `codex/`, `ephemera/`, `wiki/`,
`images/`).

## Running the pipeline

From the `src/` folder, run each step in order:

```powershell
# 1. Parse the corpus into text chunks (~5,900 chunks from ~320 files)
python ingest.py

# 2. Embed all chunks into a local vector store (no API key needed —
#    runs entirely on your machine, first run downloads the model ~1.3GB)
python embed.py

# 3. Test the orchestrator on a single question
python orchestrator.py

# 4. Batch-test against the official 1C sample questions
python run_sample_questions.py

# 5. Run additional hand-written stress-test questions
python stress_test.py
```

Each script is resumable / re-runnable — `ingest.py` and `embed.py` won't
redo completed work if interrupted.

## Project structure

```
codefest-ai/
├── corpus/              # Ashen Era Archive (extracted, read-only)
├── data/                # generated: chunks.jsonl, chroma_db/ (git-ignored)
├── output/              # generated: test run results (git-ignored)
├── src/
│   ├── ingest.py         # corpus → chunks.jsonl
│   ├── embed.py          # chunks.jsonl → Chroma vector store
│   ├── orchestrator.py   # the core 1C iterative search loop
│   ├── run_sample_questions.py
│   └── stress_test.py
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   └── limitations.md
├── ai_usage/
│   ├── ai-usage-disclosure.md
│   └── chat_logs/
├── .env.example
├── .gitignore
└── README.md
```

## Known limitations

See [docs/limitations.md](docs/limitations.md) — summary: the free LLM
router occasionally returns non-JSON responses (auto-retried), and very
easy questions can resolve in a single search iteration where a harder
question would require several.
