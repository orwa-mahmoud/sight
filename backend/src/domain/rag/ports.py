"""RAG ports — chunker, embedder, retriever.

These keep `domain` and `application` layers ignorant of any specific text
splitter, embedding provider, or vector store. Adapters live in
`infrastructure/rag/` and are wired through the DI container.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from src.domain.rag.value_objects import RetrievedChunk, TextChunk


class ParserPort(Protocol):
    def parse(self, content: bytes, mime_type: object) -> str: ...


class ChunkerPort(Protocol):
    def chunk(self, text: str) -> list[TextChunk]: ...


class EmbeddingPort(Protocol):
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    async def embed_query(self, text: str) -> list[float]: ...

    @property
    def dimensions(self) -> int: ...


class RerankerPort(Protocol):
    async def rerank(self, query: str, chunks: list[RetrievedChunk], *, top_k: int = 8) -> list[RetrievedChunk]: ...


class RetrieverPort(Protocol):
    async def hybrid_retrieve(
        self,
        *,
        query: str,
        tenant_id: UUID,
        top_k: int = 8,
    ) -> list[RetrievedChunk]: ...
