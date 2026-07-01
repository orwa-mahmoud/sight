"""LLM-based reranker for the RAG pipeline.

`LLMReranker` asks the tenant's own LLM to order the candidate chunks by
relevance and keeps the best top-k. It falls back to the input order on any
failure and never drops a candidate the model omits, so it can only improve the
hybrid ranking, never degrade below it.

A reranker is the highest-ROI query-side quality lever: the right chunk is
usually retrieved but ranked just below the cutoff, and reranking promotes it.
When no reranker is configured the retriever simply keeps the hybrid order.
"""

from __future__ import annotations

import re

import structlog

from src.domain.llm.ports import LLMClientPort
from src.domain.llm.usage_sink import LLMUsageSink
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole
from src.domain.rag.value_objects import RetrievedChunk

logger = structlog.get_logger()

_SNIPPET_CHARS = 400
_RERANK_MAX_TOKENS = 200


class LLMReranker:
    """Reorders candidate chunks by LLM-judged relevance to the query.

    One bounded LLM call over the candidate pool. Robust by construction: if the
    model errors or returns nothing parseable, the original hybrid order is kept,
    and any candidate the model omits is appended rather than dropped.
    """

    def __init__(self, llm: LLMClientPort, *, usage_sink: LLMUsageSink | None = None) -> None:
        self._llm = llm
        self._usage_sink = usage_sink

    async def rerank(self, query: str, chunks: list[RetrievedChunk], *, top_k: int = 8) -> list[RetrievedChunk]:
        # Nothing to gain when we'd keep everything anyway — skip the call.
        if len(chunks) <= top_k:
            return chunks[:top_k]

        listing = "\n".join(f"[{i}] {c.content[:_SNIPPET_CHARS]}" for i, c in enumerate(chunks))
        messages = [
            LLMMessage(
                role=LLMMessageRole.SYSTEM,
                content=(
                    "You rank passages by how well they help answer a query. "
                    "Reply with ONLY a JSON array of passage indices, most relevant first."
                ),
            ),
            LLMMessage(
                role=LLMMessageRole.USER,
                content=(
                    f"Query: {query}\n\nPassages:\n{listing}\n\n"
                    f"Return the {top_k} most relevant indices as a JSON array, e.g. [3, 0, 7]."
                ),
            ),
        ]

        try:
            result = await self._llm.chat_with_tools(messages, max_tokens=_RERANK_MAX_TOKENS, temperature=0.0)
        except Exception:
            logger.warning("reranker.llm_failed", exc_info=True)
            return chunks[:top_k]

        # The rerank call is billable — hand its usage to the sink so the turn's
        # orchestrator records it. Done before parsing so it counts even when the
        # reply is unparseable and we fall back to the hybrid order.
        if self._usage_sink is not None:
            self._usage_sink.add(result)

        order = _parse_indices(result.text, count=len(chunks))

        if not order:
            return chunks[:top_k]

        ranked = [chunks[i] for i in order]
        seen = set(order)
        # Never drop a candidate the model didn't mention — append it after.
        ranked.extend(c for i, c in enumerate(chunks) if i not in seen)
        return ranked[:top_k]


def _parse_indices(text: str, *, count: int) -> list[int]:
    """Extract a de-duplicated list of valid chunk indices from the model's reply."""
    seen: set[int] = set()
    order: list[int] = []
    for match in re.findall(r"\d+", text):
        idx = int(match)
        if 0 <= idx < count and idx not in seen:
            seen.add(idx)
            order.append(idx)
    return order
