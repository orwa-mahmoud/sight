"""Parsers for the supported document mime types.

PDF -> pypdf; DOCX -> python-docx; MD/TXT -> straight UTF-8 decode.
Each parser returns plain text; structure (headings, tables) is preserved
only insofar as the source format renders it as paragraph breaks.
"""

from __future__ import annotations

import io

from pypdf import PdfReader

from src.domain.documents.value_objects import DocumentMimeType
from src.domain.shared.exceptions import InvalidOperationError


def parse(content: bytes, mime_type: DocumentMimeType) -> str:
    match mime_type:
        case DocumentMimeType.PDF:
            return _parse_pdf(content)
        case DocumentMimeType.DOCX:
            return _parse_docx(content)
        case DocumentMimeType.MARKDOWN | DocumentMimeType.PLAIN:
            return content.decode("utf-8", errors="replace")


def _parse_pdf(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n\n".join(p.strip() for p in pages if p.strip())
    except Exception as exc:
        raise InvalidOperationError(f"Could not parse PDF: {exc}") from exc


def _parse_docx(content: bytes) -> str:
    try:
        from docx import Document as DocxDocument  # noqa: PLC0415

        doc = DocxDocument(io.BytesIO(content))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n\n".join(paragraphs)
    except Exception as exc:
        raise InvalidOperationError(f"Could not parse DOCX: {exc}") from exc
