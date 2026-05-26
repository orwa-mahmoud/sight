"""Unit tests for PostgresChunkRepository — save_many, delete_for_document, count_for_tenant."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.domain.documents.entities import Chunk
from src.infrastructure.persistence.postgres.repositories.chunk_repo import PostgresChunkRepository


def _make_chunk(
    *,
    document_id: UUID | None = None,
    tenant_id: UUID | None = None,
    chunk_index: int = 0,
    content: str = "Some text",
    embedding: list[float] | None = None,
    extra_metadata: dict[str, Any] | None = None,
) -> Chunk:
    return Chunk.create(
        document_id=document_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        chunk_index=chunk_index,
        content=content,
        embedding=embedding or [0.1, 0.2, 0.3],
        extra_metadata=extra_metadata,
    )


def test_save_many_adds_models_and_marks_persisted() -> None:
    session = MagicMock()
    repo = PostgresChunkRepository(session)

    chunks = [_make_chunk(chunk_index=i) for i in range(3)]
    for c in chunks:
        assert c.is_new is True

    repo.save_many(chunks)

    session.add_all.assert_called_once()
    models = session.add_all.call_args[0][0]
    assert len(models) == 3
    for c in chunks:
        assert c.is_new is False  # mark_persisted was called


@pytest.mark.asyncio
async def test_delete_for_document_executes_delete() -> None:
    session = AsyncMock()
    repo = PostgresChunkRepository(session)

    doc_id = uuid4()
    await repo.delete_for_document(doc_id)

    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_count_for_tenant_returns_int() -> None:
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 42
    session.execute = AsyncMock(return_value=mock_result)

    repo = PostgresChunkRepository(session)
    count = await repo.count_for_tenant(uuid4())

    assert count == 42
    session.execute.assert_called_once()


def test_to_model_maps_all_fields() -> None:
    chunk = _make_chunk(content="Test content", chunk_index=5)
    model = PostgresChunkRepository._to_model(chunk)

    assert model.id == chunk.id
    assert model.document_id == chunk.document_id
    assert model.tenant_id == chunk.tenant_id
    assert model.chunk_index == 5
    assert model.content == "Test content"
    assert model.embedding == chunk.embedding
    assert model.extra_metadata == {}
    assert model.created_at == chunk.created_at
