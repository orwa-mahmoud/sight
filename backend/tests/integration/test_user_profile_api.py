"""Integration tests for user profile endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_full_name(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/users/me",
        json={"full_name": "New Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "New Name"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_password(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/users/me",
        json={"password": "newlongpassword123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_requires_auth(client: AsyncClient) -> None:
    resp = await client.put("/api/v1/users/me", json={"full_name": "X"})
    assert resp.status_code == 401
