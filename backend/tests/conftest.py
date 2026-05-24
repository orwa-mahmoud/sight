"""Shared pytest fixtures — sets the test env, migrates the test DB, exposes an HTTP client."""

from __future__ import annotations

import os

# ── Set test env BEFORE any `src.*` import so settings resolve to the test DB ─
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/frontdesk_test",
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    "postgresql://postgres:postgres@localhost:5432/frontdesk_test",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
os.environ["APP_ENV"] = "test"  # forces NullPool in the engine factory

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _migrate_test_db() -> AsyncIterator[None]:
    """Apply alembic migrations to the test database once per session."""
    from alembic.config import Config  # noqa: PLC0415

    from alembic import command  # noqa: PLC0415

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL_SYNC"])
    command.upgrade(cfg, "head")
    yield


@pytest_asyncio.fixture
async def _clean_db() -> AsyncIterator[None]:
    """Truncate data tables before each test (preserves schema + alembic_version)."""
    from src.infrastructure.persistence.postgres.database import async_session_factory  # noqa: PLC0415

    async with async_session_factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE questions, token_usages, messages, conversations, "
                "chunks, documents, user_tenants, tenant_configs, users, tenants "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
    yield


@pytest_asyncio.fixture
async def client(_clean_db: None) -> AsyncIterator[AsyncClient]:
    from src.main import app  # noqa: PLC0415

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def register_and_token(client: AsyncClient) -> tuple[str, str, str]:
    """Helper: register a fresh owner, return (token, user_id, tenant_id)."""
    import uuid  # noqa: PLC0415

    slug = f"t-{uuid.uuid4().hex[:8]}"
    resp = await client.post(
        "/api/v1/auth/register",
        json={
            "email": f"{slug}@test.com",
            "password": "supersecure123",
            "full_name": "Test Owner",
            "tenant_name": f"Tenant {slug}",
            "tenant_slug": slug,
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    return body["access_token"], body["user_id"], body["tenant_id"]
