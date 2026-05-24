"""RetrieveForQuery — hybrid retrieval through the RetrieverPort.

Kept in `application` (not `ai/`) so future use cases (the agent loop, a
"why did the AI say that" debug view) can call it directly without going
through the agent.
"""

from __future__ import annotations

from src.application.documents.dtos import RetrievedChunkDTO
from src.application.documents.queries import RetrieveForQuery
from src.domain.rag.ports import RetrieverPort


class RetrieveForQueryUseCase:
    def __init__(self, *, retriever: RetrieverPort) -> None:
        self._retriever = retriever

    async def execute(self, query: RetrieveForQuery) -> list[RetrievedChunkDTO]:
        chunks = await self._retriever.hybrid_retrieve(
            query=query.query,
            tenant_id=query.tenant_id,
            top_k=query.top_k,
        )
        return [
            RetrievedChunkDTO(
                chunk_id=c.chunk_id,
                document_id=c.document_id,
                content=c.content,
                score=c.score,
            )
            for c in chunks
        ]
