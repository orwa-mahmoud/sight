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
        await session.execute(text("TRUNCATE TABLE user_tenants, users, tenants RESTART IDENTITY CASCADE"))
        await session.commit()
    yield


@pytest_asyncio.fixture
async def client(_clean_db: None) -> AsyncIterator[AsyncClient]:
    from src.main import app  # noqa: PLC0415

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
