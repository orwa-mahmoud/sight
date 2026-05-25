"""Unit tests for the IngestDocument use case."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.application.documents.commands import IngestDocument
from src.application.documents.use_cases.ingest_document import IngestDocumentUseCase
from src.domain.documents.value_objects import DocumentStatus
from src.domain.rag.value_objects import TextChunk
from src.domain.shared.exceptions import InvalidOperationError


def _make_uow() -> MagicMock:
    uow = MagicMock()
    uow.documents = MagicMock()
    uow.documents.save = AsyncMock()
    uow.chunks = MagicMock()
    uow.chunks.save_many = MagicMock()
    uow.flush = AsyncMock()
    return uow


def _make_chunker(chunks: list[TextChunk] | None = None) -> MagicMock:
    chunker = MagicMock()
    if chunks is None:
        chunks = [TextChunk(index=0, content="Hello world")]
    chunker.chunk.return_value = chunks
    return chunker


def _make_embedder(embeddings: list[list[float]] | None = None) -> AsyncMock:
    embedder = AsyncMock()
    if embeddings is None:
        embeddings = [[0.1, 0.2, 0.3]]
    embedder.embed_documents.return_value = embeddings
    return embedder


@pytest.mark.asyncio
async def test_ingest_unsupported_file_type() -> None:
    uow = _make_uow()
    uc = IngestDocumentUseCase(uow=uow, chunker=_make_chunker(), embedder=_make_embedder())
    cmd = IngestDocument(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="data.exe",
        content=b"binary stuff",
    )
    with pytest.raises(InvalidOperationError, match="Unsupported file type"):
        await uc.execute(cmd)


@pytest.mark.asyncio
async def test_ingest_happy_path() -> None:
    uow = _make_uow()
    text_chunks = [
        TextChunk(index=0, content="chunk one"),
        TextChunk(index=1, content="chunk two"),
    ]
    embeddings = [[0.1, 0.2], [0.3, 0.4]]
    chunker = _make_chunker(text_chunks)
    embedder = _make_embedder(embeddings)

    uc = IngestDocumentUseCase(uow=uow, chunker=chunker, embedder=embedder)
    cmd = IngestDocument(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="doc.txt",
        content=b"chunk one\nchunk two",
    )

    with patch(
        "src.application.documents.use_cases.ingest_document.parse",
        return_value="chunk one\nchunk two",
    ):
        dto = await uc.execute(cmd)

    assert dto.status == DocumentStatus.READY.value
    assert dto.chunk_count == 2
    uow.chunks.save_many.assert_called_once()
    saved_chunks = uow.chunks.save_many.call_args[0][0]
    assert len(saved_chunks) == 2


@pytest.mark.asyncio
async def test_ingest_empty_after_parsing_marks_failed() -> None:
    uow = _make_uow()
    chunker = _make_chunker([])  # empty chunks
    embedder = _make_embedder()

    uc = IngestDocumentUseCase(uow=uow, chunker=chunker, embedder=embedder)
    cmd = IngestDocument(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="empty.txt",
        content=b"",
    )

    with (
        patch(
            "src.application.documents.use_cases.ingest_document.parse",
            return_value="",
        ),
        pytest.raises(InvalidOperationError, match="empty after parsing"),
    ):
        await uc.execute(cmd)

    # Document should have been saved with FAILED status
    save_calls = uow.documents.save.call_args_list
    last_saved_doc = save_calls[-1][0][0]
    assert last_saved_doc.status == DocumentStatus.FAILED


@pytest.mark.asyncio
async def test_ingest_embedder_failure_marks_failed() -> None:
    uow = _make_uow()
    chunker = _make_chunker([TextChunk(index=0, content="text")])
    embedder = AsyncMock()
    embedder.embed_documents.side_effect = RuntimeError("OpenAI down")

    uc = IngestDocumentUseCase(uow=uow, chunker=chunker, embedder=embedder)
    cmd = IngestDocument(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="notes.md",
        content=b"Some markdown content",
    )

    with (
        patch(
            "src.application.documents.use_cases.ingest_document.parse",
            return_value="text",
        ),
        pytest.raises(RuntimeError, match="OpenAI down"),
    ):
        await uc.execute(cmd)

    save_calls = uow.documents.save.call_args_list
    last_saved_doc = save_calls[-1][0][0]
    assert last_saved_doc.status == DocumentStatus.FAILED
    assert "OpenAI down" in (last_saved_doc.error or "")


@pytest.mark.asyncio
async def test_ingest_to_dto_conversion() -> None:
    """Ensure _to_dto produces a correct DocumentDTO."""
    uow = _make_uow()
    chunker = _make_chunker([TextChunk(index=0, content="hello")])
    embedder = _make_embedder([[0.1]])

    uc = IngestDocumentUseCase(uow=uow, chunker=chunker, embedder=embedder)
    cmd = IngestDocument(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="readme.md",
        content=b"hello",
    )

    with patch(
        "src.application.documents.use_cases.ingest_document.parse",
        return_value="hello",
    ):
        dto = await uc.execute(cmd)

    assert dto.filename == "readme.md"
    assert dto.mime_type == "text/markdown"
    assert dto.size_bytes == 5
    assert dto.error is None
