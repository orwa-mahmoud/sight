"""Unit tests for the tenant LLM client factory."""

from __future__ import annotations

from uuid import uuid4

from src.domain.tenant_config.entities import TenantConfig
from src.infrastructure.llm.tenant_factory import TenantLLMClientFactory


def _config(tenant_id=None):
    c = TenantConfig.create_default(tenant_id=tenant_id or uuid4())
    c.llm_api_key = "sk-test-12345678"
    return c


def test_builds_and_caches():
    factory = TenantLLMClientFactory()
    tid = uuid4()
    cfg = _config(tid)
    c1 = factory.get_or_build(tid, cfg)
    c2 = factory.get_or_build(tid, cfg)
    assert c1 is c2


def test_invalidate_removes_entry():
    factory = TenantLLMClientFactory()
    tid = uuid4()
    cfg = _config(tid)
    factory.get_or_build(tid, cfg)
    factory.invalidate(tid)
    c2 = factory.get_or_build(tid, cfg)
    assert c2 is not None


def test_ttl_expiry():
    factory = TenantLLMClientFactory(ttl=0)
    tid = uuid4()
    cfg = _config(tid)
    c1 = factory.get_or_build(tid, cfg)
    c2 = factory.get_or_build(tid, cfg)
    assert c1 is not c2


def test_max_size_evicts():
    factory = TenantLLMClientFactory(max_size=2)
    configs = [(uuid4(), _config()) for _ in range(3)]
    for tid, cfg in configs:
        cfg.llm_api_key = "sk-test-12345678"
        factory.get_or_build(tid, cfg)
    assert len(factory._cache) == 2


def test_clear():
    factory = TenantLLMClientFactory()
    factory.get_or_build(uuid4(), _config())
    factory.clear()
    assert len(factory._cache) == 0
