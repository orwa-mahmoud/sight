"""Tenant config value objects."""

from __future__ import annotations

from enum import StrEnum


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"
    # OpenAI-compatible providers — driven through the langchain-openai client pointed
    # at a vendor base URL (see infrastructure/llm/client.py), not a dedicated SDK.
    ZHIPU = "zhipu"  # Zhipu / GLM (Z.ai)
    DEEPSEEK = "deepseek"
