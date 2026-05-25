"""Integration test for auth refresh endpoint."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_returns_new_token(client: AsyncClient) -> None:
    token, user_id, tenant_id = await register_and_token(client)
    resp = await client.post("/api/v1/auth/refresh", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["tenant_id"] == tenant_id
    assert body["access_token"]  # new token issued

@pytest.mark.integration
@pytest.mark.asyncio
async def test_refresh_requires_auth(client: AsyncClient) -> None:
    resp = await client.post("/api/v1/auth/refresh")
    assert resp.status_code == 401
