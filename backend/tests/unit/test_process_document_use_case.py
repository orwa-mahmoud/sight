"""Unit tests for the ProcessDocument use case (background ingestion)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.documents.commands import ProcessDocument
from src.application.documents.use_cases.process_document import ProcessDocumentUseCase
from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentMimeType, DocumentStatus
from src.domain.rag.value_objects import TextChunk


def _doc() -> Document:
    mime = DocumentMimeType.from_filename("doc.txt")
    assert mime is not None
    return Document.upload(
        tenant_id=uuid4(), uploaded_by_user_id=uuid4(), filename="doc.txt", mime_type=mime, size_bytes=10
    )


def _uow(doc: Document | None) -> MagicMock:
    uow = MagicMock()
    uow.documents = MagicMock()
    uow.documents.get_by_id = AsyncMock(return_value=doc)
    uow.documents.save = AsyncMock()
    uow.chunks = MagicMock()
    uow.chunks.save_many = MagicMock()
    uow.chunks.delete_for_document = AsyncMock()
    uow.commit = AsyncMock()
    uow.rollback = AsyncMock()
    uow.set_tenant_scope = AsyncMock()
    return uow


def _chunker(chunks: list[TextChunk]) -> MagicMock:
    chunker = MagicMock()
    chunker.chunk.return_value = chunks
    return chunker


def _parser(text: str = "chunk one\nchunk two") -> MagicMock:
    parser = MagicMock()
    parser.parse.return_value = text
    return parser


def _embedder(embeddings: list[list[float]]) -> AsyncMock:
    embedder = AsyncMock()
    embedder.embed_documents.return_value = embeddings
    return embedder


def _cmd(doc: Document) -> ProcessDocument:
    return ProcessDocument(
        tenant_id=doc.tenant_id, document_id=doc.id, filename="doc.txt", content=b"chunk one\nchunk two"
    )


@pytest.mark.asyncio
async def test_process_marks_ready_and_saves_chunks() -> None:
    doc = _doc()
    uow = _uow(doc)
    uc = ProcessDocumentUseCase(
        uow=uow,
        parser=_parser(),
        chunker=_chunker([TextChunk(index=0, content="chunk one"), TextChunk(index=1, content="chunk two")]),
        embedder=_embedder([[0.1, 0.2], [0.3, 0.4]]),
    )

    await uc.execute(_cmd(doc))

    assert doc.status == DocumentStatus.READY
    assert doc.chunk_count == 2
    uow.chunks.save_many.assert_called_once()
    assert len(uow.chunks.save_many.call_args[0][0]) == 2
    uow.chunks.delete_for_document.assert_awaited_once()  # idempotent: prior chunks cleared before re-save
    uow.track.assert_called_with(doc)  # DocumentIngested is dispatched after commit


@pytest.mark.asyncio
async def test_process_empty_after_parsing_marks_failed() -> None:
    doc = _doc()
    uow = _uow(doc)
    uc = ProcessDocumentUseCase(uow=uow, parser=_parser(""), chunker=_chunker([]), embedder=_embedder([]))

    await uc.execute(_cmd(doc))  # background work never raises — it records the failure

    assert doc.status == DocumentStatus.FAILED
    assert doc.error
    uow.commit.assert_awaited()
    uow.track.assert_called_with(doc)  # DocumentIngestionFailed is dispatched after commit


@pytest.mark.asyncio
async def test_process_embedder_failure_marks_failed() -> None:
    doc = _doc()
    uow = _uow(doc)
    embedder = AsyncMock()
    embedder.embed_documents.side_effect = RuntimeError("OpenAI down")
    uc = ProcessDocumentUseCase(
        uow=uow, parser=_parser("text"), chunker=_chunker([TextChunk(index=0, content="text")]), embedder=embedder
    )

    await uc.execute(_cmd(doc))

    assert doc.status == DocumentStatus.FAILED
    assert "OpenAI down" in (doc.error or "")
    uow.commit.assert_awaited()


@pytest.mark.asyncio
async def test_failed_document_has_its_chunks_deleted() -> None:
    """A failure (even an ambiguous work-commit) must leave no retrievable chunks."""
    doc = _doc()
    uow = _uow(doc)
    embedder = AsyncMock()
    embedder.embed_documents.side_effect = RuntimeError("boom")
    uc = ProcessDocumentUseCase(
        uow=uow, parser=_parser("text"), chunker=_chunker([TextChunk(index=0, content="text")]), embedder=embedder
    )

    await uc.execute(_cmd(doc))

    assert doc.status == DocumentStatus.FAILED
    uow.chunks.delete_for_document.assert_awaited_with(doc.id)  # chunks cleaned in the failure path


@pytest.mark.asyncio
async def test_process_missing_document_is_noop() -> None:
    uow = _uow(None)
    uc = ProcessDocumentUseCase(uow=uow, parser=_parser(), chunker=_chunker([]), embedder=_embedder([]))

    await uc.execute(ProcessDocument(tenant_id=uuid4(), document_id=uuid4(), filename="x.txt", content=b"x"))

    uow.documents.save.assert_not_called()


@pytest.mark.asyncio
async def test_failure_during_final_commit_still_records_failed() -> None:
    """If the work commit fails *after* mark_ready advanced the status, the recovery
    handler rolls back, re-fetches, and forces FAILED — the row is never left ingesting."""
    doc = _doc()
    uow = _uow(doc)
    # Commits in order: mark_ingesting (ok), mark_ready (raises), recovery (ok).
    uow.commit = AsyncMock(side_effect=[None, RuntimeError("DB connection lost"), None])
    uc = ProcessDocumentUseCase(
        uow=uow,
        parser=_parser(),
        chunker=_chunker([TextChunk(index=0, content="chunk one"), TextChunk(index=1, content="chunk two")]),
        embedder=_embedder([[0.1, 0.2], [0.3, 0.4]]),
    )

    await uc.execute(_cmd(doc))  # background work never raises

    assert doc.status == DocumentStatus.FAILED  # not left INGESTING or READY
    assert "DB connection lost" in (doc.error or "")
    uow.rollback.assert_awaited()  # the dead work transaction was rolled back
    uow.track.assert_called_with(doc)  # DocumentIngestionFailed still dispatched
