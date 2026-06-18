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
from src.domain.rag.ports import ChunkerPort, ContextualizerPort, EmbeddingPort, ParserPort
from src.domain.rag.value_objects import TextChunk
from src.domain.shared.exceptions import InvalidOperationError

logger = structlog.get_logger()

# Cap how many chunks get an LLM-generated context per upload, so a very large
# document can't fan out into unbounded LLM calls during a synchronous ingest.
_MAX_CONTEXTUALIZED_CHUNKS = 100


class IngestDocumentUseCase:
    def __init__(
        self,
        *,
        uow: UnitOfWork,
        parser: ParserPort,
        chunker: ChunkerPort,
        embedder: EmbeddingPort,
        contextualizer: ContextualizerPort | None = None,
    ) -> None:
        self._uow = uow
        self._parser = parser
        self._chunker = chunker
        self._embedder = embedder
        self._contextualizer = contextualizer

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

            # Embed each chunk with an LLM-generated context prepended (Contextual
            # Retrieval); the stored chunk content stays the original, only the
            # embedding sees the context. Falls back to the raw chunk if disabled.
            embed_inputs = await self._contextualized_inputs(text, text_chunks)
            embeddings = await self._embedder.embed_documents(embed_inputs)

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

    async def _contextualized_inputs(self, document: str, text_chunks: list[TextChunk]) -> list[str]:
        """Build the per-chunk strings to embed.

        With a contextualizer, each chunk gets a short LLM-generated context line
        prepended (Contextual Retrieval). Without one — or beyond the per-upload
        cap — the raw chunk is embedded, so this is never worse than plain embedding.
        """
        if self._contextualizer is None:
            return [c.content for c in text_chunks]
        inputs: list[str] = []
        for i, chunk in enumerate(text_chunks):
            context = ""
            if i < _MAX_CONTEXTUALIZED_CHUNKS:
                context = await self._contextualizer.contextualize(document=document, chunk=chunk.content)
            inputs.append(f"{context}\n\n{chunk.content}" if context else chunk.content)
        return inputs


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
