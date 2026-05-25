"""Unit tests for tenant LLM builder."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.ai.utils.tenant_llm import build_llm_client
from src.domain.shared.exceptions import InvalidOperationError
from src.domain.tenant_config.entities import TenantConfig


def test_build_with_key() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.llm_api_key = "sk-test-key-12345678"
    assert build_llm_client(c) is not None


def test_build_empty_key_raises() -> None:
    c = TenantConfig.create_default(tenant_id=uuid4())
    c.llm_api_key = ""
    with pytest.raises(InvalidOperationError):
        build_llm_client(c)
