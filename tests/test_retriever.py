"""
Basic smoke test: does retrieval return non-empty, plausible results?
Run with: python -m pytest tests/test_retriever.py -v
(Requires the index to already be built: python -m src.ingest.build_index)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.retriever.retrieve import retrieve


def test_retrieve_returns_results():
    hits = retrieve("why is my pod crashing with out of memory errors", k=3)
    assert len(hits) > 0, "Expected at least one runbook chunk, got none — did you run build_index.py?"


def test_retrieve_oom_query_hits_oom_runbook():
    hits = retrieve("OOMKilled CrashLoopBackOff memory limit", k=3)
    sources = [h["source"] for h in hits]
    assert "oom_crashloop.md" in sources, f"Expected oom_crashloop.md in top results, got: {sources}"


def test_retrieve_imagepull_query_hits_imagepull_runbook():
    hits = retrieve("image pull error wrong tag registry", k=3)
    sources = [h["source"] for h in hits]
    assert "image_pull_backoff.md" in sources, f"Expected image_pull_backoff.md in top results, got: {sources}"


if __name__ == "__main__":
    test_retrieve_returns_results()
    test_retrieve_oom_query_hits_oom_runbook()
    test_retrieve_imagepull_query_hits_imagepull_runbook()
    print("All smoke tests passed.")
