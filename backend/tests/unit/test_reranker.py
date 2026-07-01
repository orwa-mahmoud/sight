"""Unit tests for the LLM reranker and lost-in-the-middle reordering."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.domain.llm.usage_sink import LLMUsageSink
from src.domain.llm.value_objects import LLMCallResult, TokenUsage
from src.domain.rag.value_objects import RetrievedChunk
from src.infrastructure.rag.reranker import LLMReranker, _parse_indices
from src.infrastructure.rag.retriever import reorder_lost_in_the_middle


def _chunk(content: str, score: float = 1.0) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid4(),
        document_id=uuid4(),
        tenant_id=uuid4(),
        content=content,
        score=score,
        extra_metadata={},
    )


def _llm(text: str) -> MagicMock:
    llm = MagicMock()
    llm.chat_with_tools = AsyncMock(return_value=MagicMock(text=text))
    return llm


# ── reorder_lost_in_the_middle ────────────────────────────────────


def test_reorder_keeps_strongest_at_edges() -> None:
    chunks = [_chunk(f"c{i}") for i in range(8)]
    out = reorder_lost_in_the_middle(chunks)
    assert out[0].content == "c0"  # best stays first
    assert out[-1].content == "c1"  # second-best moves to the end
    assert {c.content for c in out} == {f"c{i}" for i in range(8)}  # same set, no loss


def test_reorder_is_noop_for_small_lists() -> None:
    pair = [_chunk("a"), _chunk("b")]
    assert reorder_lost_in_the_middle(pair) == pair
    assert reorder_lost_in_the_middle([]) == []


# ── LLMReranker ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reranker_orders_by_model_output() -> None:
    chunks = [_chunk(f"c{i}") for i in range(6)]
    out = await LLMReranker(_llm("[4, 1, 0]")).rerank("q", chunks, top_k=3)
    assert [c.content for c in out] == ["c4", "c1", "c0"]


@pytest.mark.asyncio
async def test_reranker_skips_llm_when_candidates_fit() -> None:
    chunks = [_chunk("a"), _chunk("b")]
    llm = MagicMock()
    llm.chat_with_tools = AsyncMock()
    out = await LLMReranker(llm).rerank("q", chunks, top_k=3)
    assert out == chunks
    llm.chat_with_tools.assert_not_called()


@pytest.mark.asyncio
async def test_reranker_falls_back_to_input_order_on_error() -> None:
    chunks = [_chunk(f"c{i}") for i in range(6)]
    llm = MagicMock()
    llm.chat_with_tools = AsyncMock(side_effect=RuntimeError("boom"))
    out = await LLMReranker(llm).rerank("q", chunks, top_k=3)
    assert [c.content for c in out] == ["c0", "c1", "c2"]


@pytest.mark.asyncio
async def test_reranker_never_drops_omitted_candidates() -> None:
    chunks = [_chunk(f"c{i}") for i in range(6)]
    out = await LLMReranker(_llm("[5]")).rerank("q", chunks, top_k=3)
    assert out[0].content == "c5"  # the model's pick leads
    assert len(out) == 3  # rest backfilled from hybrid order — nothing lost


@pytest.mark.asyncio
async def test_reranker_falls_back_on_unparseable_reply() -> None:
    chunks = [_chunk(f"c{i}") for i in range(6)]
    out = await LLMReranker(_llm("no numbers here")).rerank("q", chunks, top_k=3)
    assert [c.content for c in out] == ["c0", "c1", "c2"]


def test_parse_indices_dedupes_and_bounds() -> None:
    assert _parse_indices("[2, 0, 2, 9, 1]", count=3) == [2, 0, 1]  # drops 9 (out of range) + dup 2
    assert _parse_indices("garbage", count=5) == []


# ── usage sink (per-search billing) ───────────────────────────────


def _llm_with_usage(text: str, *, input_tokens: int, output_tokens: int) -> MagicMock:
    llm = MagicMock()
    llm.chat_with_tools = AsyncMock(
        return_value=LLMCallResult(
            text=text,
            usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
            provider="openai",
            model="gpt-5.4-mini",
        )
    )
    return llm


@pytest.mark.asyncio
async def test_reranker_records_usage_into_sink() -> None:
    chunks = [_chunk(f"c{i}") for i in range(6)]
    sink = LLMUsageSink()
    llm = _llm_with_usage("[4, 1, 0]", input_tokens=320, output_tokens=40)

    await LLMReranker(llm, usage_sink=sink).rerank("q", chunks, top_k=3)

    drained = sink.drain()
    assert len(drained) == 1
    assert drained[0].usage.input_tokens == 320
    assert drained[0].model == "gpt-5.4-mini"


@pytest.mark.asyncio
async def test_reranker_records_usage_even_when_reply_unparseable() -> None:
    chunks = [_chunk(f"c{i}") for i in range(6)]
    sink = LLMUsageSink()
    llm = _llm_with_usage("no numbers", input_tokens=300, output_tokens=5)

    out = await LLMReranker(llm, usage_sink=sink).rerank("q", chunks, top_k=3)

    assert [c.content for c in out] == ["c0", "c1", "c2"]  # fell back to hybrid order
    assert len(sink.drain()) == 1  # but the billable call was still recorded


@pytest.mark.asyncio
async def test_reranker_records_nothing_when_llm_skipped() -> None:
    chunks = [_chunk("a"), _chunk("b")]
    sink = LLMUsageSink()
    await LLMReranker(_llm_with_usage("[0]", input_tokens=1, output_tokens=1), usage_sink=sink).rerank(
        "q", chunks, top_k=3
    )
    assert sink.drain() == []  # candidates fit → no call → no usage
