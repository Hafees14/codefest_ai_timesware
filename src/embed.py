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

from sentence_transformers import SentenceTransformer
import chromadb

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
CHUNKS_FILE = r"D:\COMPETITIONS\SLIIT CodeFest\CodeFest AI Innovation\codefest-ai\data\chunks.jsonl"
CHROMA_DIR = r"D:\COMPETITIONS\SLIIT CodeFest\CodeFest AI Innovation\codefest-ai\data\chroma_db"
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
def search(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """Embed a query and retrieve the top_k most relevant chunks.
    Returns list of {"text", "source", "doc_id", "score", ...} dicts,
    matching the shape orchestrator.py's vector_search() expects."""
    model = get_model()
    chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = chroma_client.get_collection(COLLECTION_NAME)

    query_embedding = model.encode(
        QUERY_PREFIX + query, normalize_embeddings=True, show_progress_bar=False
    ).tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        meta = results["metadatas"][0][i]
        chunks.append({
            "text": results["documents"][0][i],
            "source": meta["doc_id"],
            "doc_id": meta["doc_id"],
            "doc_type": meta["doc_type"],
            "is_ocr": meta["is_ocr"],
            "score": results["distances"][0][i],
        })
    return chunks


if __name__ == "__main__":
    build_vector_store()

    # Quick smoke test after building
    print("\n--- Smoke test ---")
    test_results = search("What happened at Crookgate Keep?", top_k=3)
    for r in test_results:
        print(f"[{r['doc_type']}] {r['doc_id']} (score={r['score']:.4f})")
        print(f"  {r['text'][:150]}...\n")
