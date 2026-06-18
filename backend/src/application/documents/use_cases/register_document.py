"""RegisterDocument — record an uploaded document so it shows up immediately.

The heavy work (parse / chunk / embed) runs separately in ProcessDocument, so
the upload request returns fast and the document appears as ``uploaded`` while it
is processed in the background.
"""

from __future__ import annotations

from src.application.documents.commands import RegisterDocument
from src.application.documents.dtos import DocumentDTO
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.documents.entities import Document
from src.domain.documents.value_objects import DocumentMimeType
from src.domain.shared.exceptions import InvalidOperationError


class RegisterDocumentUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: RegisterDocument) -> DocumentDTO:
        mime = DocumentMimeType.from_filename(cmd.filename)
        if mime is None:
            raise InvalidOperationError(
                "Unsupported file type. Allowed: PDF, DOCX, Markdown, plain text.",
                code="document.unsupported_type",
            )

        doc = Document.upload(
            tenant_id=cmd.tenant_id,
            uploaded_by_user_id=cmd.uploaded_by_user_id,
            filename=cmd.filename,
            mime_type=mime,
            size_bytes=cmd.size_bytes,
        )
        await self._uow.documents.save(doc)
        self._uow.track(doc)
        await self._uow.commit()
        return DocumentDTO(
            id=doc.id,
            filename=doc.filename,
            mime_type=doc.mime_type.value,
            size_bytes=doc.size_bytes,
            status=doc.status.value,
            chunk_count=doc.chunk_count,
            error=doc.error,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )
