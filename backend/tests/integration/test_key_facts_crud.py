"""Integration tests for key facts CRUD."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.contacts.entities import Contact
from src.domain.key_facts.entities import KeyFact
from src.domain.tenants.entities import Tenant
from src.infrastructure.persistence.postgres.database import async_session_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_key_fact_save_get_list(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="KF", slug=f"kf-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        c = Contact.create(tenant_id=t.id, phone="+971500000000")
        await uow.contacts.save(c)
        await uow.flush()
        for k, v in [("name", "Sara"), ("language", "Arabic")]:
            f = KeyFact.create(tenant_id=t.id, contact_id=c.id, key=k, value=v)
            await uow.key_facts.save(f)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.key_facts.get(t.id, c.id, "name")
        assert loaded is not None
        assert loaded.value == "Sara"
        facts = await uow.key_facts.list_for_contact(t.id, c.id)
        assert len(facts) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_key_fact_update_and_delete(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="KF2", slug=f"kf2-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        c = Contact.create(tenant_id=t.id, phone="+971500000001")
        await uow.contacts.save(c)
        await uow.flush()
        fact = KeyFact.create(tenant_id=t.id, contact_id=c.id, key="name", value="Sara")
        await uow.key_facts.save(fact)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        loaded = await uow.key_facts.get(t.id, c.id, "name")
        assert loaded is not None
        loaded.update_value("Sarah")
        await uow.key_facts.save(loaded)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        reloaded = await uow.key_facts.get(t.id, c.id, "name")
        assert reloaded is not None
        assert reloaded.value == "Sarah"
        await uow.key_facts.delete(reloaded.id)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        assert await uow.key_facts.get(t.id, c.id, "name") is None
