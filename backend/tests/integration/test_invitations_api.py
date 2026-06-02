"""Integration tests for the tenant invitation lifecycle + role gating."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> tuple[str, str, str]:
    """Register an owner; return (token, user_id, tenant_id)."""
    slug = f"t-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "supersecure123",
            "full_name": "Owner",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    return body["access_token"], body["user_id"], body["tenant_id"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _invite(client: AsyncClient, owner_token: str, email: str) -> dict[str, str]:
    resp = await client.post("/api/v1/invitations", headers=_auth(owner_token), json={"email": email})
    assert resp.status_code == 201, resp.text
    data: dict[str, str] = resp.json()
    return data


@pytest.mark.integration
@pytest.mark.asyncio
async def test_owner_creates_and_lists_invitation(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    inv = await _invite(client, owner_token, "invitee@test.com")
    assert inv["status"] == "pending"
    assert inv["role"] == "staff"
    assert inv["token"]
    assert inv["invite_url"].endswith(f"/invite/{inv['token']}")

    listing = await client.get("/api/v1/invitations", headers=_auth(owner_token))
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["email"] == "invitee@test.com"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_duplicate_pending_invite_rejected(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    await _invite(client, owner_token, "invitee@test.com")
    resp = await client.post("/api/v1/invitations", headers=_auth(owner_token), json={"email": "invitee@test.com"})
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cannot_invite_existing_member(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    resp = await client.post("/api/v1/invitations", headers=_auth(owner_token), json={"email": "owner@test.com"})
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_public_preview_by_token(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    inv = await _invite(client, owner_token, "invitee@test.com")
    # No auth header — preview is public.
    resp = await client.get(f"/api/v1/invitations/token/{inv['token']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True
    assert body["email"] == "invitee@test.com"
    assert body["tenant_name"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_via_invitation_creates_staff_member(client: AsyncClient) -> None:
    owner_token, _, owner_tenant = await _register(client, "owner@test.com")
    inv = await _invite(client, owner_token, "newbie@test.com")

    resp = await client.post(
        f"/api/v1/invitations/token/{inv['token']}/register",
        json={"password": "supersecure123", "full_name": "Newbie"},
    )
    assert resp.status_code == 201, resp.text
    new_token = resp.json()["access_token"]

    # The new user is a STAFF member of the owner's tenant.
    me = await client.get("/api/v1/auth/me", headers=_auth(new_token))
    assert me.status_code == 200
    assert me.json()["tenant"]["id"] == owner_tenant
    assert me.json()["tenant"]["role"] == "staff"

    # The invite is now accepted.
    listing = await client.get("/api/v1/invitations", headers=_auth(owner_token))
    assert listing.json()[0]["status"] == "accepted"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_register_via_invitation_twice_fails(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    inv = await _invite(client, owner_token, "newbie@test.com")
    first = await client.post(
        f"/api/v1/invitations/token/{inv['token']}/register",
        json={"password": "supersecure123"},
    )
    assert first.status_code == 201
    # The invite is consumed; a second registration is invalid.
    second = await client.post(
        f"/api/v1/invitations/token/{inv['token']}/register",
        json={"password": "supersecure123"},
    )
    assert second.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_existing_user_accepts_invitation(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    # An existing user with their own tenant.
    other_token, _, _ = await _register(client, "existing@test.com")
    inv = await _invite(client, owner_token, "existing@test.com")

    resp = await client.post(f"/api/v1/invitations/token/{inv['token']}/accept", headers=_auth(other_token))
    assert resp.status_code == 204

    listing = await client.get("/api/v1/invitations", headers=_auth(owner_token))
    assert listing.json()[0]["status"] == "accepted"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_accept_with_wrong_account_forbidden(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    wrong_token, _, _ = await _register(client, "wrong@test.com")
    inv = await _invite(client, owner_token, "invitee@test.com")

    resp = await client.post(f"/api/v1/invitations/token/{inv['token']}/accept", headers=_auth(wrong_token))
    assert resp.status_code == 403


@pytest.mark.integration
@pytest.mark.asyncio
async def test_reject_invitation(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    other_token, _, _ = await _register(client, "existing@test.com")
    inv = await _invite(client, owner_token, "existing@test.com")

    resp = await client.post(f"/api/v1/invitations/token/{inv['token']}/reject", headers=_auth(other_token))
    assert resp.status_code == 204
    listing = await client.get("/api/v1/invitations", headers=_auth(owner_token))
    assert listing.json()[0]["status"] == "rejected"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_owner_revokes_invitation(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    inv = await _invite(client, owner_token, "invitee@test.com")
    resp = await client.post(f"/api/v1/invitations/{inv['id']}/revoke", headers=_auth(owner_token))
    assert resp.status_code == 204
    listing = await client.get("/api/v1/invitations", headers=_auth(owner_token))
    assert listing.json()[0]["status"] == "revoked"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_staff_cannot_create_invitation(client: AsyncClient) -> None:
    owner_token, _, _ = await _register(client, "owner@test.com")
    inv = await _invite(client, owner_token, "newbie@test.com")
    reg = await client.post(
        f"/api/v1/invitations/token/{inv['token']}/register",
        json={"password": "supersecure123"},
    )
    staff_token = reg.json()["access_token"]

    # A STAFF member is not an owner → cannot invite others.
    resp = await client.post("/api/v1/invitations", headers=_auth(staff_token), json={"email": "another@test.com"})
    assert resp.status_code == 403
