# AI Development Context

Team: Timesware — SLIIT Codefest 2026, Sub-track 1C.

## Competition context provided to Claude

- Full challenge document (rules, deliverables, evaluation rubric, AI
  usage policy, free-API-access appendix) shared at the start.
- Corpus structure (chronicles/, codex/, ephemera/, wiki/, images/; ~415
  documents, mixed formats) explored and shared incrementally as
  discovered on disk.

## Team environment

- Development on Windows (PowerShell), project rooted at codefest-ai/
  with corpus/, data/, output/, src/ subfolders.
- Tesseract OCR and Poppler installed locally for OCR.
- No paid services used — OpenRouter free tier for LLM calls, local
  sentence-transformers for embeddings, local Chroma for the vector store.

## How this context was used

Claude used this context to tailor code to the actual corpus structure
and Windows environment, align technical choices with the competition's
evaluation rubric (prioritizing honest "insufficient evidence" answers
over confident fabrication), and avoid recommending paid services that
would violate the "fully solvable with free resources" constraint.
