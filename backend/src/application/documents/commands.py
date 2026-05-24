"""Document commands."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class IngestDocument:
    tenant_id: UUID
    uploaded_by_user_id: UUID | None
    filename: str
    content: bytes


@dataclass(frozen=True, kw_only=True)
class DeleteDocument:
    tenant_id: UUID
    document_id: UUID
