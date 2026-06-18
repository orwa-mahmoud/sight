"""ListProcessingDocuments — documents still being ingested for a tenant.

Backs the global ingestion progress indicator. Because status lives in the DB,
the indicator re-derives in-flight work after a page refresh — nothing is held
only in the browser.
"""

from __future__ import annotations

from src.application.documents.dtos import DocumentDTO
from src.application.documents.queries import ListProcessingDocuments
from src.application.shared.unit_of_work import UnitOfWork


class ListProcessingDocumentsUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: ListProcessingDocuments) -> list[DocumentDTO]:
        docs = await self._uow.documents.list_processing(query.tenant_id)
        return [DocumentDTO.from_entity(d) for d in docs]
