"""PostgreSQL Chunk repository — append + delete by document, count by tenant."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.documents.entities import Chunk
from src.infrastructure.persistence.postgres.models.chunk import ChunkModel


class PostgresChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def save_many(self, chunks: list[Chunk]) -> None:
        models = [self._to_model(c) for c in chunks]
        self._session.add_all(models)
        for c in chunks:
            c.mark_persisted()

    async def delete_for_document(self, document_id: UUID) -> None:
        await self._session.execute(delete(ChunkModel).where(ChunkModel.document_id == document_id))

    async def count_for_tenant(self, tenant_id: UUID) -> int:
        stmt = select(func.count(ChunkModel.id)).where(ChunkModel.tenant_id == tenant_id)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    @staticmethod
    def _to_model(c: Chunk) -> ChunkModel:
        return ChunkModel(
            id=c.id,
            document_id=c.document_id,
            tenant_id=c.tenant_id,
            chunk_index=c.chunk_index,
            content=c.content,
            embedding=c.embedding,
            extra_metadata=c.extra_metadata,
            created_at=c.created_at,
        )
