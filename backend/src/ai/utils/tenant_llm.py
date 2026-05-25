"""Tenant LLM client builder."""

from __future__ import annotations

from src.domain.llm.ports import LLMClientPort
from src.domain.shared.exceptions import InvalidOperationError
from src.domain.tenant_config.entities import TenantConfig
from src.infrastructure.llm.client import LangChainLLMClient


def build_llm_client(config: TenantConfig) -> LLMClientPort:
    if not config.llm_api_key:
        raise InvalidOperationError("LLM API key not configured.")
    return LangChainLLMClient(
        provider=config.llm_provider.value,
        model=config.llm_model,
        api_key=config.llm_api_key,
    )
