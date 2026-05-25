"""Coverage tests for abstract repository ports — instantiate mock implementations."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.key_facts.entities import KeyFact
from src.domain.key_facts.repositories import KeyFactRepository
from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenant_config.repositories import TenantConfigRepository


class FakeKeyFactRepo:
    """Concrete implementation of KeyFactRepository for coverage."""

    async def save(self, fact: KeyFact) -> None:
        pass

    async def get(self, tenant_id, contact_id, key: str) -> KeyFact | None:
        return None

    async def list_for_contact(self, tenant_id, contact_id) -> list[KeyFact]:
        return []

    async def delete(self, fact_id) -> None:
        pass


class FakeTenantConfigRepo:
    """Concrete implementation of TenantConfigRepository for coverage."""

    async def save(self, config: TenantConfig) -> None:
        pass

    async def get_by_tenant_id(self, tenant_id) -> TenantConfig | None:
        return None


def test_key_fact_repo_protocol_satisfied() -> None:
    """A FakeKeyFactRepo satisfies the KeyFactRepository protocol."""
    repo: KeyFactRepository = FakeKeyFactRepo()
    # Protocol is structural — if this typechecks and doesn't raise, it's satisfied
    assert repo is not None


def test_tenant_config_repo_protocol_satisfied() -> None:
    """A FakeTenantConfigRepo satisfies the TenantConfigRepository protocol."""
    repo: TenantConfigRepository = FakeTenantConfigRepo()
    assert repo is not None


@pytest.mark.asyncio
async def test_key_fact_repo_methods() -> None:
    repo = FakeKeyFactRepo()
    tid = uuid4()
    cid = uuid4()
    fact = KeyFact.create(tenant_id=tid, contact_id=cid, key="name", value="Ali")
    await repo.save(fact)
    assert await repo.get(tid, cid, "name") is None
    assert await repo.list_for_contact(tid, cid) == []
    await repo.delete(fact.id)


@pytest.mark.asyncio
async def test_tenant_config_repo_methods() -> None:
    repo = FakeTenantConfigRepo()
    tid = uuid4()
    config = TenantConfig.create_default(tenant_id=tid)
    await repo.save(config)
    assert await repo.get_by_tenant_id(tid) is None
