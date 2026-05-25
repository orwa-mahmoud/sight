"""Full parser tests including PDF."""

from __future__ import annotations

import io

import pytest

from src.domain.documents.value_objects import DocumentMimeType
from src.domain.shared.exceptions import InvalidOperationError
from src.infrastructure.rag.parser import parse


def test_parse_plain_text() -> None:
    text = parse(b"Hello world", DocumentMimeType.PLAIN)
    assert text == "Hello world"


def test_parse_markdown() -> None:
    text = parse(b"# Title\n\nContent here.", DocumentMimeType.MARKDOWN)
    assert "Title" in text
    assert "Content" in text


def test_parse_pdf_valid() -> None:
    """Create a minimal valid PDF to test the parser."""
    from pypdf import PdfWriter  # noqa: PLC0415

    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    # pypdf doesn't support adding text to blank pages easily,
    # but we can test that parsing doesn't crash.
    buf = io.BytesIO()
    writer.write(buf)
    buf.seek(0)
    text = parse(buf.read(), DocumentMimeType.PDF)
    assert isinstance(text, str)


def test_parse_pdf_invalid_raises() -> None:
    with pytest.raises(InvalidOperationError, match="Could not parse PDF"):
        parse(b"not a pdf", DocumentMimeType.PDF)


def test_parse_docx_invalid_raises() -> None:
    with pytest.raises(InvalidOperationError, match="Could not parse DOCX"):
        parse(b"not a docx", DocumentMimeType.DOCX)
