"""Integration tests for conversations API endpoints."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_conversations_empty(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/conversations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daily_summary_empty(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.get("/api/v1/conversations/daily-summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_messages"] == 0
    assert body["active_conversations"] == 0
    assert body["questions_escalated"] == 0
    assert "date" in body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_daily_summary_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/conversations/daily-summary")
    assert resp.status_code == 401
