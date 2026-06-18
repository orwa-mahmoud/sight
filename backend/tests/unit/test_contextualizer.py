"""Unit tests for Contextual Retrieval: the contextualizer and the ingest hook."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.documents.use_cases.ingest_document import IngestDocumentUseCase
from src.domain.rag.ports import ContextualizerPort
from src.domain.rag.value_objects import TextChunk
from src.infrastructure.rag.contextualizer import LLMContextualizer


def _llm(text: str) -> MagicMock:
    llm = MagicMock()
    llm.chat_with_tools = AsyncMock(return_value=MagicMock(text=text))
    return llm


def _use_case(contextualizer: ContextualizerPort | None = None) -> IngestDocumentUseCase:
    return IngestDocumentUseCase(
        uow=MagicMock(),
        parser=MagicMock(),
        chunker=MagicMock(),
        embedder=MagicMock(),
        contextualizer=contextualizer,
    )


# ── LLMContextualizer ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_contextualizer_returns_stripped_context() -> None:
    out = await LLMContextualizer(_llm("  This section covers refunds.  ")).contextualize(document="doc", chunk="chunk")
    assert out == "This section covers refunds."


@pytest.mark.asyncio
async def test_contextualizer_returns_empty_on_error() -> None:
    llm = MagicMock()
    llm.chat_with_tools = AsyncMock(side_effect=RuntimeError("boom"))
    out = await LLMContextualizer(llm).contextualize(document="d", chunk="c")
    assert out == ""


# ── ingest: contextualized embed inputs ───────────────────────────


@pytest.mark.asyncio
async def test_ingest_prepends_context_before_embedding() -> None:
    ctx = MagicMock()
    ctx.contextualize = AsyncMock(return_value="CTX")
    chunks = [TextChunk(index=0, content="alpha"), TextChunk(index=1, content="beta")]
    out = await _use_case(ctx)._contextualized_inputs("document", chunks)
    assert out == ["CTX\n\nalpha", "CTX\n\nbeta"]


@pytest.mark.asyncio
async def test_ingest_without_contextualizer_embeds_raw() -> None:
    chunks = [TextChunk(index=0, content="alpha")]
    out = await _use_case()._contextualized_inputs("document", chunks)
    assert out == ["alpha"]


@pytest.mark.asyncio
async def test_ingest_falls_back_to_raw_when_context_empty() -> None:
    ctx = MagicMock()
    ctx.contextualize = AsyncMock(return_value="")  # contextualizer produced nothing
    chunks = [TextChunk(index=0, content="alpha")]
    out = await _use_case(ctx)._contextualized_inputs("document", chunks)
    assert out == ["alpha"]
