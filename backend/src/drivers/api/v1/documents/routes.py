"""Documents routes — upload, list, delete, retrieve."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

import structlog
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, UploadFile, status

from src.application.documents.commands import ProcessDocument, RegisterDocument
from src.application.documents.queries import ListDocuments, RetrieveForQuery
from src.application.documents.use_cases.delete_document import DeleteDocumentUseCase
from src.application.documents.use_cases.list_documents import ListDocumentsUseCase
from src.application.documents.use_cases.process_document import ProcessDocumentUseCase
from src.application.documents.use_cases.register_document import RegisterDocumentUseCase
from src.application.documents.use_cases.retrieve_for_query import RetrieveForQueryUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import EntityNotFoundError
from src.domain.tenant_config.entities import TenantConfig
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep, resolve_tenant_id
from src.drivers.api.v1.documents.schemas import (
    DocumentSummary,
    RetrievedChunkResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from src.infrastructure.llm.tenant_factory import TenantLLMClientFactory
from src.infrastructure.persistence.postgres.database import async_session_factory
from src.infrastructure.rag.chunker import RecursiveTokenChunker
from src.infrastructure.rag.contextualizer import LLMContextualizer
from src.infrastructure.rag.embedder import OpenAIEmbedder
from src.infrastructure.rag.parser import DocumentParser
from src.infrastructure.rag.retriever import HybridRetriever

router = APIRouter(prefix="/documents", tags=["documents"])

logger = structlog.get_logger()

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB hard cap for v1


async def _load_tenant_config(tenant_id: UUID, uow: UnitOfWork) -> TenantConfig:
    config: TenantConfig | None = await uow.tenant_configs.get_by_tenant_id(tenant_id)
    if config is None:
        raise EntityNotFoundError("Tenant configuration not found")
    return config


_EMBEDDING_DIMENSIONS = 1536


def _build_embedder(config: TenantConfig) -> OpenAIEmbedder:
    return OpenAIEmbedder(
        api_key=config.embedding_api_key or config.llm_api_key,
        model=config.embedding_model,
        dimensions=_EMBEDDING_DIMENSIONS,
    )


_llm_factory = TenantLLMClientFactory()


def _build_contextualizer(tenant_id: UUID, config: TenantConfig) -> LLMContextualizer | None:
    """Contextual Retrieval needs the tenant's LLM — skip when none is configured."""
    if not config.llm_api_key:
        return None
    return LLMContextualizer(_llm_factory.get_or_build(tenant_id, config))


async def _process_document_in_background(
    *, tenant_id: UUID, document_id: UUID, filename: str, content: bytes, config: TenantConfig
) -> None:
    """Parse + chunk + embed a registered document off the request, in its own
    session. Failures are recorded on the document; this never raises."""
    try:
        async with async_session_factory() as session:
            uow = UnitOfWork(session)
            await uow.set_tenant_scope(tenant_id)
            use_case = ProcessDocumentUseCase(
                uow=uow,
                parser=DocumentParser(),
                chunker=RecursiveTokenChunker(),
                embedder=_build_embedder(config),
                contextualizer=_build_contextualizer(tenant_id, config),
            )
            await use_case.execute(
                ProcessDocument(tenant_id=tenant_id, document_id=document_id, filename=filename, content=content)
            )
    except Exception:
        logger.error("documents.background_ingest_failed", document_id=str(document_id), exc_info=True)


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Unsupported file type"}, 413: {"description": "File too large (25 MB max)"}},
)
async def upload_document(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File()],
) -> DocumentSummary:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    # Reject oversized uploads from the declared size before buffering the whole
    # body into memory; re-check the actual bytes in case the size was unknown.
    if file.size is not None and file.size > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (25 MB max)")
    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (25 MB max)")

    tenant_id = await resolve_tenant_id(current_user, uow)
    config = await _load_tenant_config(tenant_id, uow)

    # Record the document synchronously (so it appears immediately and bad file
    # types are rejected now), then parse + chunk + embed it in the background so
    # a large upload never blocks the request. The frontend polls for the status.
    dto = await RegisterDocumentUseCase(uow=uow).execute(
        RegisterDocument(
            tenant_id=tenant_id,
            uploaded_by_user_id=current_user.id,
            filename=file.filename,
            size_bytes=len(content),
        )
    )
    background_tasks.add_task(
        _process_document_in_background,
        tenant_id=tenant_id,
        document_id=dto.id,
        filename=file.filename,
        content=content,
        config=config,
    )
    return DocumentSummary(
        id=dto.id,
        filename=dto.filename,
        mime_type=dto.mime_type,
        size_bytes=dto.size_bytes,
        status=dto.status,
        chunk_count=dto.chunk_count,
        error=dto.error,
        created_at=dto.created_at,
        updated_at=dto.updated_at,
    )


@router.get("")
async def list_documents(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentSummary]:
    tenant_id = await resolve_tenant_id(current_user, uow)
    dtos = await ListDocumentsUseCase(uow=uow).execute(ListDocuments(tenant_id=tenant_id, limit=limit, offset=offset))
    return [
        DocumentSummary(
            id=d.id,
            filename=d.filename,
            mime_type=d.mime_type,
            size_bytes=d.size_bytes,
            status=d.status,
            chunk_count=d.chunk_count,
            error=d.error,
            created_at=d.created_at,
            updated_at=d.updated_at,
        )
        for d in dtos
    ]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> None:
    tenant_id = await resolve_tenant_id(current_user, uow)
    await DeleteDocumentUseCase(uow=uow).execute(tenant_id=tenant_id, document_id=document_id)


@router.post("/retrieve")
async def retrieve(
    req: RetrieveRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> RetrieveResponse:
    """Test endpoint: run the hybrid retriever and return the matched chunks
    + RRF scores. Useful for tuning the index and for the future "trace" UI."""
    tenant_id = await resolve_tenant_id(current_user, uow)
    config = await _load_tenant_config(tenant_id, uow)
    retriever = HybridRetriever(session=uow._session, embedder=_build_embedder(config))
    dtos = await RetrieveForQueryUseCase(retriever=retriever).execute(
        RetrieveForQuery(tenant_id=tenant_id, query=req.query, top_k=req.top_k)
    )
    return RetrieveResponse(
        results=[
            RetrievedChunkResponse(
                chunk_id=d.chunk_id,
                document_id=d.document_id,
                content=d.content,
                score=d.score,
            )
            for d in dtos
        ]
    )
