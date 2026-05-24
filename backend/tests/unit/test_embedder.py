"""Unit tests for the OpenAI embedder — construction + lazy client."""

from __future__ import annotations

import pytest

from src.domain.shared.exceptions import InvalidOperationError
from src.infrastructure.rag.embedder import OpenAIEmbedder


def test_embedder_defers_client_creation() -> None:
    embedder = OpenAIEmbedder(api_key="")
    assert embedder._client is None


def test_embedder_raises_on_empty_key_at_call_time() -> None:
    embedder = OpenAIEmbedder(api_key="")
    with pytest.raises(InvalidOperationError, match="API key not configured"):
        embedder._get_client()


def test_embedder_creates_client_with_key() -> None:
    embedder = OpenAIEmbedder(api_key="sk-test-key-12345678")
    client = embedder._get_client()
    assert client is not None


def test_embedder_dimensions() -> None:
    embedder = OpenAIEmbedder(api_key="sk-x", dimensions=768)
    assert embedder.dimensions == 768


@pytest.mark.asyncio
async def test_embed_documents_empty_returns_empty() -> None:
    embedder = OpenAIEmbedder(api_key="sk-x")
    result = await embedder.embed_documents([])
    assert result == []
