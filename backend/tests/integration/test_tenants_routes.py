"""Integration tests for tenants routes — covers get_my_tenant response shape
and fields."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_my_tenant_full_response(client: AsyncClient) -> None:
    """Verify all fields in the tenant response and that slug/name match registration."""
    token, _, tenant_id = await register_and_token(client)
    resp = await client.get(
        "/api/v1/tenants/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == tenant_id
    assert body["status"] == "active"
    # name and slug should be non-empty strings
    assert isinstance(body["name"], str) and len(body["name"]) > 0
    assert isinstance(body["slug"], str) and len(body["slug"]) > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_my_tenant_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/tenants/me")
    assert resp.status_code == 401
