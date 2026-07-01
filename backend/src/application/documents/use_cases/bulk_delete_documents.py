"""BulkDeleteDocuments — remove many documents (and their chunks) in one statement."""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork


class BulkDeleteDocumentsUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, tenant_id: UUID, document_ids: list[UUID]) -> int:
        """Delete the caller's documents in a single tenant-scoped statement and
        return how many were removed. Ids the tenant doesn't own (or that don't
        exist) are silently skipped, so there's no cross-tenant leak and no error
        on a stale selection — the count reflects what was actually deleted."""
        deleted = await self._uow.documents.delete_many_for_tenant(tenant_id, document_ids)
        await self._uow.commit()
        return deleted
