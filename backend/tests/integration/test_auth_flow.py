"""End-to-end auth flow: register → login → /me."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

_OWNER = {
    "email": "owner@example.com",
    "password": "supersecure123",
    "full_name": "Test Owner",
    "tenant_name": "Test Front Desk",
    "tenant_slug": "test-front-desk",
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_login_me_flow(client: AsyncClient) -> None:
    # ── Register ──────────────────────────────────────────────────
    resp = await client.post("/api/v1/auth/register", json=_OWNER)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    user_id = body["user_id"]
    tenant_id = body["tenant_id"]

    # ── Login ─────────────────────────────────────────────────────
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": _OWNER["email"], "password": _OWNER["password"]},
    )
    assert resp.status_code == 200, resp.text
    login_body = resp.json()
    assert login_body["user_id"] == user_id
    assert login_body["tenant_id"] == tenant_id
    token = login_body["access_token"]

    # ── /me ───────────────────────────────────────────────────────
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    me = resp.json()
    assert me["id"] == user_id
    assert me["email"] == _OWNER["email"]
    assert me["full_name"] == _OWNER["full_name"]
    assert me["is_active"] is True
    assert me["tenant"]["id"] == tenant_id
    assert me["tenant"]["slug"] == _OWNER["tenant_slug"]
    assert me["tenant"]["name"] == _OWNER["tenant_name"]
    assert me["tenant"]["role"] == "owner"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    first = await client.post("/api/v1/auth/register", json=_OWNER)
    assert first.status_code == 201

    second_payload = {**_OWNER, "tenant_slug": "another-slug"}
    second = await client.post("/api/v1/auth/register", json=second_payload)
    assert second.status_code == 400
    assert "email" in second.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_rejects_duplicate_slug(client: AsyncClient) -> None:
    first = await client.post("/api/v1/auth/register", json=_OWNER)
    assert first.status_code == 201

    second_payload = {**_OWNER, "email": "another@example.com"}
    second = await client.post("/api/v1/auth/register", json=second_payload)
    assert second.status_code == 400
    assert "slug" in second.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post("/api/v1/auth/register", json=_OWNER)
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": _OWNER["email"], "password": "wrong-password"},
    )
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_requires_token(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_me_rejects_malformed_token(client: AsyncClient) -> None:
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert resp.status_code == 401
