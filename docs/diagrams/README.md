# Diagrams

Place architecture/design diagram image files here (PNG, SVG, or
draw.io/Excalidraw exports).

The ASCII-art pipeline diagrams already embedded in ../architecture.md
are sufficient for text-based understanding, but a clean visual diagram
(e.g. exported from Excalidraw, draw.io, or Mermaid) should be added here
and linked from ../architecture.md for the submission report and demo
video, per the deliverable requirements (section 5.2: "Include
architecture and design diagrams").

Suggested diagrams to create:
1. Pipeline overview — corpus -> ingest.py -> embed.py -> orchestrator.py -> answer
2. Orchestrator loop detail — the retrieve / judge_sufficiency / refine /
   synthesize cycle with the iteration cap and retry logic shown
