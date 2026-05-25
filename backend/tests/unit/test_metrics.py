"""Unit tests for Prometheus metric definitions."""

from __future__ import annotations

from src.infrastructure.metrics import (
    AGENT_DURATION,
    AGENT_INVOCATIONS_TOTAL,
    AGENT_TOOL_CALLS_TOTAL,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS_TOTAL,
    LLM_CALLS_TOTAL,
    LLM_TOKENS_TOTAL,
    QUESTIONS_RESOLVED_TOTAL,
    QUESTIONS_SUBMITTED_TOTAL,
    RAG_RETRIEVALS_TOTAL,
)


def test_all_metrics_importable() -> None:
    """Verify all 10 metrics are importable."""
    metrics = [
        HTTP_REQUESTS_TOTAL,
        HTTP_REQUEST_DURATION,
        LLM_CALLS_TOTAL,
        LLM_TOKENS_TOTAL,
        AGENT_INVOCATIONS_TOTAL,
        AGENT_TOOL_CALLS_TOTAL,
        AGENT_DURATION,
        RAG_RETRIEVALS_TOTAL,
        QUESTIONS_SUBMITTED_TOTAL,
        QUESTIONS_RESOLVED_TOTAL,
    ]
    assert len(metrics) == 10
    for m in metrics:
        assert m._name  # noqa: SLF001


def test_counter_can_increment() -> None:
    LLM_CALLS_TOTAL.labels(provider="openai", model="gpt-4o-mini", status="success").inc()
    LLM_TOKENS_TOTAL.labels(provider="openai", model="gpt-4o-mini", direction="input").inc(100)
