"""PostgreSQL Document repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentMimeType, DocumentStatus
from src.infrastructure.persistence.postgres.models.document import DocumentModel


class PostgresDocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, document: Document) -> None:
        if document.is_new:
            self._session.add(self._to_model(document))
            document.mark_persisted()
            return
        model = await self._session.get(DocumentModel, document.id)
        if model is None:
            self._session.add(self._to_model(document))
            return
        model.filename = document.filename
        model.status = document.status.value
        model.chunk_count = document.chunk_count
        model.error = document.error
        model.updated_at = document.updated_at

    async def get_by_id(self, document_id: UUID) -> Document | None:
        model = await self._session.get(DocumentModel, document_id)
        return self._to_entity(model) if model else None

    async def list_for_tenant(self, tenant_id: UUID) -> list[Document]:
        stmt = (
            select(DocumentModel).where(DocumentModel.tenant_id == tenant_id).order_by(DocumentModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, document_id: UUID) -> None:
        await self._session.execute(delete(DocumentModel).where(DocumentModel.id == document_id))

    @staticmethod
    def _to_model(d: Document) -> DocumentModel:
        return DocumentModel(
            id=d.id,
            tenant_id=d.tenant_id,
            uploaded_by_user_id=d.uploaded_by_user_id,
            filename=d.filename,
            mime_type=d.mime_type.value,
            size_bytes=d.size_bytes,
            status=d.status.value,
            chunk_count=d.chunk_count,
            error=d.error,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )

    @staticmethod
    def _to_entity(m: DocumentModel) -> Document:
        return Document(
            id=m.id,
            tenant_id=m.tenant_id,
            uploaded_by_user_id=m.uploaded_by_user_id,
            filename=m.filename,
            mime_type=DocumentMimeType(m.mime_type),
            size_bytes=m.size_bytes,
            status=DocumentStatus(m.status),
            chunk_count=m.chunk_count,
            error=m.error,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
