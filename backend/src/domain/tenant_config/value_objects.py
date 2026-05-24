"""Tenant config value objects."""

from __future__ import annotations

from enum import StrEnum


class LLMProvider(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    AZURE_OPENAI = "azure_openai"
    GOOGLE = "google"
