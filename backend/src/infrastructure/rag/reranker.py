"""Reranker implementations for the RAG pipeline.

PassThroughReranker: returns chunks as-is (no-op, used when no reranker is configured).

To add a real reranker (Cohere, cross-encoder, LLM-based), implement the
RerankerPort protocol and inject it into the HybridRetriever.
"""

from __future__ import annotations

from src.domain.rag.value_objects import RetrievedChunk


class PassThroughReranker:
    """No-op reranker — returns chunks unchanged."""

    # Sync for now; upgrade to async when a real reranker (Cohere, cross-encoder) is added.
    def rerank(self, _query: str, chunks: list[RetrievedChunk], *, top_k: int = 8) -> list[RetrievedChunk]:
        return chunks[:top_k]
