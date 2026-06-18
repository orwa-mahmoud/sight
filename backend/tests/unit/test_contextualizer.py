"""Unit tests for Contextual Retrieval: the contextualizer and the ingest hook."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.documents.use_cases.process_document import ProcessDocumentUseCase
from src.domain.rag.ports import ContextualizerPort
from src.domain.rag.value_objects import TextChunk
from src.infrastructure.rag.contextualizer import LLMContextualizer


def _llm(text: str) -> MagicMock:
    llm = MagicMock()
    llm.chat_with_tools = AsyncMock(return_value=MagicMock(text=text))
    return llm


def _use_case(contextualizer: ContextualizerPort | None = None) -> ProcessDocumentUseCase:
    return ProcessDocumentUseCase(
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


def _chunks(*contents: str) -> list[TextChunk]:
    return [TextChunk(index=i, content=c) for i, c in enumerate(contents)]


@pytest.mark.asyncio
async def test_ingest_prepends_context_before_embedding() -> None:
    ctx = MagicMock()
    ctx.contextualize = AsyncMock(return_value="CTX")
    out = await _use_case(ctx)._contextualized_inputs("document", _chunks("a", "b", "c"))
    assert out == ["CTX\n\na", "CTX\n\nb", "CTX\n\nc"]


@pytest.mark.asyncio
async def test_ingest_skips_context_for_tiny_documents() -> None:
    ctx = MagicMock()
    ctx.contextualize = AsyncMock(return_value="CTX")
    # Below the chunk threshold the contextualizer is never called — no LLM cost.
    out = await _use_case(ctx)._contextualized_inputs("document", _chunks("alpha", "beta"))
    assert out == ["alpha", "beta"]
    ctx.contextualize.assert_not_called()


@pytest.mark.asyncio
async def test_ingest_without_contextualizer_embeds_raw() -> None:
    out = await _use_case()._contextualized_inputs("document", _chunks("a", "b", "c"))
    assert out == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_ingest_falls_back_to_raw_when_context_empty() -> None:
    ctx = MagicMock()
    ctx.contextualize = AsyncMock(return_value="")  # contextualizer produced nothing
    out = await _use_case(ctx)._contextualized_inputs("document", _chunks("a", "b", "c"))
    assert out == ["a", "b", "c"]
