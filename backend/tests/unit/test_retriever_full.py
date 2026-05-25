"""Unit tests for the hybrid retriever — vector search, BM25, and full hybrid_retrieve."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.infrastructure.rag.retriever import HybridRetriever


def _make_chunk(chunk_id=None, document_id=None, tenant_id=None, content="text", extra_metadata=None):
    """Build a mock ChunkModel with required fields."""
    c = MagicMock()
    c.id = chunk_id or uuid4()
    c.document_id = document_id or uuid4()
    c.tenant_id = tenant_id or uuid4()
    c.content = content
    c.extra_metadata = extra_metadata or {}
    return c


@pytest.mark.asyncio
async def test_hybrid_retrieve_empty_query_returns_empty() -> None:
    session = AsyncMock()
    embedder = AsyncMock()
    retriever = HybridRetriever(session=session, embedder=embedder)

    result = await retriever.hybrid_retrieve(query="", tenant_id=uuid4())
    assert result == []
    embedder.embed_query.assert_not_called()


@pytest.mark.asyncio
async def test_hybrid_retrieve_whitespace_query_returns_empty() -> None:
    session = AsyncMock()
    embedder = AsyncMock()
    retriever = HybridRetriever(session=session, embedder=embedder)

    result = await retriever.hybrid_retrieve(query="   ", tenant_id=uuid4())
    assert result == []


@pytest.mark.asyncio
async def test_hybrid_retrieve_fuses_vector_and_bm25() -> None:
    tenant_id = uuid4()
    doc_id = uuid4()

    chunk_a = _make_chunk(tenant_id=tenant_id, document_id=doc_id, content="alpha")
    chunk_b = _make_chunk(tenant_id=tenant_id, document_id=doc_id, content="beta")
    chunk_c = _make_chunk(tenant_id=tenant_id, document_id=doc_id, content="gamma")

    session = AsyncMock()
    embedder = AsyncMock()
    embedder.embed_query = AsyncMock(return_value=[0.1, 0.2, 0.3])

    retriever = HybridRetriever(session=session, embedder=embedder)

    # Mock internal search methods
    retriever._vector_search = AsyncMock(return_value=[chunk_a, chunk_b])
    retriever._bm25_search = AsyncMock(return_value=[chunk_b, chunk_c])

    results = await retriever.hybrid_retrieve(query="test query", tenant_id=tenant_id, top_k=2)

    embedder.embed_query.assert_called_once_with("test query")
    assert len(results) <= 2
    # chunk_b appears in both lists, should be ranked first
    assert results[0].chunk_id == chunk_b.id
    assert results[0].content == "beta"
    assert results[0].tenant_id == tenant_id
    assert results[0].document_id == doc_id
    assert results[0].score > 0


@pytest.mark.asyncio
async def test_vector_search_returns_empty_for_empty_embedding() -> None:
    session = AsyncMock()
    embedder = AsyncMock()
    retriever = HybridRetriever(session=session, embedder=embedder)

    result = await retriever._vector_search([], uuid4(), 10)
    assert result == []


@pytest.mark.asyncio
async def test_vector_search_executes_query() -> None:
    mock_scalars = MagicMock()
    chunk = _make_chunk()
    mock_scalars.all.return_value = [chunk]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    embedder = AsyncMock()
    retriever = HybridRetriever(session=session, embedder=embedder)

    result = await retriever._vector_search([0.1, 0.2], uuid4(), 10)
    assert len(result) == 1
    assert result[0] is chunk
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_bm25_search_executes_query() -> None:
    mock_scalars = MagicMock()
    chunk = _make_chunk()
    mock_scalars.all.return_value = [chunk]
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    embedder = AsyncMock()
    retriever = HybridRetriever(session=session, embedder=embedder)

    result = await retriever._bm25_search("hello world", uuid4(), 10)
    assert len(result) == 1
    assert result[0] is chunk
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_hybrid_retrieve_respects_top_k() -> None:
    tenant_id = uuid4()
    doc_id = uuid4()

    chunks = [_make_chunk(tenant_id=tenant_id, document_id=doc_id) for _ in range(5)]

    session = AsyncMock()
    embedder = AsyncMock()
    embedder.embed_query = AsyncMock(return_value=[0.1])

    retriever = HybridRetriever(session=session, embedder=embedder)
    retriever._vector_search = AsyncMock(return_value=chunks[:3])
    retriever._bm25_search = AsyncMock(return_value=chunks[2:])

    results = await retriever.hybrid_retrieve(query="test", tenant_id=tenant_id, top_k=2)
    assert len(results) <= 2
