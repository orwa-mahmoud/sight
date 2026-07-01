"""Unit tests for the pricing module — pure math, no IO."""

from __future__ import annotations

from decimal import Decimal

from src.domain.llm_usage.pricing import calculate_cost, get_model_pricing


def test_known_model_resolves() -> None:
    pricing = get_model_pricing("gpt-4o-mini")
    assert pricing is not None
    assert pricing.provider == "openai"


def test_unknown_model_costs_zero() -> None:
    cost = calculate_cost(model="nonexistent-model", input_tokens=1000, cache_read_tokens=0, output_tokens=500)
    assert cost.total == Decimal("0")


def test_gpt_4o_mini_cost_math() -> None:
    # $0.15 per 1M input, $0.60 per 1M output. 100k in + 50k out:
    # input = 0.15 * 0.1 = 0.015 ; output = 0.60 * 0.05 = 0.03 ; total = 0.045
    cost = calculate_cost(
        model="gpt-4o-mini",
        input_tokens=100_000,
        cache_read_tokens=0,
        output_tokens=50_000,
    )
    assert cost.input_cost == Decimal("0.01500000")
    assert cost.output_cost == Decimal("0.03000000")
    assert cost.total == Decimal("0.04500000")


def test_anthropic_cache_read_is_cheaper() -> None:
    pricing = get_model_pricing("claude-sonnet-4-5")
    assert pricing is not None
    assert pricing.cache_read_per_million < pricing.input_per_million


def test_cache_read_is_a_subset_of_input_not_double_billed() -> None:
    # input_tokens is the TOTAL prompt (cached + uncached); cache_read is the cached
    # subset. Only the uncached remainder is billed at the full input rate.
    cost = calculate_cost(
        model="claude-sonnet-4-5",
        input_tokens=1_000_000,  # total prompt tokens
        cache_read_tokens=400_000,  # of which 400k were cache hits
        output_tokens=1_000_000,
    )
    # non-cached input 600k @ $3/M = 1.80 ; cache 400k @ $0.30/M = 0.12 ; output 15.00
    assert cost.input_cost == Decimal("1.80000000")
    assert cost.cache_read_cost == Decimal("0.12000000")
    assert cost.output_cost == Decimal("15.00000000")
    assert cost.total == Decimal("16.92000000")


def test_fully_cached_prompt_bills_no_full_rate_input() -> None:
    # Every input token was a cache hit → nothing charged at the full input rate.
    cost = calculate_cost(
        model="claude-sonnet-4-5",
        input_tokens=500_000,
        cache_read_tokens=500_000,
        output_tokens=0,
    )
    assert cost.input_cost == Decimal("0")  # not double-billed
    assert cost.cache_read_cost == Decimal("0.15000000")  # 500k @ $0.30/M
    assert cost.total == Decimal("0.15000000")
