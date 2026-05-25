"""Integration tests for key facts routes — covers listing with and without
contact_id filter, with seeded data."""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.contacts.entities import Contact
from src.domain.key_facts.entities import KeyFact
from src.infrastructure.persistence.postgres.database import async_session_factory
from tests.conftest import register_and_token


async def _seed_key_facts(tenant_id: UUID) -> tuple[UUID, UUID]:
    """Insert a few key facts for two contacts. Returns their IDs."""
    async with async_session_factory() as session:
        uow = UnitOfWork(session)

        c1 = Contact.create(tenant_id=tenant_id, phone="+971501234567")
        await uow.contacts.save(c1)
        c2 = Contact.create(tenant_id=tenant_id, phone="+971509876543")
        await uow.contacts.save(c2)
        await uow.flush()

        for contact, facts in [
            (c1, [("name", "Alice"), ("language", "English")]),
            (c2, [("name", "Bob"), ("budget", "500 AED")]),
        ]:
            for key, value in facts:
                fact = KeyFact.create(
                    tenant_id=tenant_id,
                    contact_id=contact.id,
                    key=key,
                    value=value,
                )
                await uow.key_facts.save(fact)

        await uow.commit()
    return c1.id, c2.id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_all_key_facts(client: AsyncClient) -> None:
    """Without a contact_id filter, all facts for the tenant are returned."""
    token, _, tenant_id = await register_and_token(client)
    await _seed_key_facts(UUID(tenant_id))

    resp = await client.get(
        "/api/v1/key-facts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 4
    # Each fact has the expected shape
    for fact in body:
        assert "id" in fact
        assert "contact_id" in fact
        assert "key" in fact
        assert "value" in fact


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_key_facts_filtered_by_contact(client: AsyncClient) -> None:
    """With a contact_id filter, only that contact's facts are returned."""
    token, _, tenant_id = await register_and_token(client)
    c1_id, _ = await _seed_key_facts(UUID(tenant_id))

    resp = await client.get(
        "/api/v1/key-facts",
        params={"contact_id": str(c1_id)},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    contact_ids = {f["contact_id"] for f in body}
    assert contact_ids == {str(c1_id)}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_key_facts_contact_no_results(client: AsyncClient) -> None:
    """Filtering by a non-existent contact returns an empty list."""
    token, _, _ = await register_and_token(client)

    resp = await client.get(
        "/api/v1/key-facts",
        params={"contact_id": "00000000-0000-0000-0000-000000000000"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_key_facts_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/key-facts")
    assert resp.status_code == 401
