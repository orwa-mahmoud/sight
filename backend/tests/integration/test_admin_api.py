"""Integration tests for the platform super-admin endpoints."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.shared.unit_of_work import UnitOfWork
from src.bootstrap.container import set_platform_admin_use_case
from src.infrastructure.persistence.postgres.database import async_session_factory


async def _register(client: AsyncClient, email: str) -> tuple[str, str, str]:
    """Register an owner with a known email; return (token, user_id, tenant_id)."""
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


async def _promote(email: str) -> None:
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        await set_platform_admin_use_case(uow).execute(email=email, granted=True)
        await session.commit()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_endpoints(client: AsyncClient) -> None:
    token, _, _ = await _register(client, "regular@test.com")
    for path in ("/api/v1/admin/tenants", "/api/v1/admin/users"):
        resp = await client.get(path, headers=_auth(token))
        assert resp.status_code == 403, f"{path}: {resp.text}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_lists_all_tenants_and_users(client: AsyncClient) -> None:
    admin_token, _, _ = await _register(client, "admin@test.com")
    await _register(client, "other@test.com")
    await _promote("admin@test.com")

    tenants = await client.get("/api/v1/admin/tenants", headers=_auth(admin_token))
    assert tenants.status_code == 200
    assert len(tenants.json()) == 2
    owner_emails = {row["owner_email"] for row in tenants.json()}
    assert owner_emails == {"admin@test.com", "other@test.com"}

    users = await client.get("/api/v1/admin/users", headers=_auth(admin_token))
    assert users.status_code == 200
    assert len(users.json()) == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_deactivates_tenant_blocks_member_login(client: AsyncClient) -> None:
    admin_token, _, _ = await _register(client, "admin@test.com")
    _, _, victim_tenant = await _register(client, "victim@test.com")
    await _promote("admin@test.com")

    # Suspend the victim's tenant.
    resp = await client.post(f"/api/v1/admin/tenants/{victim_tenant}/deactivate", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "suspended"

    # Victim can no longer log in.
    login = await client.post("/api/v1/auth/login", json={"email": "victim@test.com", "password": "supersecure123"})
    assert login.status_code == 401

    # Reactivate → login works again.
    resp = await client.post(f"/api/v1/admin/tenants/{victim_tenant}/activate", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"
    login = await client.post("/api/v1/auth/login", json={"email": "victim@test.com", "password": "supersecure123"})
    assert login.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_deactivates_user_blocks_login(client: AsyncClient) -> None:
    admin_token, _, _ = await _register(client, "admin@test.com")
    _, victim_id, _ = await _register(client, "victim@test.com")
    await _promote("admin@test.com")

    resp = await client.post(f"/api/v1/admin/users/{victim_id}/deactivate", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert resp.json()["is_active"] is False

    login = await client.post("/api/v1/auth/login", json={"email": "victim@test.com", "password": "supersecure123"})
    assert login.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(client: AsyncClient) -> None:
    admin_token, admin_id, _ = await _register(client, "admin@test.com")
    await _promote("admin@test.com")
    resp = await client.post(f"/api/v1/admin/users/{admin_id}/deactivate", headers=_auth(admin_token))
    assert resp.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_admin_cannot_deactivate_another_admin(client: AsyncClient) -> None:
    admin_token, _, _ = await _register(client, "admin@test.com")
    _, other_admin_id, _ = await _register(client, "admin2@test.com")
    await _promote("admin@test.com")
    await _promote("admin2@test.com")
    resp = await client.post(f"/api/v1/admin/users/{other_admin_id}/deactivate", headers=_auth(admin_token))
    assert resp.status_code == 400
