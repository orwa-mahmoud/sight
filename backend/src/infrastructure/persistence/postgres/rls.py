"""Row-Level Security (RLS) helpers — per-transaction tenant scoping.

Postgres RLS policies on the tenant-scoped tables filter rows by the
`app.current_tenant` runtime setting. The application sets that setting once the
tenant is known (after auth, or from a webhook/gateway tenant id), so the
database itself refuses cross-tenant rows — a backstop beneath the app-layer
`WHERE tenant_id = ...` filters.

This is INERT until the app connects as a non-superuser role without BYPASSRLS
(see docs/TENANT_ISOLATION.md). Under the default `postgres` superuser the
SET is harmless and RLS is bypassed, so these calls are safe to leave in place.

`set_config(..., is_local => true)` is the parameterized equivalent of
`SET LOCAL`: it lives for the current transaction only, so a pooled connection
never leaks one request's tenant scope into the next.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

_SET_TENANT = text("SELECT set_config('app.current_tenant', :tenant_id, true)")
_CLEAR_TENANT = text("SELECT set_config('app.current_tenant', '', true)")


async def set_current_tenant(session: AsyncSession, tenant_id: UUID) -> None:
    """Scope the current transaction to `tenant_id` for RLS-protected tables."""
    await session.execute(_SET_TENANT, {"tenant_id": str(tenant_id)})


async def clear_current_tenant(session: AsyncSession) -> None:
    """Clear tenant scope (RLS-protected tables then return no rows)."""
    await session.execute(_CLEAR_TENANT)
