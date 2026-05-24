"""Unit tests for document mime type resolution."""

from __future__ import annotations

from src.domain.documents.value_objects import DocumentMimeType, DocumentStatus


def test_mime_from_filename_all_supported() -> None:
    assert DocumentMimeType.from_filename("file.pdf") == DocumentMimeType.PDF
    assert DocumentMimeType.from_filename("FILE.PDF") == DocumentMimeType.PDF
    assert DocumentMimeType.from_filename("notes.md") == DocumentMimeType.MARKDOWN
    assert DocumentMimeType.from_filename("notes.markdown") == DocumentMimeType.MARKDOWN
    assert DocumentMimeType.from_filename("readme.txt") == DocumentMimeType.PLAIN
    assert DocumentMimeType.from_filename("readme.text") == DocumentMimeType.PLAIN
    assert DocumentMimeType.from_filename("contract.docx") == DocumentMimeType.DOCX


def test_mime_unsupported_returns_none() -> None:
    assert DocumentMimeType.from_filename("image.png") is None
    assert DocumentMimeType.from_filename("data.csv") is None
    assert DocumentMimeType.from_filename("script.py") is None


def test_document_status_values() -> None:
    assert DocumentStatus.UPLOADED == "uploaded"
    assert DocumentStatus.READY == "ready"
    assert DocumentStatus.FAILED == "failed"
