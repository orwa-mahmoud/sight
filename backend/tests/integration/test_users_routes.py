"""Integration tests for users routes — covers update_profile with name,
password, both, and empty updates."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from tests.conftest import register_and_token


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_full_name_returns_profile(client: AsyncClient) -> None:
    token, user_id, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/users/me",
        json={"full_name": "Updated Name"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["id"] == user_id
    assert body["full_name"] == "Updated Name"
    assert "email" in body


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_password_then_login(client: AsyncClient) -> None:
    """After changing the password, the old one should fail and the new one should work."""
    import uuid

    slug = f"t-{uuid.uuid4().hex[:8]}"
    email = f"{slug}@test.com"
    old_password = "supersecure123"
    new_password = "brandnewpassword456"

    # Register
    reg_resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": old_password,
            "full_name": "Password Tester",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["access_token"]

    # Change password
    resp = await client.put(
        "/api/v1/users/me",
        json={"password": new_password, "current_password": old_password},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200

    # Old password should fail
    login_old = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": old_password},
    )
    assert login_old.status_code == 401

    # New password should succeed
    login_new = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": new_password},
    )
    assert login_new.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_both_name_and_password(client: AsyncClient) -> None:
    token, _, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/users/me",
        json={"full_name": "Both Updated", "password": "anothersecure99", "current_password": "supersecure123"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["full_name"] == "Both Updated"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_noop(client: AsyncClient) -> None:
    """Sending no fields still returns the current profile without errors."""
    token, user_id, _ = await register_and_token(client)
    resp = await client.put(
        "/api/v1/users/me",
        json={},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json()["id"] == user_id


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update_profile_requires_auth(client: AsyncClient) -> None:
    resp = await client.put("/api/v1/users/me", json={"full_name": "Hacker"})
    assert resp.status_code == 401
