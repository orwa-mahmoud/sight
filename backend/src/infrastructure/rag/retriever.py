"""Hybrid retriever — vector + BM25 fused via Reciprocal Rank Fusion.

Step 1: pull top-N candidates from the HNSW index (cosine distance).
Step 2: pull top-N from BM25 over the tsvector column.
Step 3: combine ranks with RRF (k=60) — robust to scale differences.
Step 4: optional reranking via RerankerPort (kept hybrid order when absent).
Step 5: take top-k, then re-order so the strongest chunks sit at the edges of
        the context the LLM sees ("lost in the middle").
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.rag.ports import EmbeddingPort, RerankerPort
from src.domain.rag.value_objects import RetrievedChunk
from src.infrastructure.metrics import RAG_RETRIEVALS_TOTAL
from src.infrastructure.persistence.postgres.models.chunk import ChunkModel

_DEFAULT_CANDIDATE_POOL = 50
_RRF_K = 60


def reorder_lost_in_the_middle(chunks: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Place the strongest chunks at the start and end of the list.

    LLMs attend best to the beginning and end of their context and worst to the
    middle. Given chunks in best-first order, interleave them so the top result
    stays first, the second-best lands last, and the weakest sit in the middle.
    Order-only — same chunks, same set — so it never changes recall, only layout.
    """
    if len(chunks) <= 2:
        return chunks
    return chunks[0::2] + chunks[1::2][::-1]


class HybridRetriever:
    """Implements `RetrieverPort`. Tenant-isolated at every query."""

    def __init__(self, *, session: AsyncSession, embedder: EmbeddingPort, reranker: RerankerPort | None = None) -> None:
        self._session = session
        self._embedder = embedder
        self._reranker = reranker

    async def hybrid_retrieve(
        self,
        *,
        query: str,
        tenant_id: UUID,
        top_k: int = 8,
    ) -> list[RetrievedChunk]:
        query = query.strip()
        if not query:
            return []

        RAG_RETRIEVALS_TOTAL.inc()
        query_embedding = await self._embedder.embed_query(query)
        vector_hits = await self._vector_search(query_embedding, tenant_id, _DEFAULT_CANDIDATE_POOL)
        bm25_hits = await self._bm25_search(query, tenant_id, _DEFAULT_CANDIDATE_POOL)

        rerank_pool = top_k * 3
        fused = self._rrf_fuse(vector_hits, bm25_hits)[:rerank_pool]

        by_id: dict[UUID, ChunkModel] = {m.id: m for m in vector_hits + bm25_hits}
        candidates = [
            RetrievedChunk(
                chunk_id=cid,
                document_id=by_id[cid].document_id,
                tenant_id=by_id[cid].tenant_id,
                content=by_id[cid].content,
                score=score,
                extra_metadata=by_id[cid].extra_metadata,
            )
            for cid, score in fused
            if cid in by_id
        ]

        if self._reranker is not None:
            candidates = await self._reranker.rerank(query, candidates, top_k=top_k)
        else:
            candidates = candidates[:top_k]

        return reorder_lost_in_the_middle(candidates)

    # ── Stage 1: vector (HNSW cosine) ─────────────────────────────
    async def _vector_search(
        self,
        embedding: list[float],
        tenant_id: UUID,
        limit: int,
    ) -> list[ChunkModel]:
        if not embedding:
            return []
        stmt = (
            select(ChunkModel)
            .where(ChunkModel.tenant_id == tenant_id)
            .order_by(ChunkModel.embedding.cosine_distance(embedding))
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Stage 2: BM25 via tsvector ────────────────────────────────
    async def _bm25_search(self, query: str, tenant_id: UUID, limit: int) -> list[ChunkModel]:
        tsquery = func.websearch_to_tsquery("english", query)
        rank = func.ts_rank(ChunkModel.content_tsvector, tsquery)
        stmt = (
            select(ChunkModel)
            .where(
                ChunkModel.tenant_id == tenant_id,
                ChunkModel.content_tsvector.op("@@")(tsquery),
            )
            .order_by(rank.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    # ── Stage 3: Reciprocal Rank Fusion ───────────────────────────
    @staticmethod
    def _rrf_fuse(*ranked_lists: list[ChunkModel]) -> list[tuple[UUID, float]]:
        scores: dict[UUID, float] = {}
        for ranked in ranked_lists:
            for rank, item in enumerate(ranked, start=1):
                scores[item.id] = scores.get(item.id, 0.0) + 1.0 / (_RRF_K + rank)
        return sorted(scores.items(), key=lambda kv: kv[1], reverse=True)
