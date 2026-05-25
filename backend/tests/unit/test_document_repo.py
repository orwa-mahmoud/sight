"""Unit tests for PostgresDocumentRepository — save update-path and _to_entity/_to_model."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentMimeType, DocumentStatus
from src.infrastructure.persistence.postgres.repositories.document_repo import PostgresDocumentRepository


def _make_document(**overrides) -> Document:
    return Document.upload(
        tenant_id=overrides.get("tenant_id", uuid4()),
        uploaded_by_user_id=overrides.get("uploaded_by_user_id", uuid4()),
        filename=overrides.get("filename", "test.pdf"),
        mime_type=overrides.get("mime_type", DocumentMimeType.PDF),
        size_bytes=overrides.get("size_bytes", 1024),
    )


@pytest.mark.asyncio
async def test_save_existing_not_found_inserts() -> None:
    """When a persisted document is not found in DB (None from session.get), add it."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()  # add is sync

    repo = PostgresDocumentRepository(session)
    doc = _make_document()
    doc.mark_persisted()  # simulate already persisted (not new)

    await repo.save(doc)

    session.get.assert_called_once()
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_save_existing_updates_fields() -> None:
    """When a persisted document IS found, update the mutable fields in place."""
    existing_model = MagicMock()
    session = AsyncMock()
    session.get = AsyncMock(return_value=existing_model)

    repo = PostgresDocumentRepository(session)
    doc = _make_document(filename="updated.pdf")
    doc.mark_persisted()
    doc.mark_ready(chunk_count=10)

    await repo.save(doc)

    assert existing_model.filename == "updated.pdf"
    assert existing_model.status == DocumentStatus.READY.value
    assert existing_model.chunk_count == 10
    assert existing_model.error == doc.error
    assert existing_model.updated_at == doc.updated_at
    # Should NOT call session.add because we're updating in-place
    session.add.assert_not_called()


def test_to_model_maps_all_fields() -> None:
    doc = _make_document(filename="report.pdf", size_bytes=4096)
    model = PostgresDocumentRepository._to_model(doc)

    assert model.id == doc.id
    assert model.tenant_id == doc.tenant_id
    assert model.filename == "report.pdf"
    assert model.mime_type == DocumentMimeType.PDF.value
    assert model.size_bytes == 4096
    assert model.status == DocumentStatus.UPLOADED.value


def test_to_entity_maps_all_fields() -> None:
    model = MagicMock()
    model.id = uuid4()
    model.tenant_id = uuid4()
    model.uploaded_by_user_id = uuid4()
    model.filename = "notes.md"
    model.mime_type = DocumentMimeType.MARKDOWN.value
    model.size_bytes = 512
    model.status = DocumentStatus.READY.value
    model.chunk_count = 3
    model.error = None
    model.created_at = datetime.now(UTC)
    model.updated_at = datetime.now(UTC)

    entity = PostgresDocumentRepository._to_entity(model)

    assert entity.id == model.id
    assert entity.filename == "notes.md"
    assert entity.mime_type == DocumentMimeType.MARKDOWN
    assert entity.status == DocumentStatus.READY
    assert entity.chunk_count == 3
