"""Document + Chunk aggregates.

`Document` is the uploaded file; `Chunk` is one slice of its parsed text,
holding its own embedding vector for retrieval.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.domain.documents.events import DocumentIngested, DocumentIngestionFailed, DocumentUploaded
from src.domain.documents.value_objects import DocumentMimeType, DocumentStatus
from src.domain.shared.entities import BaseEntity
from src.domain.shared.exceptions import InvalidOperationError


@dataclass(eq=False, kw_only=True)
class Document(BaseEntity):
    tenant_id: UUID
    uploaded_by_user_id: UUID | None
    filename: str
    mime_type: DocumentMimeType
    size_bytes: int
    status: DocumentStatus
    chunk_count: int = 0
    error: str | None = None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def upload(
        cls,
        *,
        tenant_id: UUID,
        uploaded_by_user_id: UUID | None,
        filename: str,
        mime_type: DocumentMimeType,
        size_bytes: int,
    ) -> Document:
        now = datetime.now(UTC)
        doc = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            uploaded_by_user_id=uploaded_by_user_id,
            filename=filename.strip(),
            mime_type=mime_type,
            size_bytes=size_bytes,
            status=DocumentStatus.UPLOADED,
            chunk_count=0,
            error=None,
            created_at=now,
            updated_at=now,
        )
        doc._is_new = True
        doc._emit(
            DocumentUploaded(
                document_id=doc.id,
                tenant_id=tenant_id,
                filename=doc.filename,
                mime_type=mime_type.value,
                size_bytes=size_bytes,
            )
        )
        return doc

    def mark_ingesting(self) -> None:
        if self.status not in {DocumentStatus.UPLOADED, DocumentStatus.FAILED}:
            raise InvalidOperationError(f"Cannot start ingestion from status {self.status}")
        self.status = DocumentStatus.INGESTING
        self.error = None
        self.updated_at = datetime.now(UTC)

    def mark_ready(self, *, chunk_count: int) -> None:
        self.status = DocumentStatus.READY
        self.chunk_count = chunk_count
        self.updated_at = datetime.now(UTC)
        self._emit(DocumentIngested(document_id=self.id, tenant_id=self.tenant_id, chunk_count=chunk_count))

    def mark_failed(self, *, reason: str) -> None:
        self.status = DocumentStatus.FAILED
        self.error = reason[:1024]
        self.updated_at = datetime.now(UTC)
        self._emit(DocumentIngestionFailed(document_id=self.id, tenant_id=self.tenant_id, reason=self.error))


@dataclass(eq=False, kw_only=True)
class Chunk(BaseEntity):
    document_id: UUID
    tenant_id: UUID
    chunk_index: int
    content: str
    embedding: list[float]
    extra_metadata: dict[str, Any]
    created_at: datetime

    @classmethod
    def create(
        cls,
        *,
        document_id: UUID,
        tenant_id: UUID,
        chunk_index: int,
        content: str,
        embedding: list[float],
        extra_metadata: dict[str, Any] | None = None,
    ) -> Chunk:
        chunk = cls(
            id=uuid4(),
            document_id=document_id,
            tenant_id=tenant_id,
            chunk_index=chunk_index,
            content=content,
            embedding=embedding,
            extra_metadata=extra_metadata or {},
            created_at=datetime.now(UTC),
        )
        chunk._is_new = True
        return chunk
