# AI Development Context

This file summarizes the project context that was established with Claude
during development — the equivalent of a project brief or system prompt
context, kept here for transparency about what background the AI had when
assisting.

## Competition context provided to Claude

- SLIIT Codefest 2026 AI Competition, Sub-track 1C ("Searching the Way a
  Human Does" — iterative agentic search over the Ashen Era Archive
  corpus).
- Full challenge document (rules, deliverables, evaluation rubric, AI
  usage policy, free-API-access appendix) was shared with Claude at the
  start of the project.
- Corpus structure (chronicles/, codex/, ephemera/, wiki/, images/;
  ~415 documents, mixed PDF/DOCX/MD/TXT/scanned formats) was explored and
  shared incrementally as it was discovered on disk.

## Team environment

- Development on Windows (PowerShell), project rooted at
  `codefest-ai/` with `corpus/`, `data/`, `output/`, `src/` subfolders.
- Tesseract OCR and Poppler installed locally for PDF/image OCR.
- No paid API services used — OpenRouter (free tier) for LLM calls,
  local `sentence-transformers` model for embeddings, local Chroma for
  the vector store.

## How this context was used

Claude used this context to:
- Tailor code to the actual corpus structure and Windows environment
  (e.g. Windows-style paths, PowerShell command syntax, cmd.exe vs.
  PowerShell environment variable differences).
- Align technical choices with the competition's stated evaluation
  rubric (e.g. prioritizing source-reliability reasoning and honest
  "insufficient evidence" answers over confident-sounding fabrication,
  since the corpus is explicitly designed to test this).
- Avoid recommending paid services or approaches that would violate the
  "fully solvable with free resources" constraint in the challenge
  document.
