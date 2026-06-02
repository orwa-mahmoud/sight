"""Proof that Row-Level Security actually enforces at the database layer.

The rest of the suite connects as the `postgres` superuser, for whom RLS is
bypassed — so it cannot exercise the policies. This test creates a dedicated
NOBYPASSRLS role, connects as it, and verifies that the `app.current_tenant`
setting scopes every query to a single tenant (and that an unset scope returns
nothing — fail-closed).

This is the test that would fail if the RLS policies (migration a83dce9a149a)
were dropped or written incorrectly.
"""

from __future__ import annotations

import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.tenants.entities import Tenant
from src.infrastructure.persistence.postgres.database import async_session_factory

_APP_ROLE = "frontdesk_rls_test"
_APP_PASSWORD = "rls_test_pw"


def _restricted_url() -> str:
    """Derive the restricted-role async URL from the test DATABASE_URL."""
    url = os.environ["DATABASE_URL"]  # e.g. postgresql+asyncpg://postgres:postgres@host/db
    after_scheme = url.split("://", 1)[1]
    host_part = after_scheme.split("@", 1)[1]
    return f"postgresql+asyncpg://{_APP_ROLE}:{_APP_PASSWORD}@{host_part}"


@pytest_asyncio.fixture
async def restricted_engine(_clean_db: None) -> AsyncIterator[AsyncEngine]:
    # Seed two tenants, each with one contact (contacts is RLS-protected).
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant_a = Tenant.create(name="Tenant A", slug="rls-a")
        tenant_b = Tenant.create(name="Tenant B", slug="rls-b")
        await uow.tenants.save(tenant_a)
        await uow.tenants.save(tenant_b)
        await uow.flush()
        await uow.contacts.get_or_create_by_phone(tenant_id=tenant_a.id, phone="+100", name="A")
        await uow.contacts.get_or_create_by_phone(tenant_id=tenant_b.id, phone="+200", name="B")
        await session.commit()

    # Create the NOBYPASSRLS role + grants (idempotent), as superuser.
    async with async_session_factory() as session:
        await session.execute(
            text(
                "DO $$ BEGIN "
                f"IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{_APP_ROLE}') THEN "
                f"CREATE ROLE {_APP_ROLE} LOGIN PASSWORD '{_APP_PASSWORD}' NOSUPERUSER NOBYPASSRLS; "
                "END IF; END $$;"
            )
        )
        await session.execute(text(f"GRANT USAGE ON SCHEMA public TO {_APP_ROLE}"))
        await session.execute(
            text(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {_APP_ROLE}")
        )
        await session.commit()

    engine = create_async_engine(_restricted_url(), poolclass=NullPool)
    # Sanity: the role must NOT bypass RLS, or the test would prove nothing.
    async with engine.connect() as conn:
        bypass = await conn.scalar(text("SELECT rolbypassrls FROM pg_roles WHERE rolname = current_user"))
        assert bypass is False, "test role unexpectedly bypasses RLS"
    yield engine
    await engine.dispose()


async def _count_contacts(engine: AsyncEngine, tenant_scope: str | None) -> int:
    async with engine.connect() as conn:
        if tenant_scope is None:
            await conn.execute(text("SELECT set_config('app.current_tenant', '', true)"))
        else:
            await conn.execute(text("SELECT set_config('app.current_tenant', :t, true)"), {"t": tenant_scope})
        result = await conn.scalar(text("SELECT count(*) FROM contacts"))
        return int(result or 0)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_rls_scopes_reads_to_the_current_tenant(restricted_engine: AsyncEngine) -> None:
    # Find the two tenants we seeded.
    async with async_session_factory() as session:
        a = await UnitOfWork(session).tenants.get_by_slug("rls-a")
        b = await UnitOfWork(session).tenants.get_by_slug("rls-b")
    assert a is not None and b is not None

    # Scoped to A → only A's contact; scoped to B → only B's.
    assert await _count_contacts(restricted_engine, str(a.id)) == 1
    assert await _count_contacts(restricted_engine, str(b.id)) == 1

    # No scope set → fail-closed, zero rows (not a leak of everything).
    assert await _count_contacts(restricted_engine, None) == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_superuser_bypasses_rls_sees_all(restricted_engine: AsyncEngine) -> None:
    # The default (postgres) connection bypasses RLS and sees both tenants'
    # rows — which is exactly why the app must NOT run as a superuser in prod.
    async with async_session_factory() as session:
        total = await session.scalar(text("SELECT count(*) FROM contacts"))
    assert int(total or 0) == 2
