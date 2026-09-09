"""
Embedding & Vector Store Pipeline — LOCAL MODEL VERSION
SLIIT Codefest 2026 AI Competition — Ashen Era Archive

Reads data/chunks.jsonl (produced by ingest.py), embeds each chunk with a
local sentence-transformers model (no API key, no card, no rate limits,
no cost), and stores vectors + metadata in a local Chroma collection.

Install:
    pip install sentence-transformers chromadb --break-system-packages

First run will download the model (~1.3GB for bge-large) — needs internet
once, then works fully offline.
"""

import os
import json
import time
from pathlib import Path
from typing import List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

from sentence_transformers import SentenceTransformer
import chromadb

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
# Paths resolve relative to the project root by default; override via .env.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHUNKS_FILE = os.environ.get("CHUNKS_FILE", str(_PROJECT_ROOT / "data" / "chunks.jsonl"))
CHROMA_DIR = os.environ.get("CHROMA_DIR", str(_PROJECT_ROOT / "data" / "chroma_db"))
COLLECTION_NAME = "ashen_era_archive"

# bge-large-en-v1.5: strong open-weight retrieval model, free, runs locally.
# If your PC is slow / low on RAM, swap to "BAAI/bge-small-en-v1.5" (much
# faster, slightly lower quality) or "BAAI/bge-base-en-v1.5" (middle ground).
EMBED_MODEL_NAME = "BAAI/bge-large-en-v1.5"
BATCH_SIZE = 32     # local batches can be larger — no API rate limits, only your PC's RAM/CPU/GPU

# bge models expect a specific instruction prefix on QUERIES ONLY (not documents)
# for best retrieval performance. This is a quirk of the bge model family.
QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


# ---------------------------------------------------------------------------
# Load chunks
# ---------------------------------------------------------------------------
def load_chunks(path: str) -> List[Dict[str, Any]]:
    chunks = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    return chunks


# ---------------------------------------------------------------------------
# Model loading (cached across calls within a process)
# ---------------------------------------------------------------------------
_model = None


def get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        print(f"Loading embedding model '{EMBED_MODEL_NAME}' (first run downloads it)...")
        _model = SentenceTransformer(EMBED_MODEL_NAME)
        print("Model loaded.")
    return _model


# ---------------------------------------------------------------------------
# Build the vector store
# ---------------------------------------------------------------------------
def build_vector_store(force_rebuild: bool = False):
    """Set force_rebuild=True if you've changed ingest.py (e.g. chunk size)
    and chunk_ids may have changed — otherwise resuming could mix stale
    old vectors with new ones."""
    model = get_model()
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

    existing_collections = [c.name for c in chroma_client.list_collections()]
    if force_rebuild and COLLECTION_NAME in existing_collections:
        chroma_client.delete_collection(COLLECTION_NAME)
        existing_collections.remove(COLLECTION_NAME)
        print("force_rebuild=True — deleted existing collection.")

    if COLLECTION_NAME in existing_collections:
        collection = chroma_client.get_collection(COLLECTION_NAME)
        print(f"Found existing collection with {collection.count()} vectors — resuming.")
    else:
        collection = chroma_client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        print("Created new collection.")

    chunks = load_chunks(CHUNKS_FILE)
    print(f"Loaded {len(chunks)} chunks from {CHUNKS_FILE}")

    already_done = set(collection.get()["ids"]) if collection.count() > 0 else set()
    chunks = [c for c in chunks if c["chunk_id"] not in already_done]
    if already_done:
        print(f"Skipping {len(already_done)} already-embedded chunks. {len(chunks)} remain.")

    if not chunks:
        print("Nothing left to embed.")
        return

    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    start_time = time.time()

    for batch_num in range(total_batches):
        start = batch_num * BATCH_SIZE
        end = min(start + BATCH_SIZE, len(chunks))
        batch = chunks[start:end]

        texts = [c["text"] for c in batch]
        # normalize_embeddings=True so cosine similarity via dot product works cleanly
        embeddings = model.encode(texts, normalize_embeddings=True, show_progress_bar=False).tolist()

        ids = [c["chunk_id"] for c in batch]
        metadatas = [
            {
                "doc_id": c["doc_id"],
                "source_path": c["source_path"],
                "doc_type": c["doc_type"],
                "page_or_section": c.get("page_or_section") or "",
                "is_ocr": c.get("is_ocr", False),
            }
            for c in batch
        ]

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        if (batch_num + 1) % 5 == 0 or (batch_num + 1) == total_batches:
            elapsed = time.time() - start_time
            print(f"Embedded & stored batch {batch_num + 1}/{total_batches} "
                  f"({end}/{len(chunks)} chunks) — {elapsed:.0f}s elapsed")

    print(f"\nDone. Collection '{COLLECTION_NAME}' now has {collection.count()} vectors.")
    print(f"Stored at: {CHROMA_DIR}")


