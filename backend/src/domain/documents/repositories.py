"""Document + Chunk repository ports."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.documents.entities import Chunk, Document


class DocumentRepository(Protocol):
    async def save(self, document: Document) -> None: ...

    async def get_by_id(self, document_id: UUID) -> Document | None: ...

    async def list_for_tenant(self, tenant_id: UUID, *, limit: int = 100, offset: int = 0) -> list[Document]: ...

    async def list_processing(self, tenant_id: UUID) -> list[Document]:
        """Documents still in flight (uploaded or ingesting) — drives the global
        ingestion progress indicator, which polls this without fetching every doc."""
        ...

    async def count_for_tenant(self, tenant_id: UUID) -> int: ...

    async def delete(self, document_id: UUID) -> None: ...


class ChunkRepository(Protocol):
    # Sync — add_all is sync. Upgrade to async if batch insert is needed.
    def save_many(self, chunks: list[Chunk]) -> None: ...

    async def delete_for_document(self, document_id: UUID) -> None: ...

    async def count_for_tenant(self, tenant_id: UUID) -> int: ...
