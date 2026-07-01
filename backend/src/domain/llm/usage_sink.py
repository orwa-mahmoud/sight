"""Collector for auxiliary LLM-call usage.

The agent-loop reply is the obvious billable call, but a turn also spends tokens
on side calls — the RAG reranker today, potentially others later — that happen
deep inside infrastructure adapters. Those adapters cannot import the application
layer to record usage themselves, so they append the raw call result to this
sink instead. The ai layer, which orchestrates the turn, drains the sink after
the agent loop and persists each call via RecordTokenUsageUseCase.
"""

from __future__ import annotations

from src.domain.llm.value_objects import LLMCallResult


class LLMUsageSink:
    """Accumulates usage from non-agent-loop LLM calls within a single turn."""

    def __init__(self) -> None:
        self._calls: list[LLMCallResult] = []

    def add(self, result: LLMCallResult) -> None:
        """Record a call. No-ops for calls that reported no tokens (e.g. a
        provider that omitted usage metadata), so drained calls are always
        worth persisting."""
        usage = result.usage
        if usage.input_tokens <= 0 and usage.output_tokens <= 0:
            return
        self._calls.append(result)

    def drain(self) -> list[LLMCallResult]:
        """Return and clear the accumulated calls."""
        calls = self._calls
        self._calls = []
        return calls