# ---------------------------------------------------------------------------
# Retrieval helper — this is what your orchestrator.py should call
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Hybrid retrieval: dense (semantic) + BM25 (keyword) via simple rank fusion.
#
# Why: the corpus contains OCR'd scans, tables, and mixed-reliability
# ephemera. Dense-only retrieval can miss exact-name/number matches (a
# codex date like "246 AS", a proper noun spelled unusually) that a
# keyword-based signal catches reliably. This is intentionally simple
# (rank-position averaging, not a trained reranker or learned fusion
# weight) — a cheap, low-risk addition rather than a new ML component
# whose behavior would need separate validation before submission.
# ---------------------------------------------------------------------------
_bm25_index = None
_bm25_chunk_lookup: List[Dict[str, Any]] = None


def _build_bm25_index():
    """Lazily build a BM25 index over every chunk currently in the Chroma
    collection. Built once per process and cached — rebuilding per-query
    would be wasteful since the corpus doesn't change during a run."""
    global _bm25_index, _bm25_chunk_lookup
    if _bm25_index is not None:
        return

    from rank_bm25 import BM25Okapi

    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma_client.get_collection(COLLECTION_NAME)
    all_data = collection.get()  # fetches every stored document + metadata

    _bm25_chunk_lookup = []
    tokenized_corpus = []
    for doc_id_key, text, meta in zip(all_data["ids"], all_data["documents"], all_data["metadatas"]):
        _bm25_chunk_lookup.append({
            "text": text,
            "source": meta["doc_id"],
            "doc_id": meta["doc_id"],
            "doc_type": meta["doc_type"],
            "is_ocr": meta["is_ocr"],
        })
        tokenized_corpus.append(text.lower().split())

    _bm25_index = BM25Okapi(tokenized_corpus)
    print(f"  [bm25] Built keyword index over {len(_bm25_chunk_lookup)} chunks.")


def _bm25_search(query: str, top_k: int) -> List[Dict[str, Any]]:
    _build_bm25_index()
    scores = _bm25_index.get_scores(query.lower().split())
    ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_k]
    return [_bm25_chunk_lookup[i] for i in ranked_indices]


def search(query: str, top_k: int = 5, use_hybrid: bool = True) -> List[Dict[str, Any]]:
    """Retrieve the top_k most relevant chunks for a query.

    Returns list of {"text", "source", "doc_id", "score", ...} dicts,
    matching the shape orchestrator.py's vector_search() expects.

    When use_hybrid=True (default), combines dense semantic search with a
    BM25 keyword search via simple reciprocal-rank fusion: each chunk's
    final rank is based on the sum of (1 / rank_in_dense) and
    (1 / rank_in_bm25), so a chunk appearing near the top of either list
    scores well, and a chunk appearing in both scores best. Set
    use_hybrid=False to fall back to pure dense search (the original
    behavior) for comparison/debugging.
    """
    model = get_model()
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma_client.get_collection(COLLECTION_NAME)

    dense_k = top_k * 3 if use_hybrid else top_k  # widen the dense pool before fusing
    query_embedding = model.encode(
        QUERY_PREFIX + query, normalize_embeddings=True, show_progress_bar=False
    ).tolist()
    results = collection.query(query_embeddings=[query_embedding], n_results=dense_k)

    dense_chunks = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        dense_chunks.append({
            "text": results["documents"][0][i],
            "source": meta["doc_id"],
            "doc_id": meta["doc_id"],
            "doc_type": meta["doc_type"],
            "is_ocr": meta["is_ocr"],
            "score": results["distances"][0][i],
        })

    if not use_hybrid:
        return dense_chunks[:top_k]

    bm25_chunks = _bm25_search(query, top_k=top_k * 3)

    # Reciprocal-rank fusion, keyed by doc_id + a text prefix (same key
    # shape used by orchestrator.py's near-duplicate check, for consistency)
    def chunk_key(c):
        return (c["doc_id"], c["text"][:120])

    fused_scores: Dict[Any, float] = {}
    chunk_by_key: Dict[Any, Dict[str, Any]] = {}
    for rank, c in enumerate(dense_chunks, start=1):
        k = chunk_key(c)
        fused_scores[k] = fused_scores.get(k, 0.0) + 1.0 / rank
        chunk_by_key[k] = c
    for rank, c in enumerate(bm25_chunks, start=1):
        k = chunk_key(c)
        fused_scores[k] = fused_scores.get(k, 0.0) + 1.0 / rank
        chunk_by_key.setdefault(k, c)

    ranked_keys = sorted(fused_scores.keys(), key=lambda k: fused_scores[k], reverse=True)
    return [chunk_by_key[k] for k in ranked_keys[:top_k]]


if __name__ == "__main__":
    build_vector_store()

    # Quick smoke test after building
    print("\n--- Smoke test ---")
    test_results = search("What happened at Crookgate Keep?", top_k=3)
    for r in test_results:
        print(f"[{r['doc_type']}] {r['doc_id']} (score={r['score']:.4f})")
        print(f"  {r['text'][:150]}...\n")
