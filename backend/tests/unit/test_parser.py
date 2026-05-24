"""Unit tests for the document parsers."""

from __future__ import annotations

from src.domain.documents.value_objects import DocumentMimeType
from src.infrastructure.rag.parser import parse


def test_markdown_round_trips_as_text() -> None:
    body = b"# Heading\n\nThis is a paragraph."
    out = parse(body, DocumentMimeType.MARKDOWN)
    assert "Heading" in out
    assert "paragraph" in out


def test_plain_text_passthrough() -> None:
    body = b"Just some plain text."
    out = parse(body, DocumentMimeType.PLAIN)
    assert out.strip() == "Just some plain text."


def test_mime_from_filename() -> None:
    assert DocumentMimeType.from_filename("notes.md") == DocumentMimeType.MARKDOWN
    assert DocumentMimeType.from_filename("report.PDF") == DocumentMimeType.PDF
    assert DocumentMimeType.from_filename("contract.docx") == DocumentMimeType.DOCX
    assert DocumentMimeType.from_filename("readme.txt") == DocumentMimeType.PLAIN
    assert DocumentMimeType.from_filename("image.png") is None
