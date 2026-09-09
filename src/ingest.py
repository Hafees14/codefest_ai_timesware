"""
Corpus Ingestion & Chunking Pipeline
SLIIT Codefest 2026 AI Competition — Ashen Era Archive

Handles: PDF (text + scanned/image-based), DOCX, Markdown, plain text.
Outputs: a list of chunk dicts ready for embedding, saved to chunks.jsonl

Tested against the real Ashen Era Archive corpus; adjust
chunk sizes / metadata fields to match what your retrieval + orchestrator need.
"""

import os
import re
import json
import hashlib
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict

from dotenv import load_dotenv
load_dotenv()  # reads .env from project root (searches parent directories)

# ---------------------------------------------------------------------------
# Dependencies (install as needed):
#   pip install pypdf pdf2image pytesseract python-docx markdown-it-py --break-system-packages
#   pytesseract also needs the `tesseract-ocr` system binary installed for scanned PDFs
# ---------------------------------------------------------------------------

CHUNK_SIZE = 800          # target chars per chunk (tune based on your embedding model)
CHUNK_OVERLAP = 150       # overlap between consecutive chunks
# Paths are resolved relative to the project root by default (this file
# lives in src/, so the project root is one level up). Override via .env
# or environment variables if your corpus lives elsewhere.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CORPUS_DIR = os.environ.get(
    "CORPUS_DIR",
    str(_PROJECT_ROOT / "corpus" / "Ashen_Era_Archive" / "Ashen_Era_Archive"),
)
OUTPUT_FILE = os.environ.get(
    "CHUNKS_FILE",
    str(_PROJECT_ROOT / "data" / "chunks.jsonl"),
)


# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------
@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    source_path: str
    doc_type: str          # "novel" | "wiki" | "codex" | "ephemera" | "image" | etc.
    text: str
    page_or_section: Optional[str] = None
    is_ocr: bool = False    # flag chunks pulled from scanned/OCR'd content — lower trust


# ---------------------------------------------------------------------------
# Per-format extractors
# ---------------------------------------------------------------------------
def extract_pdf(path: Path, force_ocr: bool = False) -> List[dict]:
    """
    Returns list of {"text": str, "page": int, "is_ocr": bool}
    If force_ocr is True (e.g. filename matches *.scan.pdf), every page is OCR'd
    without bothering to try normal text extraction first.
    Otherwise tries normal text extraction, falling back to OCR per-page if a
    page has near-zero extractable text.
    """
    from pypdf import PdfReader

    results = []
    reader = PdfReader(str(path))
    for i, page in enumerate(reader.pages):
        if force_ocr:
            ocr_text = ocr_pdf_page(path, i)
            results.append({"text": ocr_text, "page": i + 1, "is_ocr": True})
            continue
        text = (page.extract_text() or "").strip()
        if len(text) > 30:
            results.append({"text": text, "page": i + 1, "is_ocr": False})
        else:
            ocr_text = ocr_pdf_page(path, i)
            results.append({"text": ocr_text, "page": i + 1, "is_ocr": True})
    return results


def fix_mojibake(text: str) -> str:
    """Fix common UTF-8-decoded-as-Latin-1 double-encoding artifacts
    (e.g. 'â€™' instead of a right single quote) that pytesseract/OCR
    sometimes produces depending on the image's embedded encoding."""
    try:
        return text.encode("latin-1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text  # text wasn't actually double-encoded; leave as-is


def ocr_pdf_page(path: Path, page_index: int) -> str:
    """Rasterize a single PDF page and run OCR on it."""
    from pdf2image import convert_from_path
    import pytesseract

    images = convert_from_path(str(path), first_page=page_index + 1, last_page=page_index + 1)
    if not images:
        return ""
    raw = pytesseract.image_to_string(images[0]).strip()
    return fix_mojibake(raw)


def extract_docx(path: Path) -> str:
    from docx import Document

    doc = Document(str(path))
    parts = []
    for para in doc.paragraphs:
        if para.text.strip():
            parts.append(para.text.strip())
    # Tables often carry structured facts — don't skip them
    for table in doc.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text.strip() for cell in row.cells)
            if row_text.strip(" |"):
                parts.append(row_text)
    return fix_mojibake("\n\n".join(parts))


