"""Document commands."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class RegisterDocument:
    """Record an uploaded document immediately; processing happens after."""

    tenant_id: UUID
    uploaded_by_user_id: UUID | None
    filename: str
    size_bytes: int


@dataclass(frozen=True, kw_only=True)
class ProcessDocument:
    """Parse + chunk + embed a registered document (runs in the background)."""

    tenant_id: UUID
    document_id: UUID
    filename: str
    content: bytes


@dataclass(frozen=True, kw_only=True)
class DeleteDocument:
    tenant_id: UUID
    document_id: UUID
