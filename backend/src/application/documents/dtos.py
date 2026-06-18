"""Document DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from src.domain.documents.entities import Document


@dataclass(frozen=True, kw_only=True)
class DocumentDTO:
    id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    chunk_count: int
    error: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_entity(cls, d: Document) -> DocumentDTO:
        return cls(
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


@dataclass(frozen=True, kw_only=True)
class RetrievedChunkDTO:
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
