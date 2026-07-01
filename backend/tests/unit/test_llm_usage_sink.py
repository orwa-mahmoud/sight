"""Unit tests for LLMUsageSink."""

from __future__ import annotations

from src.domain.llm.usage_sink import LLMUsageSink
from src.domain.llm.value_objects import LLMCallResult, TokenUsage


def _result(*, input_tokens: int, output_tokens: int) -> LLMCallResult:
    return LLMCallResult(
        text="[0]",
        usage=TokenUsage(input_tokens=input_tokens, output_tokens=output_tokens),
        provider="openai",
        model="gpt-4o-mini",
    )


def test_add_and_drain_returns_calls_then_clears() -> None:
    sink = LLMUsageSink()
    sink.add(_result(input_tokens=120, output_tokens=30))

    drained = sink.drain()
    assert len(drained) == 1
    assert drained[0].usage.input_tokens == 120
    assert sink.drain() == []  # cleared after the first drain


def test_add_ignores_calls_with_no_tokens() -> None:
    sink = LLMUsageSink()
    sink.add(_result(input_tokens=0, output_tokens=0))
    assert sink.drain() == []
