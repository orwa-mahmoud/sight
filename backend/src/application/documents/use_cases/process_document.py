"""ProcessDocument — parse, chunk, embed and persist a registered document.

Runs in the background after the upload request returns. Moves the document
INGESTING -> READY, or records FAILED with the reason. Failures are captured in
the document's status rather than raised, since there is no request to surface
them to — the owner sees the failure (and reason) in the documents list.
"""

from __future__ import annotations

import structlog

from src.application.documents.commands import ProcessDocument
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.documents.entities import Chunk
from src.domain.rag.ports import ChunkerPort, ContextualizerPort, EmbeddingPort, ParserPort
from src.domain.rag.value_objects import TextChunk
from src.domain.shared.exceptions import InvalidOperationError

logger = structlog.get_logger()

# Cap how many chunks get an LLM-generated context, so a very large document
# can't fan out into unbounded LLM calls.
_MAX_CONTEXTUALIZED_CHUNKS = 100
# Below this chunk count the document is small enough that each chunk already
# carries its context — contextualizing would add LLM cost for no retrieval gain.
_MIN_CHUNKS_FOR_CONTEXT = 3


class ProcessDocumentUseCase:
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

    async def execute(self, cmd: ProcessDocument) -> None:
        doc = await self._uow.documents.get_by_id(cmd.document_id)
        if doc is None:
            logger.warning("process.document_missing", document_id=str(cmd.document_id))
            return

        doc.mark_ingesting()
        await self._uow.documents.save(doc)
        await self._uow.commit()
        # commit ends the transaction, clearing the transaction-local RLS scope —
        # re-apply it for the chunk writes that follow.
        await self._uow.set_tenant_scope(cmd.tenant_id)

        try:
            text = self._parser.parse(cmd.content, doc.mime_type)
            text_chunks = self._chunker.chunk(text)
            if not text_chunks:
                raise InvalidOperationError("Document is empty after parsing")

            # Embed each chunk with an LLM-generated context prepended (Contextual
            # Retrieval); the stored chunk content stays original, only the embedding
            # sees the context. Falls back to the raw chunk if disabled.
            embed_inputs = await self._contextualized_inputs(text, text_chunks)
            embeddings = await self._embedder.embed_documents(embed_inputs)

            chunks = [
                Chunk.create(
                    document_id=doc.id,
                    tenant_id=cmd.tenant_id,
                    chunk_index=chunk.index,
                    content=chunk.content,
                    embedding=embeddings[i],
                    extra_metadata={"source_filename": cmd.filename, **chunk.extra_metadata},
                )
                for i, chunk in enumerate(text_chunks)
            ]
            self._uow.chunks.save_many(chunks)
            doc.mark_ready(chunk_count=len(chunks))
            await self._uow.documents.save(doc)
            await self._uow.commit()
        except Exception as exc:
            logger.warning("process.failed", document_id=str(doc.id), exc_info=True)
            doc.mark_failed(reason=str(exc))
            await self._uow.documents.save(doc)
            await self._uow.commit()

    async def _contextualized_inputs(self, document: str, text_chunks: list[TextChunk]) -> list[str]:
        """Build the per-chunk strings to embed.

        With a contextualizer, each chunk gets a short LLM-generated context line
        prepended (Contextual Retrieval). Without one, for a tiny document, or
        beyond the per-upload cap, the raw chunk is embedded — so this is never
        worse than plain embedding, and small uploads pay no extra LLM cost.
        """
        if self._contextualizer is None or len(text_chunks) < _MIN_CHUNKS_FOR_CONTEXT:
            return [c.content for c in text_chunks]
        inputs: list[str] = []
        for i, chunk in enumerate(text_chunks):
            context = ""
            if i < _MAX_CONTEXTUALIZED_CHUNKS:
                context = await self._contextualizer.contextualize(document=document, chunk=chunk.content)
            inputs.append(f"{context}\n\n{chunk.content}" if context else chunk.content)
        return inputs
