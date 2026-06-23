"""Edge case tests for Document entity state transitions."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentMimeType, DocumentStatus
from src.domain.shared.exceptions import InvalidOperationError


def test_cannot_ingest_from_ready() -> None:
    d = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=None,
        filename="a.pdf",
        mime_type=DocumentMimeType.PDF,
        size_bytes=100,
    )
    d.mark_ingesting()
    d.mark_ready(chunk_count=5)
    with pytest.raises(InvalidOperationError):
        d.mark_ingesting()


def test_can_re_ingest_after_failure() -> None:
    d = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=None,
        filename="b.pdf",
        mime_type=DocumentMimeType.PDF,
        size_bytes=100,
    )
    d.mark_ingesting()
    d.mark_failed(reason="timeout")
    d.mark_ingesting()
    assert d.status == DocumentStatus.INGESTING
    assert d.error is None


def test_mark_failed_truncates_long_reason() -> None:
    d = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=None,
        filename="c.pdf",
        mime_type=DocumentMimeType.PDF,
        size_bytes=100,
    )
    d.mark_ingesting()
    d.mark_failed(reason="x" * 2000)
    assert len(d.error or "") <= 1024


def test_force_failed_from_ready_and_idempotent() -> None:
    d = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=None,
        filename="d.pdf",
        mime_type=DocumentMimeType.PDF,
        size_bytes=100,
    )
    d.mark_ingesting()
    d.mark_ready(chunk_count=5)
    # mark_failed rejects a READY doc; force_failed is the recovery escape hatch.
    with pytest.raises(InvalidOperationError):
        d.mark_failed(reason="late error")
    d.force_failed(reason="late error")
    assert d.status == DocumentStatus.FAILED
    assert d.error == "late error"
    # Idempotent: forcing failure on an already-failed doc keeps the first reason.
    d.force_failed(reason="second error")
    assert d.error == "late error"


def test_upload_events() -> None:
    d = Document.upload(
        tenant_id=uuid4(),
        uploaded_by_user_id=uuid4(),
        filename="d.md",
        mime_type=DocumentMimeType.MARKDOWN,
        size_bytes=50,
    )
    assert len(d.pending_events) == 1
    d.mark_ingesting()
    d.mark_ready(chunk_count=3)
    assert len(d.pending_events) == 2  # DocumentUploaded + DocumentIngested
