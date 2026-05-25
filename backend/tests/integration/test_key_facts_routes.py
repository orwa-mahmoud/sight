"""Integration tests for key facts routes — covers listing with and without
participant filter, with seeded data."""

from __future__ import annotations

from uuid import UUID

import pytest
from httpx import AsyncClient

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.key_facts.entities import KeyFact
from src.infrastructure.persistence.postgres.database import async_session_factory
from tests.conftest import register_and_token


async def _seed_key_facts(tenant_id: UUID) -> None:
    """Insert a few key facts for two participants."""
    async with async_session_factory() as session:
        uow = UnitOfWork(session)

        for participant, facts in [
            ("+971501234567", [("name", "Alice"), ("language", "English")]),
            ("+971509876543", [("name", "Bob"), ("budget", "500 AED")]),
        ]:
            for key, value in facts:
                fact = KeyFact.create(
                    tenant_id=tenant_id,
                    participant_identifier=participant,
                    key=key,
                    value=value,
                )
                await uow.key_facts.save(fact)

        await uow.commit()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_all_key_facts(client: AsyncClient) -> None:
    """Without a participant filter, all facts for the tenant are returned."""
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
        assert "participant_identifier" in fact
        assert "key" in fact
        assert "value" in fact


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_key_facts_filtered_by_participant(client: AsyncClient) -> None:
    """With a participant filter, only that participant's facts are returned."""
    token, _, tenant_id = await register_and_token(client)
    await _seed_key_facts(UUID(tenant_id))

    resp = await client.get(
        "/api/v1/key-facts",
        params={"participant": "+971501234567"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 2
    identifiers = {f["participant_identifier"] for f in body}
    assert identifiers == {"+971501234567"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_key_facts_participant_no_results(client: AsyncClient) -> None:
    """Filtering by a non-existent participant returns an empty list."""
    token, _, _ = await register_and_token(client)

    resp = await client.get(
        "/api/v1/key-facts",
        params={"participant": "nobody"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_key_facts_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/key-facts")
    assert resp.status_code == 401
