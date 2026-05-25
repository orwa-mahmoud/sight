"""Integration tests for tenant API."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_my_tenant(client: AsyncClient) -> None:
    token, _, tenant_id = await register_and_token(client)
    resp = await client.get("/api/v1/tenants/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == tenant_id
    assert body["status"] == "active"

@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_my_tenant_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/tenants/me")
    assert resp.status_code == 401
