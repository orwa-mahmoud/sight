"""RAG value objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID


@dataclass(frozen=True, kw_only=True)
class TextChunk:
    """A piece of text produced by a chunker, with per-chunk metadata."""

    index: int
    content: str
    extra_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class RetrievedChunk:
    """One chunk returned by hybrid retrieval, with a fused relevance score."""

    chunk_id: UUID
    document_id: UUID
    tenant_id: UUID
    content: str
    score: float
    extra_metadata: dict[str, Any]
