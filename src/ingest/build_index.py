"""
One-time ingestion: read data/knowledge_base/*.md, chunk, embed, store in Chroma.
Run this whenever you add or edit a runbook: python -m src.ingest.build_index
"""
import glob
import os
import sys

import chromadb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.config import CHROMA_DB_PATH, CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_MODEL_NAME, EMBEDDING_DEVICE

KB_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge_base")


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Simple sliding-window chunker. Good enough for short runbook docs."""
    if len(text) <= chunk_size:
        return [text]
    step = max(chunk_size - overlap, 1)
    return [text[i:i + chunk_size] for i in range(0, len(text), step) if text[i:i + chunk_size].strip()]


def build_index():
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=EMBEDDING_DEVICE)
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    # Drop and recreate so re-running is idempotent (no duplicate chunks on re-ingest)
    try:
        client.delete_collection("runbooks")
    except Exception:
        pass
    collection = client.create_collection("runbooks")

    md_files = glob.glob(os.path.join(KB_DIR, "*.md"))
    if not md_files:
        print(f"No .md files found in {KB_DIR} — add runbooks before ingesting.")
        return

    total_chunks = 0
    for path in md_files:
        with open(path, "r", encoding="utf-8") as f:
            text = f.read()
        chunks = chunk_text(text)
        embeddings = model.encode(chunks).tolist()
        ids = [f"{os.path.basename(path)}-{i}" for i in range(len(chunks))]
        collection.add(
            documents=chunks,
            embeddings=embeddings,
            ids=ids,
            metadatas=[{"source": os.path.basename(path)}] * len(chunks),
        )
        total_chunks += len(chunks)
        print(f"Indexed {len(chunks)} chunks from {os.path.basename(path)}")

    print(f"\nDone. Indexed {total_chunks} chunks total from {len(md_files)} files.")
    print(f"Chroma DB at: {CHROMA_DB_PATH}")


if __name__ == "__main__":
    build_index()