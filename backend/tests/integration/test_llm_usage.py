"""Integration tests for the token-usage recording + aggregation endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from src.application.llm_usage.commands import RecordTokenUsage
from src.application.llm_usage.use_cases.record_token_usage import RecordTokenUsageUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.infrastructure.persistence.postgres.database import async_session_factory


@pytest.mark.integration
@pytest.mark.asyncio
async def test_usage_stats_empty_for_new_tenant(client: AsyncClient) -> None:
    # Register the owner to get a token.
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@example.com",
            "password": "supersecure123",
            "full_name": "Owner",
            "tenant_name": "Test",
            "tenant_slug": "test",
        },
    )
    token = resp.json()["access_token"]

    resp = await client.get(
        "/api/v1/llm-usage/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_calls"] == 0
    assert body["total_input_tokens"] == 0
    assert body["total_cost"] == "0"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_usage_stats_aggregate_after_recording(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner2@example.com",
            "password": "supersecure123",
            "full_name": "Owner",
            "tenant_name": "Test 2",
            "tenant_slug": "test-2",
        },
    )
    tenant_id_str = resp.json()["tenant_id"]
    token = resp.json()["access_token"]

    from uuid import UUID

    tenant_id = UUID(tenant_id_str)

    # Record two LLM calls directly through the use case.
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await RecordTokenUsageUseCase(uow=uow).execute(
            RecordTokenUsage(
                tenant_id=tenant_id,
                provider="openai",
                model="gpt-4o-mini",
                input_tokens=1000,
                output_tokens=500,
            )
        )
        await RecordTokenUsageUseCase(uow=uow).execute(
            RecordTokenUsage(
                tenant_id=tenant_id,
                provider="openai",
                model="gpt-4o-mini",
                input_tokens=2000,
                output_tokens=1000,
            )
        )
        await uow.commit()

    resp = await client.get(
        "/api/v1/llm-usage/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_calls"] == 2
    assert body["total_input_tokens"] == 3000
    assert body["total_output_tokens"] == 1500
    # gpt-4o-mini: 3000 input * $0.15/1M + 1500 output * $0.60/1M
    # = 0.00045 + 0.00090 = 0.00135
    assert body["total_cost"] == "0.00135000"
