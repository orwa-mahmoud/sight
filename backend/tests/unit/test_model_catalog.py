"""Unit tests for the LLM model catalog."""

from __future__ import annotations

from src.domain.tenant_config.model_catalog import (
    MAX_COMPLETION_TOKENS,
    MAX_TOKENS,
    MODEL_CATALOG,
    PROVIDER_LABELS,
    get_model_spec,
)
from src.domain.tenant_config.value_objects import LLMProvider


def test_get_model_spec_known_model() -> None:
    spec = get_model_spec("gpt-4o-mini")
    assert spec is not None
    assert spec.provider == LLMProvider.OPENAI
    assert spec.token_param == MAX_TOKENS
    assert spec.supports_temperature is True


def test_reasoning_model_uses_max_completion_tokens() -> None:
    spec = get_model_spec("gpt-5.4-nano")
    assert spec is not None
    assert spec.token_param == MAX_COMPLETION_TOKENS


def test_unknown_model_returns_none() -> None:
    assert get_model_spec("not-a-real-model") is None


def test_every_catalog_provider_has_a_label() -> None:
    for spec in MODEL_CATALOG:
        assert spec.provider in PROVIDER_LABELS


def test_glm_and_deepseek_present() -> None:
    models = {spec.model for spec in MODEL_CATALOG}
    assert {"glm-4.5-flash", "glm-4.7-flash", "deepseek-chat"} <= models
