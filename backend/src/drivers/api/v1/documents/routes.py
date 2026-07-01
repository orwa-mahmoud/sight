"""Documents routes — upload, list, delete, retrieve."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from src.application.documents.commands import RegisterDocument
from src.application.documents.dtos import DocumentDTO
from src.application.documents.queries import ListDocuments, ListProcessingDocuments, RetrieveForQuery
from src.application.documents.use_cases.delete_document import DeleteDocumentUseCase
from src.application.documents.use_cases.list_documents import ListDocumentsUseCase
from src.application.documents.use_cases.list_processing_documents import ListProcessingDocumentsUseCase
from src.application.documents.use_cases.register_document import RegisterDocumentUseCase
from src.application.documents.use_cases.retrieve_for_query import RetrieveForQueryUseCase
from src.application.llm_usage.commands import RecordTokenUsage
from src.application.llm_usage.use_cases.record_token_usage import RecordTokenUsageUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.config.settings import get_settings
from src.domain.llm.usage_sink import LLMUsageSink
from src.domain.shared.exceptions import EntityNotFoundError
from src.domain.tenant_config.entities import TenantConfig
from src.drivers.api.dependencies import CurrentUser, JobPoolDep, UnitOfWorkDep, resolve_tenant_id
from src.drivers.api.v1.documents.schemas import (
    DocumentSummary,
    RetrievedChunkResponse,
    RetrieveRequest,
    RetrieveResponse,
)
from src.drivers.jobs.ingestion import document_storage
from src.drivers.jobs.queue import enqueue_document_ingestion
from src.infrastructure.llm.client import LangChainLLMClient
from src.infrastructure.rag.embedder import OpenAIEmbedder
from src.infrastructure.rag.reranker import LLMReranker
from src.infrastructure.rag.retriever import HybridRetriever

router = APIRouter(prefix="/documents", tags=["documents"])

_MAX_UPLOAD_BYTES = 25 * 1024 * 1024  # 25 MB hard cap for v1
_UPLOAD_CHUNK = 1024 * 1024  # 1 MB read window
_TOO_LARGE = "File too large (25 MB max)"


def _to_summary(dto: DocumentDTO) -> DocumentSummary:
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


def _build_reranker(config: TenantConfig, usage_sink: LLMUsageSink) -> LLMReranker:
    """The same reranker the gateway wires in production — a cheap dedicated rerank
    model reusing the tenant's LLM provider + key — so the trace reflects what the
    agent actually retrieves, not an un-reranked approximation. The trace call is
    billable, so its usage is collected in the sink and recorded by the caller."""
    return LLMReranker(
        LangChainLLMClient(
            provider=config.llm_provider.value,
            model=config.rerank_model,
            api_key=config.llm_api_key,
        ),
        usage_sink=usage_sink,
    )


async def _capped_stream(file: UploadFile, cap: int) -> AsyncIterator[bytes]:
    """Yield the upload in chunks — never the whole file (or many concurrent files)
    in memory — and abort if it exceeds the cap, so the actual bytes are bounded even
    when the declared size lied."""
    total = 0
    while chunk := await file.read(_UPLOAD_CHUNK):
        total += len(chunk)
        if total > cap:
            raise HTTPException(status_code=413, detail=_TOO_LARGE)
        yield chunk


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Unsupported file type"}, 413: {"description": _TOO_LARGE}},
)
async def upload_document(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    job_pool: JobPoolDep,
    file: Annotated[UploadFile, File()],
) -> DocumentSummary:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")
    if file.size is not None and file.size > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=_TOO_LARGE)

    tenant_id = await resolve_tenant_id(current_user, uow)

    # Record the document first (rejects bad file types now and gives us the id used
    # for the storage path), then stream the raw bytes straight to durable storage —
    # constant memory regardless of file size or concurrent uploads.
    dto = await RegisterDocumentUseCase(uow=uow).execute(
        RegisterDocument(
            tenant_id=tenant_id,
            uploaded_by_user_id=current_user.id,
            filename=file.filename,
            size_bytes=file.size or 0,
        )
    )
    storage = document_storage()
    try:
        await storage.save(tenant_id=tenant_id, document_id=dto.id, chunks=_capped_stream(file, _MAX_UPLOAD_BYTES))
    except HTTPException:
        # Oversized despite the declared size: drop the half-written file and record
        # the document as failed so the owner sees why, then surface the error.
        await storage.delete(tenant_id=tenant_id, document_id=dto.id)
        doc = await uow.documents.get_by_id(dto.id)
        if doc is not None:
            doc.force_failed(reason=_TOO_LARGE)
            await uow.documents.save(doc)
            await uow.commit()
        raise

    # The heavy parse/chunk/embed work runs on the worker; the request returns now.
    await enqueue_document_ingestion(job_pool, tenant_id=tenant_id, document_id=dto.id, filename=file.filename)
    return _to_summary(dto)


@router.get("")
async def list_documents(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[DocumentSummary]:
    tenant_id = await resolve_tenant_id(current_user, uow)
    dtos = await ListDocumentsUseCase(uow=uow).execute(ListDocuments(tenant_id=tenant_id, limit=limit, offset=offset))
    return [_to_summary(d) for d in dtos]


@router.get("/processing")
async def list_processing_documents(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> list[DocumentSummary]:
    """In-flight uploads (uploaded or ingesting) for the global progress indicator.

    Lightweight by design: returns only the few documents still being ingested,
    so any page can poll it cheaply and a refresh re-derives progress from the DB.
    Documents stuck past the reaper window are excluded so the indicator stops
    polling them — the reaper reclaims them out of band.
    """
    tenant_id = await resolve_tenant_id(current_user, uow)
    cutoff = datetime.now(UTC) - timedelta(seconds=get_settings().ingestion_stale_after_seconds)
    dtos = await ListProcessingDocumentsUseCase(uow=uow).execute(
        ListProcessingDocuments(tenant_id=tenant_id, active_since=cutoff)
    )
    return [_to_summary(d) for d in dtos]


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> None:
    tenant_id = await resolve_tenant_id(current_user, uow)
    await DeleteDocumentUseCase(uow=uow).execute(tenant_id=tenant_id, document_id=document_id)
    await document_storage().delete(tenant_id=tenant_id, document_id=document_id)


@router.post("/retrieve")
async def retrieve(
    req: RetrieveRequest,
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
) -> RetrieveResponse:
    """Trace endpoint: run the *production* hybrid retriever (vector + BM25 + RRF +
    the same LLM reranker the agent uses) and return the matched chunks + scores.
    Useful for tuning the index and for the future "trace" UI."""
    tenant_id = await resolve_tenant_id(current_user, uow)
    config = await _load_tenant_config(tenant_id, uow)
    rerank_usage = LLMUsageSink()
    retriever = HybridRetriever(
        session=uow._session,
        embedder=_build_embedder(config),
        reranker=_build_reranker(config, rerank_usage),
    )
    dtos = await RetrieveForQueryUseCase(retriever=retriever).execute(
        RetrieveForQuery(tenant_id=tenant_id, query=req.query, top_k=req.top_k)
    )
    # The trace runs the real reranker (a billable LLM call) — record it like any
    # other so this debugging tool doesn't spend tokens off the books.
    record_uc = RecordTokenUsageUseCase(uow=uow)
    for call in rerank_usage.drain():
        await record_uc.execute(
            RecordTokenUsage(
                tenant_id=tenant_id,
                provider=call.provider or config.llm_provider.value,
                model=call.model or config.rerank_model,
                input_tokens=call.usage.input_tokens,
                output_tokens=call.usage.output_tokens,
                cache_read_tokens=call.usage.cache_read_tokens,
                source="reranker",
                channel="api",
            )
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
