"""Documents routes — upload, list, delete, retrieve."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, HTTPException, Query, UploadFile, status

from src.application.documents.commands import IngestDocument
from src.application.documents.queries import ListDocuments, RetrieveForQuery
from src.application.documents.use_cases.delete_document import DeleteDocumentUseCase
from src.application.documents.use_cases.ingest_document import IngestDocumentUseCase
from src.application.documents.use_cases.list_documents import ListDocumentsUseCase
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
from src.infrastructure.rag.chunker import RecursiveTokenChunker
from src.infrastructure.rag.embedder import OpenAIEmbedder
from src.infrastructure.rag.parser import DocumentParser
from src.infrastructure.rag.retriever import HybridRetriever

router = APIRouter(prefix="/documents", tags=["documents"])

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


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    responses={400: {"description": "Unsupported file type"}, 413: {"description": "File too large (25 MB max)"}},
)
async def upload_document(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    file: Annotated[UploadFile, File()],
) -> DocumentSummary:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required")

    content = await file.read()
    if len(content) > _MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large (25 MB max)")

    tenant_id = await resolve_tenant_id(current_user, uow)
    config = await _load_tenant_config(tenant_id, uow)

    use_case = IngestDocumentUseCase(
        uow=uow,
        parser=DocumentParser(),
        chunker=RecursiveTokenChunker(),
        embedder=_build_embedder(config),
    )
    dto = await use_case.execute(
        IngestDocument(
            tenant_id=tenant_id,
            uploaded_by_user_id=current_user.id,
            filename=file.filename,
            content=content,
        )
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
