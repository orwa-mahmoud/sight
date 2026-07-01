"""Per-model pricing table + cost calculator.

Prices are in USD per **1 million tokens**, current as of 2026-05. Adapted
from PropertyBot's pricing module with Sight's narrower model surface.
Cache pricing follows Anthropic's input cache semantics; OpenAI's prompt
caching is automatic on input tokens. The provider's `input_tokens` is the
TOTAL prompt count and `cache_read` is the cached SUBSET of it — so cached
tokens are billed once at the cheaper cache-read rate and only the remaining
`input_tokens - cache_read` at the full input rate (never both).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal


@dataclass(frozen=True, kw_only=True)
class ModelPricing:
    provider: str
    model: str
    input_per_million: Decimal
    cache_read_per_million: Decimal
    output_per_million: Decimal


# Per-million USD rates. Update as providers change list pricing.
_PRICING: dict[str, ModelPricing] = {
    # ── Anthropic ────────────────────────────────────────────────
    "claude-opus-4-5": ModelPricing(
        provider="anthropic",
        model="claude-opus-4-5",
        input_per_million=Decimal("15.00"),
        cache_read_per_million=Decimal("1.50"),
        output_per_million=Decimal("75.00"),
    ),
    "claude-sonnet-4-5": ModelPricing(
        provider="anthropic",
        model="claude-sonnet-4-5",
        input_per_million=Decimal("3.00"),
        cache_read_per_million=Decimal("0.30"),
        output_per_million=Decimal("15.00"),
    ),
    "claude-haiku-4-5": ModelPricing(
        provider="anthropic",
        model="claude-haiku-4-5",
        input_per_million=Decimal("1.00"),
        cache_read_per_million=Decimal("0.10"),
        output_per_million=Decimal("5.00"),
    ),
    # ── OpenAI ───────────────────────────────────────────────────
    "gpt-4o": ModelPricing(
        provider="openai",
        model="gpt-4o",
        input_per_million=Decimal("2.50"),
        cache_read_per_million=Decimal("1.25"),
        output_per_million=Decimal("10.00"),
    ),
    "gpt-4o-mini": ModelPricing(
        provider="openai",
        model="gpt-4o-mini",
        input_per_million=Decimal("0.15"),
        cache_read_per_million=Decimal("0.075"),
        output_per_million=Decimal("0.60"),
    ),
    # ── Google ───────────────────────────────────────────────────
    "gemini-2.0-flash": ModelPricing(
        provider="google",
        model="gemini-2.0-flash",
        input_per_million=Decimal("0.10"),
        cache_read_per_million=Decimal("0.025"),
        output_per_million=Decimal("0.40"),
    ),
    # ── Zhipu / GLM (OpenAI-compatible) ──────────────────────────
    # The two -flash models are free; the rest are per-million list prices.
    "glm-4.5-flash": ModelPricing(
        provider="zhipu",
        model="glm-4.5-flash",
        input_per_million=Decimal("0"),
        cache_read_per_million=Decimal("0"),
        output_per_million=Decimal("0"),
    ),
    "glm-4.7-flash": ModelPricing(
        provider="zhipu",
        model="glm-4.7-flash",
        input_per_million=Decimal("0"),
        cache_read_per_million=Decimal("0"),
        output_per_million=Decimal("0"),
    ),
    "glm-4.6": ModelPricing(
        provider="zhipu",
        model="glm-4.6",
        input_per_million=Decimal("0.60"),
        cache_read_per_million=Decimal("0.11"),
        output_per_million=Decimal("2.20"),
    ),
    "glm-4.5-air": ModelPricing(
        provider="zhipu",
        model="glm-4.5-air",
        input_per_million=Decimal("0.20"),
        cache_read_per_million=Decimal("0.03"),
        output_per_million=Decimal("1.10"),
    ),
    # ── DeepSeek (OpenAI-compatible) ─────────────────────────────
    "deepseek-chat": ModelPricing(
        provider="deepseek",
        model="deepseek-chat",
        input_per_million=Decimal("0.27"),
        cache_read_per_million=Decimal("0.07"),
        output_per_million=Decimal("1.10"),
    ),
    "deepseek-reasoner": ModelPricing(
        provider="deepseek",
        model="deepseek-reasoner",
        input_per_million=Decimal("0.55"),
        cache_read_per_million=Decimal("0.14"),
        output_per_million=Decimal("2.19"),
    ),
}


def get_model_pricing(model: str) -> ModelPricing | None:
    return _PRICING.get(model)


@dataclass(frozen=True, kw_only=True)
class ComputedCost:
    """Breakdown of one call's cost in USD."""

    input_cost: Decimal
    cache_read_cost: Decimal
    output_cost: Decimal

    @property
    def total(self) -> Decimal:
        return self.input_cost + self.cache_read_cost + self.output_cost


def calculate_cost(
    *,
    model: str,
    input_tokens: int,
    cache_read_tokens: int,
    output_tokens: int,
) -> ComputedCost:
    """Compute USD cost for a single LLM call.

    Unknown models cost 0 — RecordTokenUsageUseCase logs a warning so the gap is
    visible (the domain stays pure and cannot log).
    """
    pricing = get_model_pricing(model)
    if pricing is None:
        zero = Decimal("0")
        return ComputedCost(input_cost=zero, cache_read_cost=zero, output_cost=zero)

    one_million = Decimal("1000000")

    def _round(amount: Decimal) -> Decimal:
        # Round to 8 decimal places — sub-cent precision keeps long-running aggregates accurate.
        return amount.quantize(Decimal("0.00000001"), rounding=ROUND_HALF_UP)

    # `input_tokens` is the provider's TOTAL prompt count (cached + uncached); the
    # cached portion is billed at the cheaper cache-read rate, so only the remainder
    # is charged at the full input rate — otherwise cached tokens are billed twice.
    non_cached_input = max(0, input_tokens - cache_read_tokens)
    return ComputedCost(
        input_cost=_round(Decimal(non_cached_input) * pricing.input_per_million / one_million),
        cache_read_cost=_round(Decimal(cache_read_tokens) * pricing.cache_read_per_million / one_million),
        output_cost=_round(Decimal(output_tokens) * pricing.output_per_million / one_million),
    )