def extract_markdown(path: Path) -> str:
    return fix_mojibake(path.read_text(encoding="utf-8", errors="ignore"))


def extract_plain_text(path: Path) -> str:
    return fix_mojibake(path.read_text(encoding="utf-8", errors="ignore"))


def extract_image(path: Path) -> str:
    """OCR a standalone image file (e.g. a scanned letter saved as .png/.jpg)."""
    import pytesseract
    from PIL import Image

    img = Image.open(str(path))
    raw = pytesseract.image_to_string(img).strip()
    return fix_mojibake(raw)


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------
def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Simple sliding-window chunking on paragraph boundaries where possible."""
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) <= chunk_size:
        return [text] if text else []

    paragraphs = text.split("\n\n")
    chunks, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= chunk_size:
            current = f"{current}\n\n{para}".strip()
        else:
            if current:
                chunks.append(current)
            # start new chunk, carrying overlap from the end of the previous one
            overlap_text = current[-overlap:] if current else ""
            current = f"{overlap_text}\n\n{para}".strip()
    if current:
        chunks.append(current)
    return chunks


def make_chunk_id(doc_id: str, index: int) -> str:
    return hashlib.md5(f"{doc_id}-{index}".encode()).hexdigest()[:12]


# ---------------------------------------------------------------------------
# Doc-type classification (adjust based on actual folder structure in the zip)
# ---------------------------------------------------------------------------
def classify_doc_type(path: Path) -> str:
    parts = [p.lower() for p in path.parts]
    if "chronicles" in parts:
        return "novel"
    if "wiki" in parts:
        return "wiki"
    if "codex" in parts:
        return "codex"
    if "ephemera" in parts:
        return "ephemera"
    if "images" in parts or path.suffix.lower() in (".png", ".jpg", ".jpeg"):
        return "image"
    return "unknown"


# ---------------------------------------------------------------------------
# Dedup: many ephemera docs exist as BOTH .docx and .pdf (same content).
# Ingesting both would double-count the same document as two "independent"
# sources, which corrupts cross-referencing (1B) and sufficiency judgments (1C).
# Preference order per logical document: .docx > .md > .pdf (non-scan) > .txt
# A ".scan.pdf" is NOT a duplicate of its plain .pdf sibling if one exists —
# treat those as distinct (a scanned facsimile vs. a clean transcript may
# genuinely differ, and the corpus intentionally varies source reliability).
# ---------------------------------------------------------------------------
FORMAT_PREFERENCE = {".docx": 0, ".md": 0, ".markdown": 0, ".pdf": 1, ".txt": 2}


def logical_doc_key(path: Path) -> str:
    """Group files that represent the same underlying document.
    'contract_concerning_x.docx' and 'contract_concerning_x.pdf' share a key.
    'contract_concerning_x.scan.pdf' gets its own key (it's a distinct scan)."""
    name = path.name.lower()
    if name.endswith(".scan.pdf"):
        return str(path)  # scans are never deduped away
    stem = path.stem  # strips one suffix, e.g. "contract_concerning_x"
    return str(path.parent / stem)


def select_files_to_ingest(files: List[Path]) -> List[Path]:
    """Given all files, drop format-duplicates, keeping the preferred format
    per logical document. Prints what was skipped so the team can sanity-check."""
    groups: Dict[str, List[Path]] = {}
    for f in files:
        groups.setdefault(logical_doc_key(f), []).append(f)

    selected = []
    for key, group in groups.items():
        if len(group) == 1:
            selected.append(group[0])
            continue
        group_sorted = sorted(group, key=lambda p: FORMAT_PREFERENCE.get(p.suffix.lower(), 99))
        chosen = group_sorted[0]
        skipped = [p for p in group_sorted if p != chosen]
        print(f"[dedup] {chosen.name} kept; skipped duplicate(s): {[p.name for p in skipped]}")
        selected.append(chosen)
    return selected


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------
def process_file(path: Path) -> List[Chunk]:
    suffix = path.suffix.lower()
    doc_id = str(path.relative_to(CORPUS_DIR))
    doc_type = classify_doc_type(path)
    chunks: List[Chunk] = []

    try:
        if suffix == ".pdf":
            is_scan_named = path.name.lower().endswith(".scan.pdf")
            pages = extract_pdf(path, force_ocr=is_scan_named)
            for page_data in pages:
                for i, piece in enumerate(chunk_text(page_data["text"])):
                    chunks.append(Chunk(
                        chunk_id=make_chunk_id(doc_id, len(chunks)),
                        doc_id=doc_id,
                        source_path=str(path),
                        doc_type=doc_type,
                        text=piece,
                        page_or_section=f"page {page_data['page']}",
                        is_ocr=page_data["is_ocr"],
                    ))
        elif suffix == ".docx":
            text = extract_docx(path)
            for piece in chunk_text(text):
                chunks.append(Chunk(
                    chunk_id=make_chunk_id(doc_id, len(chunks)),
                    doc_id=doc_id, source_path=str(path), doc_type=doc_type,
                    text=piece,
                ))
        elif suffix in (".md", ".markdown"):
            text = extract_markdown(path)
            for piece in chunk_text(text):
                chunks.append(Chunk(
                    chunk_id=make_chunk_id(doc_id, len(chunks)),
                    doc_id=doc_id, source_path=str(path), doc_type=doc_type,
                    text=piece,
                ))
        elif suffix == ".txt":
            text = extract_plain_text(path)
            for piece in chunk_text(text):
                chunks.append(Chunk(
                    chunk_id=make_chunk_id(doc_id, len(chunks)),
                    doc_id=doc_id, source_path=str(path), doc_type=doc_type,
                    text=piece,
                ))
        elif suffix in (".png", ".jpg", ".jpeg"):
            text = extract_image(path)
            for piece in chunk_text(text):
                chunks.append(Chunk(
                    chunk_id=make_chunk_id(doc_id, len(chunks)),
                    doc_id=doc_id, source_path=str(path), doc_type=doc_type,
                    text=piece, is_ocr=True,
                ))
        else:
            print(f"[skip] Unhandled file type: {path}")
    except Exception as e:
        print(f"[error] Failed on {path}: {e}")

    return chunks


def run_ingestion(corpus_dir: str = CORPUS_DIR, output_file: str = OUTPUT_FILE):
    corpus_path = Path(corpus_dir)
    all_chunks: List[Chunk] = []

    files = [
        p for p in corpus_path.rglob("*")
        if p.is_file()
        and p.suffix.lower() != ".json"
        and p.name.lower() != "readme.txt"
    ]
    print(f"Found {len(files)} files in corpus (before dedup).")
    files = select_files_to_ingest(files)
    print(f"{len(files)} files remain after dedup.")

    for i, path in enumerate(files, 1):
        chunks = process_file(path)
        all_chunks.extend(chunks)
        if i % 20 == 0 or i == len(files):
            print(f"Processed {i}/{len(files)} files, {len(all_chunks)} chunks so far.")

    # Ensure the output directory exists — a fresh clone won't have data/
    # created yet, and open() does not create parent directories itself.
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(asdict(chunk), ensure_ascii=False) + "\n")

    print(f"\nDone. {len(all_chunks)} total chunks written to {output_file}")
    ocr_count = sum(1 for c in all_chunks if c.is_ocr)
    print(f"  {ocr_count} chunks came from OCR (scanned pages/images) — flagged is_ocr=True")


if __name__ == "__main__":
    run_ingestion()
