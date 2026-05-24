"""Document DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


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


@dataclass(frozen=True, kw_only=True)
class RetrievedChunkDTO:
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float
