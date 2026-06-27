"""Shared pytest fixtures — sets the test env, migrates the test DB, exposes an HTTP client."""

from __future__ import annotations

import os
import tempfile

# ── Set test env BEFORE any `src.*` import so settings resolve to the test DB ─
os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/sight_test",
)
os.environ.setdefault(
    "DATABASE_URL_SYNC",
    "postgresql://postgres:postgres@localhost:5432/sight_test",
)
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-not-for-production")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:5173")
# Stream uploaded files to a throwaway dir so the suite never touches the real one.
os.environ.setdefault("UPLOAD_STORAGE_DIR", tempfile.mkdtemp(prefix="sight-test-uploads-"))
os.environ["APP_ENV"] = "test"  # forces NullPool in the engine factory

from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text


@pytest_asyncio.fixture(scope="session", autouse=True)
async def _migrate_test_db() -> AsyncIterator[None]:
    """Apply alembic migrations to the test database once per session."""
    from alembic.config import Config

    from alembic import command

    cfg = Config("alembic.ini")
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL_SYNC"])
    command.upgrade(cfg, "head")
    yield


@pytest_asyncio.fixture
async def _clean_db() -> AsyncIterator[None]:
    """Truncate data tables before each test (preserves schema + alembic_version)."""
    from src.infrastructure.persistence.postgres.database import async_session_factory

    async with async_session_factory() as session:
        await session.execute(
            text(
                "TRUNCATE TABLE questions, token_usages, messages, conversations, "
                "chunks, documents, invitations, user_tenants, tenant_configs, users, tenants "
                "RESTART IDENTITY CASCADE"
            )
        )
        await session.commit()
    yield


@pytest_asyncio.fixture
async def client(_clean_db: None) -> AsyncIterator[AsyncClient]:
    from unittest.mock import AsyncMock

    from src.drivers.api.dependencies import get_job_pool
    from src.main import app

    # ASGITransport doesn't run the lifespan, so the real Arq pool is never created.
    # Override the dependency with a no-op pool: uploads enqueue against a mock and the
    # document stays `uploaded` until a worker (or a direct `ingest_document` call) runs it.
    no_op_pool = AsyncMock()
    app.dependency_overrides[get_job_pool] = lambda: no_op_pool
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_job_pool, None)


async def register_and_token(client: AsyncClient) -> tuple[str, str, str]:
    """Helper: register a fresh owner, return (token, user_id, tenant_id)."""
    import uuid

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
