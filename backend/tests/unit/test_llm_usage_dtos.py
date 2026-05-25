"""Unit tests for LLM usage DTOs + pricing edge cases."""

from __future__ import annotations

from decimal import Decimal

from src.application.llm_usage.dtos import UsageStatsDTO
from src.domain.llm_usage.pricing import ComputedCost, get_model_pricing
from src.domain.llm_usage.repositories import UsageStats


def test_usage_stats_dto_total() -> None:
    dto = UsageStatsDTO(
        total_input_tokens=100,
        total_output_tokens=50,
        total_cache_read_tokens=10,
        total_input_cost=Decimal("0.01"),
        total_cache_read_cost=Decimal("0.001"),
        total_output_cost=Decimal("0.03"),
        total_cost=Decimal("0.041"),
        total_calls=2,
    )
    assert dto.total_calls == 2


def test_usage_stats_total_cost() -> None:
    stats = UsageStats(
        total_input_tokens=100,
        total_output_tokens=50,
        total_cache_read_tokens=10,
        total_input_cost=Decimal("0.01"),
        total_cache_read_cost=Decimal("0.001"),
        total_output_cost=Decimal("0.03"),
        total_calls=1,
    )
    assert stats.total_cost == Decimal("0.041")


def test_computed_cost_total() -> None:
    c = ComputedCost(
        input_cost=Decimal("1.00"),
        cache_read_cost=Decimal("0.50"),
        output_cost=Decimal("2.00"),
    )
    assert c.total == Decimal("3.50")


def test_all_known_models_resolve() -> None:
    for model in [
        "gpt-4o",
        "gpt-4o-mini",
        "claude-opus-4-5",
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "gemini-2.0-flash",
    ]:
        assert get_model_pricing(model) is not None
