"""Unit tests for the OpenAI embedder — covers embed_documents and embed_query with mocked API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.rag.embedder import OpenAIEmbedder


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "_get_client")
async def test_embed_documents_calls_api(mock_get_client: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_embedding_1 = MagicMock()
    mock_embedding_1.embedding = [0.1, 0.2, 0.3]
    mock_embedding_2 = MagicMock()
    mock_embedding_2.embedding = [0.4, 0.5, 0.6]
    mock_response = MagicMock()
    mock_response.data = [mock_embedding_1, mock_embedding_2]
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    embedder = OpenAIEmbedder(api_key="sk-test-key-12345678")

    result = await embedder.embed_documents(["Hello", "World"])
    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_client.embeddings.create.assert_called_once()


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "_get_client")
async def test_embed_documents_replaces_blank_with_space(mock_get_client: MagicMock) -> None:
    """Texts that are blank (only whitespace) should be replaced with a single space."""
    mock_client = AsyncMock()
    mock_embedding = MagicMock()
    mock_embedding.embedding = [0.0, 0.0, 0.0]
    mock_response = MagicMock()
    mock_response.data = [mock_embedding]
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    embedder = OpenAIEmbedder(api_key="sk-test-key-12345678")

    await embedder.embed_documents(["   "])  # blank text
    call_args = mock_client.embeddings.create.call_args
    # The "input" kwarg should contain [" "] not ["   "]
    assert call_args.kwargs["input"] == [" "]


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "embed_documents")
async def test_embed_query_delegates_to_embed_documents(mock_embed_docs: AsyncMock) -> None:
    mock_embed_docs.return_value = [[0.1, 0.2]]

    embedder = OpenAIEmbedder(api_key="sk-test-key-12345678")
    result = await embedder.embed_query("hello")
    assert result == [0.1, 0.2]
    mock_embed_docs.assert_called_once_with(["hello"])


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "embed_documents")
async def test_embed_query_returns_empty_when_no_results(mock_embed_docs: AsyncMock) -> None:
    mock_embed_docs.return_value = []

    embedder = OpenAIEmbedder(api_key="sk-test-key-12345678")
    result = await embedder.embed_query("hello")
    assert result == []
