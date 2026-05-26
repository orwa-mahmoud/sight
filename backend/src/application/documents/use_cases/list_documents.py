"""ListDocuments — return all documents for a tenant."""

from __future__ import annotations

from src.application.documents.dtos import DocumentDTO
from src.application.documents.queries import ListDocuments
from src.application.shared.unit_of_work import UnitOfWork


class ListDocumentsUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListDocuments) -> list[DocumentDTO]:
        docs = await self._uow.documents.list_for_tenant(query.tenant_id, limit=query.limit, offset=query.offset)
        return [
            DocumentDTO(
                id=d.id,
                filename=d.filename,
                mime_type=d.mime_type.value,
                size_bytes=d.size_bytes,
                status=d.status.value,
                chunk_count=d.chunk_count,
                error=d.error,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in docs
        ]
