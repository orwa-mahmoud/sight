"""Integration tests for the admin CLI + platform-admin startup bootstrap."""

from __future__ import annotations

import uuid

import pytest
from httpx import AsyncClient

from src.application.shared.unit_of_work import UnitOfWork
from src.bootstrap.startup import bootstrap_platform_admin
from src.cli.__main__ import _set_admin
from src.config.settings import get_settings
from src.infrastructure.persistence.postgres.database import async_session_factory


async def _register(client: AsyncClient, email: str) -> None:
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


async def _is_admin(email: str) -> bool:
    async with async_session_factory() as session:
        user = await UnitOfWork(session).users.get_by_email(email)
        assert user is not None
        return user.is_platform_admin


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cli_grant_and_revoke(client: AsyncClient) -> None:
    await _register(client, "cli@test.com")

    assert await _set_admin("cli@test.com", granted=True) == 0
    assert await _is_admin("cli@test.com") is True

    assert await _set_admin("cli@test.com", granted=False) == 0
    assert await _is_admin("cli@test.com") is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cli_grant_unknown_user_returns_error(client: AsyncClient) -> None:
    assert await _set_admin("nobody@test.com", granted=True) == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_startup_bootstrap_grants_when_user_exists(client: AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    await _register(client, "boot@test.com")
    settings = get_settings()
    monkeypatch.setattr(settings, "platform_admin_email", "boot@test.com")
    await bootstrap_platform_admin(settings)
    assert await _is_admin("boot@test.com") is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_startup_bootstrap_missing_user_is_not_fatal(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "platform_admin_email", "ghost@test.com")
    # Should not raise even though no such user exists.
    await bootstrap_platform_admin(settings)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_startup_bootstrap_noop_without_email(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "platform_admin_email", None)
    await bootstrap_platform_admin(settings)  # no-op, no error
