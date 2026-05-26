"""Unit tests for TenantConfig entity methods."""

from __future__ import annotations

from uuid import uuid4

from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenant_config.value_objects import LLMProvider


def test_update_embedding() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.update_embedding(provider="voyage", model="voyage-3")
    assert c.embedding_provider == "voyage"
    assert c.embedding_model == "voyage-3"


def test_update_telegram() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.update_telegram(bot_token="123:ABC", webhook_secret="secret")
    assert c.telegram_bot_token == "123:ABC"
    assert c.telegram_webhook_secret == "secret"


def test_mask_key_edge_cases() -> None:
    assert TenantConfig.mask_key("12345678") == "****5678"
    assert TenantConfig.mask_key("1234567") == "****"
    assert TenantConfig.mask_key("a") == "****"


def test_llm_provider_values() -> None:
    assert LLMProvider.OPENAI.value == "openai"
    assert LLMProvider.ANTHROPIC.value == "anthropic"
    assert LLMProvider.AZURE_OPENAI.value == "azure_openai"
    assert LLMProvider.GOOGLE.value == "google"


def test_update_llm_partial() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    old_model = c.llm_model
    c.update_llm(api_key="new-key")
    assert c.llm_api_key == "new-key"
    assert c.llm_model == old_model  # unchanged
