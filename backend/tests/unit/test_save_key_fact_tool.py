"""Unit tests for save_key_fact + remove_key_fact tools."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.ai.tools.remove_key_fact import REMOVE_KEY_FACT_DEF, run_remove_key_fact
from src.ai.tools.save_key_fact import SAVE_KEY_FACT_DEF, run_save_key_fact
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.contacts.entities import Contact
from src.domain.key_facts.entities import KeyFact
from src.domain.tenants.entities import Tenant
from src.infrastructure.persistence.postgres.database import async_session_factory


def test_save_key_fact_def_shape() -> None:
    assert SAVE_KEY_FACT_DEF.name == "save_key_fact"
    assert "key" in SAVE_KEY_FACT_DEF.parameters_schema["properties"]


def test_remove_key_fact_def_shape() -> None:
    assert REMOVE_KEY_FACT_DEF.name == "remove_key_fact"
    assert "key" in REMOVE_KEY_FACT_DEF.parameters_schema["properties"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_key_fact_creates_new(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="SKF", slug=f"skf-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        c = Contact.create(tenant_id=t.id, phone="+971500000000")
        await uow.contacts.save(c)
        await uow.commit()

    async with async_session_factory() as session:
        result = await run_save_key_fact(
            arguments={"key": "name", "value": "Sara"},
            tenant_id=t.id,
            contact_id=c.id,
            session=session,
        )
        await session.commit()
    assert result["status"] == "saved"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_key_fact_updates_existing(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="SKF2", slug=f"skf2-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        c = Contact.create(tenant_id=t.id, phone="+971500000001")
        await uow.contacts.save(c)
        await uow.flush()
        f = KeyFact.create(tenant_id=t.id, contact_id=c.id, key="name", value="Old")
        await uow.key_facts.save(f)
        await uow.commit()

    async with async_session_factory() as session:
        result = await run_save_key_fact(
            arguments={"key": "name", "value": "New"},
            tenant_id=t.id,
            contact_id=c.id,
            session=session,
        )
        await session.commit()
    assert result["status"] == "updated"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_save_key_fact_skips_empty(client: None) -> None:
    async with async_session_factory() as session:
        result = await run_save_key_fact(
            arguments={"key": "", "value": ""},
            tenant_id=uuid4(),
            contact_id=uuid4(),
            session=session,
        )
    assert result["status"] == "skipped"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_key_fact_removes(client: None) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        t = Tenant.create(name="RKF", slug=f"rkf-{uuid4().hex[:8]}")
        await uow.tenants.save(t)
        await uow.flush()
        c = Contact.create(tenant_id=t.id, phone="+971500000002")
        await uow.contacts.save(c)
        await uow.flush()
        f = KeyFact.create(tenant_id=t.id, contact_id=c.id, key="name", value="Sara")
        await uow.key_facts.save(f)
        await uow.commit()

    async with async_session_factory() as session:
        result = await run_remove_key_fact(
            arguments={"key": "name"},
            tenant_id=t.id,
            contact_id=c.id,
            session=session,
        )
        await session.commit()
    assert result["status"] == "removed"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_remove_key_fact_not_found(client: None) -> None:
    async with async_session_factory() as session:
        result = await run_remove_key_fact(
            arguments={"key": "nonexistent"},
            tenant_id=uuid4(),
            contact_id=uuid4(),
            session=session,
        )
    assert result["status"] == "not_found"
