"""Document domain events."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.shared.events import DomainEvent


@dataclass(frozen=True, kw_only=True)
class DocumentUploaded(DomainEvent):
    document_id: UUID
    tenant_id: UUID
    filename: str
    mime_type: str
    size_bytes: int


@dataclass(frozen=True, kw_only=True)
class DocumentIngested(DomainEvent):
    document_id: UUID
    tenant_id: UUID
    chunk_count: int


@dataclass(frozen=True, kw_only=True)
class DocumentIngestionFailed(DomainEvent):
    document_id: UUID
    tenant_id: UUID
    reason: str
