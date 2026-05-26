"""DeleteDocument — remove a document and its chunks (FK cascade)."""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError


class DeleteDocumentUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, tenant_id: UUID, document_id: UUID) -> None:
        doc = await self._uow.documents.get_by_id(document_id)
        if doc is None:
            raise EntityNotFoundError("Document not found")
        if doc.tenant_id != tenant_id:
            raise AuthorizationError("Document does not belong to this tenant")
        await self._uow.documents.delete(document_id)
