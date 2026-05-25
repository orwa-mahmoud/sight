"""Unit tests for TokenUsage entity edge cases."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from src.domain.llm_usage.entities import TokenUsage


def test_record_with_cache_tokens() -> None:
    u = TokenUsage.record(
        tenant_id=uuid4(),
        provider="anthropic",
        model="claude-sonnet-4-5",
        input_tokens=1000,
        output_tokens=500,
        cache_read_tokens=200,
    )
    assert u.cache_read_tokens == 200
    assert u.total_cost > 0
    assert u.is_new
    assert len(u.pending_events) == 1


def test_record_unknown_model_zero_cost() -> None:
    u = TokenUsage.record(
        tenant_id=uuid4(),
        provider="custom",
        model="unknown-model",
        input_tokens=1000,
        output_tokens=500,
    )
    assert u.total_cost == Decimal("0")


def test_record_with_thread_and_request() -> None:
    u = TokenUsage.record(
        tenant_id=uuid4(),
        provider="openai",
        model="gpt-4o",
        input_tokens=100,
        output_tokens=50,
        thread_id="t1",
        request_id="r1",
        source="owner",
        channel="web",
    )
    assert u.thread_id == "t1"
    assert u.request_id == "r1"
    assert u.source == "owner"
    assert u.channel == "web"
