"""Unit tests for key facts context loader."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.ai.context.memory import load_key_facts_context
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.contacts.entities import Contact
from src.domain.key_facts.entities import KeyFact
from src.domain.tenants.entities import Tenant
from src.infrastructure.persistence.postgres.database import async_session_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_load_key_facts_empty(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="Mem", slug=f"mem-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        c = Contact.create(tenant_id=t.id, phone="+971500000000")
        await uow.contacts.save(c)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        result = await load_key_facts_context(
            tenant_id=t.id,
            contact_id=c.id,
            uow=uow,
        )
        assert result == ""


@pytest.mark.integration
@pytest.mark.asyncio
async def test_load_key_facts_with_data(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="Mem2", slug=f"mem2-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        c = Contact.create(tenant_id=t.id, phone="+971500000001")
        await uow.contacts.save(c)
        await uow.flush()
        for k, v in [("name", "Sara"), ("language", "Arabic")]:
            f = KeyFact.create(tenant_id=t.id, contact_id=c.id, key=k, value=v)
            await uow.key_facts.save(f)
        await uow.commit()

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        result = await load_key_facts_context(
            tenant_id=t.id,
            contact_id=c.id,
            uow=uow,
        )
        assert "Sara" in result
        assert "Arabic" in result
        assert "Known facts" in result
