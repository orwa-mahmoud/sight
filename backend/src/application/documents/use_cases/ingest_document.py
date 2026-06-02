"""IngestDocument — parse + chunk + embed + persist in one transaction.

The use case orchestrates ports (chunker, embedder) without knowing their
implementations. Errors during parsing or embedding mark the document FAILED
without losing the upload metadata, so the owner can see what happened.
"""

from __future__ import annotations

import structlog

from src.application.documents.commands import IngestDocument
from src.application.documents.dtos import DocumentDTO
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.documents.entities import Chunk, Document
from src.domain.documents.value_objects import DocumentMimeType
from src.domain.rag.ports import ChunkerPort, EmbeddingPort, ParserPort
from src.domain.shared.exceptions import InvalidOperationError

logger = structlog.get_logger()


class IngestDocumentUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        parser: ParserPort,
        chunker: ChunkerPort,
        embedder: EmbeddingPort,
    ) -> None:
        self._uow = uow
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder

    async def execute(self, cmd: IngestDocument) -> DocumentDTO:
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
            size_bytes=len(cmd.content),
        )
        await self._uow.documents.save(doc)
        await self._uow.flush()  # flush INSERT so the row exists for the UPDATE
        doc.mark_ingesting()
        await self._uow.documents.save(doc)
        await self._uow.flush()

        try:
            text = self._parser.parse(cmd.content, mime)
            text_chunks = self._chunker.chunk(text)
            if not text_chunks:
                raise InvalidOperationError("Document is empty after parsing")

            embeddings = await self._embedder.embed_documents([c.content for c in text_chunks])

            chunks = [
                Chunk.create(
                    document_id=doc.id,
                    tenant_id=cmd.tenant_id,
                    chunk_index=text_chunks[i].index,
                    content=text_chunks[i].content,
                    embedding=embeddings[i],
                    extra_metadata={"source_filename": cmd.filename, **text_chunks[i].extra_metadata},
                )
                for i in range(len(text_chunks))
            ]
            self._uow.chunks.save_many(chunks)
            doc.mark_ready(chunk_count=len(chunks))
            await self._uow.documents.save(doc)
        except Exception as exc:
            logger.warning("ingest.failed", document_id=str(doc.id), exc_info=True)
            doc.mark_failed(reason=str(exc))
            await self._uow.documents.save(doc)
            # Commit the terminal FAILED state before propagating. The request's
            # session rolls back on the re-raised exception, which would otherwise
            # discard the failed row — leaving the owner with no record of what
            # went wrong. Committing here keeps the failure visible in the list.
            await self._uow.commit()
            raise

        self._uow.track(doc)
        return _to_dto(doc)


def _to_dto(doc: Document) -> DocumentDTO:
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
