# Timesware — Ashen Era Archive Iterative Search Assistant

**SLIIT Codefest 2026 AI Competition — Sub-track 1C: Searching the Way a Human Does**

**Team:** Timesware
**Members:** M.K. Hafees Ahamed (Team Leader), M.F.M. Ayyash, M.A.M. Assadh, M.N. Aamir

---

## What this is

An AI assistant that answers questions over the **Ashen Era Archive** — a
415-document, ~1,277-page fictional fantasy corpus spanning novels, wiki
articles, codexes, and ephemera — by searching the way a human researcher
does: retrieving evidence, judging whether it has enough to answer, and
refining its search when it doesn't, rather than answering from a single
retrieval pass.

The Ashen Era Archive is deliberately interconnected and unreliable: the
same characters, factions, and events surface across multiple document
types, but sources disagree with each other (a tavern ballad versus an
official codex entry), and no single document tells the whole story. This
system is built specifically to chase multi-hop facts across documents,
surface genuine source conflicts instead of silently picking one, and —
its strongest demonstrated trait — **refuse to fabricate an answer when
the evidence genuinely doesn't support one.**

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
                                                        + full search trace
```

Three stages:

1. **Ingestion** — parses all 415 documents across five formats (PDF,
   DOCX, Markdown, plain text, scanned images), with OCR for scanned
   content, deduplication of documents that exist in multiple formats,
   and a fix for a mojibake encoding bug found in the source corpus.
2. **Embedding** — embeds every chunk with a local, free
   `sentence-transformers` model into a local Chroma vector store — no
   API key, no card, no rate limits.
3. **Orchestration** — the core sub-track 1C loop: retrieve relevant
   chunks, have an LLM judge whether they're sufficient to answer, refine
   the query if not (up to 5 iterations), then synthesize a final answer
   that cites sources and explicitly flags conflicts between them.

Full technical detail: [`docs/architecture.md`](docs/architecture.md).
Why it's built this way: [`docs/decisions.md`](docs/decisions.md).
Known limitations, honestly documented: [`docs/limitations.md`](docs/limitations.md).

## Repository structure

This repository follows the competition's required submission layout:

```
Timesware.zip
├── .git/                          # full commit history
├── README.md                      # this file
├── docs/
│   ├── architecture.md            # pipeline design, explained stage by stage
│   ├── decisions.md               # key technical decisions and trade-offs
│   ├── limitations.md             # known limitations, honestly documented
│   └── diagrams/                  # architecture diagram (SVG + PNG)
├── src/                           # ingest.py, embed.py, orchestrator.py, test scripts
├── ai_usage/
│   ├── ai-usage-disclosure.md     # mandatory — what AI tools were used, for what
│   ├── skills/                    # custom AI skills used (none beyond direct prompting)
│   ├── claude.md                  # exported AI chat logs
│   └── context.md                 # project context provided to the AI assistant
├── configuration-example/         # example config and required environment variables
└── submission_report.pdf          # 5-page report: problem, architecture, decisions,
                                    # results, AI usage, team contributions
```

## Setup

### 1. System dependencies (Windows)

- **Tesseract OCR**: https://github.com/UB-Mannheim/tesseract/wiki
  Verify with: `tesseract --version`
- **Poppler**: https://github.com/oschwartz10612/poppler-windows/releases
  Verify with: `pdftoppm -h`

Both must be on your system PATH.

### 2. Python dependencies

```powershell
pip install pypdf pdf2image pytesseract python-docx Pillow --break-system-packages
pip install sentence-transformers chromadb --break-system-packages
pip install openai python-dotenv --break-system-packages
```

### 3. Get a free OpenRouter API key

Sign up at [openrouter.ai](https://openrouter.ai) — no payment card
required. Create an API key from account settings.

### 4. Configure environment

Copy `configuration-example/.env.example` to `.env` in the project root
and add your key:

```
OPENROUTER_API_KEY=your-key-here
```

`.env` is git-ignored — never commit real keys.

### 5. Get the corpus

Download and extract the Ashen Era Archive corpus into a `corpus/`
folder at the project root. Update `CORPUS_DIR` at the top of
`src/ingest.py` to point at the folder directly containing `chronicles/`,
`codex/`, `ephemera/`, `wiki/`, and `images/` (extraction sometimes
produces a doubled nested folder — point past that).

See [`configuration-example/README.md`](configuration-example/README.md)
for the full list of paths each script expects.

## Running the pipeline

From the `src/` folder, run each stage in order:

```powershell
# 1. Parse the corpus into text chunks (~5,900 chunks from ~320 deduped files)
python ingest.py

# 2. Embed all chunks into a local vector store (no API key needed;
#    first run downloads the embedding model, ~1.3GB, then works offline)
python embed.py

# 3. Ask the assistant a single question
python orchestrator.py

# 4. Batch-test against the official sub-track 1C sample questions
python run_sample_questions.py

# 5. Run hand-written multi-hop stress tests
python stress_test.py

# 6. Run additional adversarial robustness tests
python stress_test_round2.py
```

`ingest.py` and `embed.py` are resumable — an interrupted run picks up
where it left off rather than restarting from zero.

## What this system does well

Verified by manually checking outputs against raw corpus source files,
not accepted on the system's own word:

- **Surfaces genuine multi-source conflicts** instead of silently picking
  one answer (e.g. a location's founding year is reported differently by
  its codex entry, an ephemera contract, and its wiki page — the system
  presents all three with an explicit conflict note).
- **Resists fabricating answers under pressure.** When a question asks
  about something the corpus genuinely doesn't record, the system
  exhausts its full search budget trying different angles and then
  honestly reports that the record doesn't say, rather than inventing a
  plausible-sounding narrative.
- **Distinguishes correlation from causation** — e.g. correctly declining
  to infer a historical causal link between two entities that are only
  thematically or physically associated in the source material.
- **Catches false premises** embedded in a question's own phrasing rather
  than answering around them uncritically.

Full test methodology and results are in the submission report and
`docs/limitations.md`.

## AI usage

This project used Claude (Anthropic) as a coding assistant during
development, and uses OpenRouter's free-tier LLM routing and a local
embedding model as runtime components of the submitted system itself.
Full disclosure: [`ai_usage/ai-usage-disclosure.md`](ai_usage/ai-usage-disclosure.md).
Exported chat logs: [`ai_usage/claude.md`](ai_usage/claude.md).

## License / Ownership

Built for SLIIT Codefest 2026 by Team Timesware. All work was completed
within the competition window (28 August – 9 September 2026).
