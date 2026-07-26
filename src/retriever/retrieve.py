"""
Retriever: given a query string, return the top-k runbook chunks with source metadata.
"""
import os
import sys

import chromadb
from sentence_transformers import SentenceTransformer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from src.config import CHROMA_DB_PATH, EMBEDDING_MODEL_NAME, EMBEDDING_DEVICE, DEFAULT_TOP_K

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=EMBEDDING_DEVICE)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
        _collection = client.get_collection("runbooks")
    return _collection


def retrieve(query: str, k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Returns: [{"text": str, "source": str}, ...]
    Raises a clear error if the index hasn't been built yet.
    """
    try:
        collection = _get_collection()
    except Exception as e:
        raise RuntimeError(
            "Could not open the 'runbooks' collection. "
            "Did you run `python -m src.ingest.build_index` first?"
        ) from e

    model = _get_model()
    q_emb = model.encode([query]).tolist()
    results = collection.query(query_embeddings=q_emb, n_results=k)

    if not results["documents"] or not results["documents"][0]:
        return []

    return [
        {"text": doc, "source": meta["source"]}
        for doc, meta in zip(results["documents"][0], results["metadatas"][0])
    ]


if __name__ == "__main__":
    # Quick manual smoke test: python -m src.retriever.retrieve "why is my pod crashing"
    import sys as _sys
    q = " ".join(_sys.argv[1:]) or "why is my pod crashing"
    for hit in retrieve(q):
        print(f"[{hit['source']}] {hit['text'][:150]}...")