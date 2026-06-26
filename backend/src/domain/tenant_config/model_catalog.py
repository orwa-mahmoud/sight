"""Catalog of selectable LLM models per provider.

Single source of truth for two things that would otherwise drift apart:

1. The provider/model options the frontend offers (returned by GET /settings/models).
2. The per-model API quirks the LLM client must honor — chiefly whether the model
   takes ``max_tokens`` or ``max_completion_tokens`` (reasoning models reject the
   former), and whether it accepts a non-default temperature.

Adding a model is one entry here — no change to the client, routes, or frontend.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.domain.tenant_config.value_objects import LLMProvider

# Token-limit parameter names. Reasoning models (o-series, gpt-5.x) reject the
# legacy ``max_tokens`` and require ``max_completion_tokens``.
MAX_TOKENS = "max_tokens"
MAX_COMPLETION_TOKENS = "max_completion_tokens"


@dataclass(frozen=True, kw_only=True)
class ModelSpec:
    provider: LLMProvider
    model: str
    label: str
    token_param: str = MAX_TOKENS
    supports_temperature: bool = True


# Human-readable provider names for the settings dropdown.
PROVIDER_LABELS: dict[LLMProvider, str] = {
    LLMProvider.OPENAI: "OpenAI",
    LLMProvider.ANTHROPIC: "Anthropic",
    LLMProvider.AZURE_OPENAI: "Azure OpenAI",
    LLMProvider.GOOGLE: "Google",
    LLMProvider.ZHIPU: "Zhipu / GLM",
    LLMProvider.DEEPSEEK: "DeepSeek",
}


MODEL_CATALOG: tuple[ModelSpec, ...] = (
    # ── OpenAI ───────────────────────────────────────────────────
    ModelSpec(provider=LLMProvider.OPENAI, model="gpt-4o-mini", label="GPT-4o mini"),
    ModelSpec(provider=LLMProvider.OPENAI, model="gpt-4o", label="GPT-4o"),
    ModelSpec(
        provider=LLMProvider.OPENAI,
        model="gpt-5.4-nano",
        label="GPT-5.4 nano",
        token_param=MAX_COMPLETION_TOKENS,
    ),
    # ── Anthropic ────────────────────────────────────────────────
    ModelSpec(provider=LLMProvider.ANTHROPIC, model="claude-haiku-4-5", label="Claude Haiku 4.5"),
    ModelSpec(provider=LLMProvider.ANTHROPIC, model="claude-sonnet-4-5", label="Claude Sonnet 4.5"),
    # ── Google ───────────────────────────────────────────────────
    ModelSpec(provider=LLMProvider.GOOGLE, model="gemini-2.0-flash", label="Gemini 2.0 Flash"),
    # ── Zhipu / GLM (OpenAI-compatible) ──────────────────────────
    ModelSpec(provider=LLMProvider.ZHIPU, model="glm-4.5-flash", label="GLM-4.5 Flash (free)"),
    ModelSpec(provider=LLMProvider.ZHIPU, model="glm-4.7-flash", label="GLM-4.7 Flash (free)"),
    ModelSpec(provider=LLMProvider.ZHIPU, model="glm-4.6", label="GLM-4.6"),
    ModelSpec(provider=LLMProvider.ZHIPU, model="glm-4.5-air", label="GLM-4.5 Air"),
    # ── DeepSeek (OpenAI-compatible) ─────────────────────────────
    ModelSpec(provider=LLMProvider.DEEPSEEK, model="deepseek-chat", label="DeepSeek Chat"),
    ModelSpec(provider=LLMProvider.DEEPSEEK, model="deepseek-reasoner", label="DeepSeek Reasoner"),
)

_BY_MODEL: dict[str, ModelSpec] = {spec.model: spec for spec in MODEL_CATALOG}


def get_model_spec(model: str) -> ModelSpec | None:
    """The spec for a model id, or None if it is not in the catalog (caller falls
    back to legacy defaults — ``max_tokens`` + temperature)."""
    return _BY_MODEL.get(model)
