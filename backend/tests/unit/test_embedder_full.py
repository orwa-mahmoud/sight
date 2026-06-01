"""Unit tests for the OpenAI embedder — covers embed_documents and embed_query with mocked API."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.domain.shared.exceptions import InvalidOperationError
from src.infrastructure.rag.embedder import OpenAIEmbedder

_TEST_KEY = "sk-test-12345678"  # fake credential for tests only


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "_get_client")
async def test_embed_documents_calls_api(mock_get_client: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_embedding_1 = MagicMock()
    mock_embedding_1.embedding = [0.1, 0.2, 0.3]
    mock_embedding_1.index = 0
    mock_embedding_2 = MagicMock()
    mock_embedding_2.embedding = [0.4, 0.5, 0.6]
    mock_embedding_2.index = 1
    mock_response = MagicMock()
    mock_response.data = [mock_embedding_1, mock_embedding_2]
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    embedder = OpenAIEmbedder(api_key=_TEST_KEY, model="text-embedding-3-large", dimensions=1536)

    result = await embedder.embed_documents(["Hello", "World"])
    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    mock_client.embeddings.create.assert_called_once()


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "_get_client")
async def test_embed_documents_orders_by_index(mock_get_client: MagicMock) -> None:
    """Embeddings returned out of order must be realigned to input order via `index`."""
    mock_client = AsyncMock()
    first = MagicMock(embedding=[1.0], index=1)
    second = MagicMock(embedding=[0.0], index=0)
    mock_response = MagicMock()
    mock_response.data = [first, second]  # deliberately out of order
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    embedder = OpenAIEmbedder(api_key=_TEST_KEY, model="text-embedding-3-large", dimensions=1536)
    result = await embedder.embed_documents(["a", "b"])
    assert result == [[0.0], [1.0]]


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "_get_client")
async def test_embed_documents_preserves_order_across_batches(mock_get_client: MagicMock) -> None:
    """Large inputs span multiple 512-batches; vectors must stay aligned to inputs.

    OpenAI's `index` is per-request (0-based within each batch), so correctness
    relies on sorting within each batch AND extending batches in call order.
    """

    def make_resp(offset: int, count: int) -> MagicMock:
        # data deliberately reversed to exercise the within-batch index sort.
        items = [MagicMock(embedding=[offset + i], index=i) for i in range(count)]
        resp = MagicMock()
        resp.data = list(reversed(items))
        return resp

    mock_client = AsyncMock()
    # 513 inputs with _BATCH_SIZE=512 → two calls: 512 then 1.
    mock_client.embeddings.create = AsyncMock(side_effect=[make_resp(0, 512), make_resp(1000, 1)])
    mock_get_client.return_value = mock_client

    embedder = OpenAIEmbedder(api_key=_TEST_KEY, model="text-embedding-3-large", dimensions=1536)
    result = await embedder.embed_documents([f"t{i}" for i in range(513)])

    assert len(result) == 513
    assert result[0] == [0]
    assert result[511] == [511]
    assert result[512] == [1000]  # first (only) vector of the second batch
    assert mock_client.embeddings.create.await_count == 2


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "_get_client")
async def test_embed_documents_count_mismatch_raises(mock_get_client: MagicMock) -> None:
    """A provider returning the wrong number of vectors must fail loudly, not misalign."""
    mock_client = AsyncMock()
    only_one = MagicMock(embedding=[0.1], index=0)
    mock_response = MagicMock()
    mock_response.data = [only_one]  # one vector for two inputs
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    embedder = OpenAIEmbedder(api_key=_TEST_KEY, model="text-embedding-3-large", dimensions=1536)
    with pytest.raises(InvalidOperationError, match="1 vectors for 2 chunks"):
        await embedder.embed_documents(["a", "b"])


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "_get_client")
async def test_embed_documents_replaces_blank_with_space(mock_get_client: MagicMock) -> None:
    """Texts that are blank (only whitespace) should be replaced with a single space."""
    mock_client = AsyncMock()
    mock_embedding = MagicMock()
    mock_embedding.embedding = [0.0, 0.0, 0.0]
    mock_embedding.index = 0
    mock_response = MagicMock()
    mock_response.data = [mock_embedding]
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)
    mock_get_client.return_value = mock_client

    embedder = OpenAIEmbedder(api_key=_TEST_KEY, model="text-embedding-3-large", dimensions=1536)

    await embedder.embed_documents(["   "])  # blank text
    call_args = mock_client.embeddings.create.call_args
    # The "input" kwarg should contain [" "] not ["   "]
    assert call_args.kwargs["input"] == [" "]


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "embed_documents")
async def test_embed_query_delegates_to_embed_documents(mock_embed_docs: AsyncMock) -> None:
    mock_embed_docs.return_value = [[0.1, 0.2]]

    embedder = OpenAIEmbedder(api_key=_TEST_KEY, model="text-embedding-3-large", dimensions=1536)
    result = await embedder.embed_query("hello")
    assert result == [0.1, 0.2]
    mock_embed_docs.assert_called_once_with(["hello"])


@pytest.mark.asyncio
@patch.object(OpenAIEmbedder, "embed_documents")
async def test_embed_query_returns_empty_when_no_results(mock_embed_docs: AsyncMock) -> None:
    mock_embed_docs.return_value = []

    embedder = OpenAIEmbedder(api_key=_TEST_KEY, model="text-embedding-3-large", dimensions=1536)
    result = await embedder.embed_query("hello")
    assert result == []


@pytest.mark.asyncio
async def test_close_releases_client_and_is_idempotent() -> None:
    embedder = OpenAIEmbedder(api_key=_TEST_KEY, model="text-embedding-3-large", dimensions=1536)
    await embedder.close()  # no client built yet — must be a safe no-op

    mock_client = AsyncMock()
    embedder._client = mock_client
    await embedder.close()
    mock_client.close.assert_awaited_once()
    assert embedder._client is None
