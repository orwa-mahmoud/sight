"""Documents API schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class DocumentSummary(BaseModel):
    id: UUID
    filename: str
    mime_type: str
    size_bytes: int
    status: str
    chunk_count: int
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class BulkDeleteRequest(BaseModel):
    # Capped so one request can't build an unbounded IN (...) list.
    ids: list[UUID] = Field(min_length=1, max_length=500)


class BulkDeleteResponse(BaseModel):
    deleted: int


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    top_k: int = Field(default=8, ge=1, le=50)


class RetrievedChunkResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    content: str
    score: float


class RetrieveResponse(BaseModel):
    results: list[RetrievedChunkResponse]
