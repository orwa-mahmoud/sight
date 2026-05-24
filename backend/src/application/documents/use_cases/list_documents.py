"""ListDocuments — return all documents for a tenant."""

from __future__ import annotations

from src.application.documents.dtos import DocumentDTO
from src.application.documents.queries import ListDocuments
from src.application.shared.unit_of_work import UnitOfWork


class ListDocumentsUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListDocuments) -> list[DocumentDTO]:
        docs = await self._uow.documents.list_for_tenant(query.tenant_id)
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


class DeleteDocumentUseCase:
    """Delete a document (chunks cascade via FK)."""

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, tenant_id: object, document_id: object) -> None:
        from uuid import UUID  # noqa: PLC0415

        from src.domain.shared.exceptions import (  # noqa: PLC0415
            AuthorizationError,
            EntityNotFoundError,
        )

        if not isinstance(document_id, UUID) or not isinstance(tenant_id, UUID):
            raise EntityNotFoundError("Invalid identifiers")

        doc = await self._uow.documents.get_by_id(document_id)
        if doc is None:
            raise EntityNotFoundError("Document not found")
        if doc.tenant_id != tenant_id:
            raise AuthorizationError("Document does not belong to this tenant")
        await self._uow.documents.delete(document_id)
