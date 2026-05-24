"""Document value objects."""

from __future__ import annotations

from enum import StrEnum


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"  # raw bytes received, not yet ingested
    INGESTING = "ingesting"  # parse + chunk + embed in progress
    READY = "ready"  # available for retrieval
    FAILED = "failed"  # ingestion errored


class DocumentMimeType(StrEnum):
    """Supported upload types. Anything else is rejected at the API edge."""

    PDF = "application/pdf"
    MARKDOWN = "text/markdown"
    PLAIN = "text/plain"
    DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @classmethod
    def from_filename(cls, filename: str) -> DocumentMimeType | None:
        lowered = filename.lower()
        if lowered.endswith(".pdf"):
            return cls.PDF
        if lowered.endswith((".md", ".markdown")):
            return cls.MARKDOWN
        if lowered.endswith((".txt", ".text")):
            return cls.PLAIN
        if lowered.endswith(".docx"):
            return cls.DOCX
        return None
