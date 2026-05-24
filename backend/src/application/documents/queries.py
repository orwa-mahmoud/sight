"""Document queries."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class ListDocuments:
    tenant_id: UUID


@dataclass(frozen=True, kw_only=True)
class RetrieveForQuery:
    tenant_id: UUID
    query: str
    top_k: int = 8
