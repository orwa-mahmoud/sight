"""Document + Chunk repository ports."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.documents.entities import Chunk, Document


class DocumentRepository(Protocol):
    async def save(self, document: Document) -> None: ...

    async def get_by_id(self, document_id: UUID) -> Document | None: ...

    async def list_for_tenant(self, tenant_id: UUID, *, limit: int = 100, offset: int = 0) -> list[Document]: ...

    async def list_processing(self, tenant_id: UUID, *, active_since: datetime) -> list[Document]:
        """Documents still actively in flight (uploaded or ingesting AND touched
        since ``active_since``) — drives the global ingestion progress indicator,
        which polls this without fetching every doc. Documents older than the cutoff
        are treated as stuck (the reaper's job), so the UI stops polling them."""
        ...

    async def list_stuck_for_tenant(self, tenant_id: UUID, *, older_than: datetime) -> list[Document]:
        """Documents stuck mid-ingest (uploaded/ingesting) and untouched since
        ``older_than`` for one tenant — for the reaper, which iterates every tenant
        under that tenant's RLS scope. A tenant-scoped query is required: a global
        query returns zero rows under enforced RLS when no tenant scope is set."""
        ...

    async def count_for_tenant(self, tenant_id: UUID) -> int: ...

    async def delete(self, document_id: UUID) -> None: ...

    async def delete_many_for_tenant(self, tenant_id: UUID, document_ids: list[UUID]) -> int:
        """Delete the given tenant's documents in one statement; returns the count
        actually deleted (ids from another tenant or missing are ignored)."""
        ...


class ChunkRepository(Protocol):
    # Sync — add_all is sync. Upgrade to async if batch insert is needed.
    def save_many(self, chunks: list[Chunk]) -> None: ...

    async def delete_for_document(self, document_id: UUID) -> None: ...

    async def count_for_tenant(self, tenant_id: UUID) -> int: ...
