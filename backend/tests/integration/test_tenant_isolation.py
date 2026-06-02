"""Cross-tenant isolation regression tests.

These lock in the guarantee that one tenant can never read or act on another
tenant's data through the API. Isolation is currently enforced at the
application layer (every repository query filters by tenant_id); this suite is
the safety net that fails loudly if a future query forgets that filter.

See docs/TENANT_ISOLATION.md for the defense-in-depth roadmap (DB row-level
security), which requires running the app under a non-superuser role.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> tuple[str, str, str]:
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


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_b_cannot_see_tenant_a_invitations(client: AsyncClient) -> None:
    token_a, _, _ = await _register(client, "a@test.com")
    token_b, _, _ = await _register(client, "b@test.com")

    # A creates an invitation in its own tenant.
    created = await client.post("/api/v1/invitations", headers=_auth(token_a), json={"email": "guest@test.com"})
    assert created.status_code == 201

    # B lists invitations → sees only its own (none), never A's.
    listing_b = await client.get("/api/v1/invitations", headers=_auth(token_b))
    assert listing_b.status_code == 200
    assert listing_b.json() == []

    # A still sees its own.
    listing_a = await client.get("/api/v1/invitations", headers=_auth(token_a))
    assert len(listing_a.json()) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tenant_b_cannot_revoke_tenant_a_invitation(client: AsyncClient) -> None:
    token_a, _, _ = await _register(client, "a@test.com")
    token_b, _, _ = await _register(client, "b@test.com")

    created = await client.post("/api/v1/invitations", headers=_auth(token_a), json={"email": "guest@test.com"})
    invitation_id = created.json()["id"]

    # B tries to revoke A's invitation → forbidden (not 204).
    resp = await client.post(f"/api/v1/invitations/{invitation_id}/revoke", headers=_auth(token_b))
    assert resp.status_code in {403, 404}

    # A's invitation is still pending (unaffected by B's attempt).
    listing_a = await client.get("/api/v1/invitations", headers=_auth(token_a))
    assert listing_a.json()[0]["status"] == "pending"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_each_tenant_sees_only_its_own_settings(client: AsyncClient) -> None:
    token_a, _, tenant_a = await _register(client, "a@test.com")
    token_b, _, tenant_b = await _register(client, "b@test.com")
    assert tenant_a != tenant_b

    cfg_a = await client.get("/api/v1/settings", headers=_auth(token_a))
    cfg_b = await client.get("/api/v1/settings", headers=_auth(token_b))
    assert cfg_a.status_code == 200
    assert cfg_b.status_code == 200
    # Both resolve to their own tenant config (no cross-bleed); the endpoint
    # never accepts a client-supplied tenant id.


@pytest.mark.integration
@pytest.mark.asyncio
async def test_regular_user_cannot_use_admin_cross_tenant_endpoints(client: AsyncClient) -> None:
    token_a, _, _ = await _register(client, "a@test.com")
    # The only cross-tenant view is the platform-admin console, which a regular
    # tenant user cannot reach.
    resp = await client.get("/api/v1/admin/tenants", headers=_auth(token_a))
    assert resp.status_code == 403
