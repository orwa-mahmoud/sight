# 0003 — Tenant isolation: app-layer filters **and** Postgres RLS (opt-in)

**Status:** Accepted

## Context

Multi-tenant data leaks are catastrophic and easy to cause: one query that
forgets `WHERE tenant_id = …` is a cross-tenant breach with nothing to catch it.
App-layer filtering alone relies on every present *and future* query being
correct. I wanted a database-level backstop without breaking the dev/test
experience.

## Decision

Defense in depth:

1. **App layer (always on):** `tenant_id` is resolved from the authenticated JWT
   or the webhook URL path — **never** the client payload — and every repository
   query filters by it.
2. **Postgres Row-Level Security (opt-in backstop):** policies on the core
   tenant-scoped tables with a **fail-closed** predicate
   (`tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid` —
   unset scope matches *nothing*). Scope is set per-transaction via
   `set_config(..., is_local => true)` (pool-safe), wherever the tenant becomes
   known: `get_current_user`, the AI gateway, and per-tenant inside the admin
   console.

RLS ships **inert under the default `postgres` superuser** (which bypasses RLS),
so local dev and the existing test suite are unaffected. Activation = create the
`frontdesk_app` NOBYPASSRLS role (`scripts/create_app_role.sql`) and point
`DATABASE_URL` at it. Full detail in
[backend/docs/TENANT_ISOLATION.md](../../backend/docs/TENANT_ISOLATION.md).

## Consequences

**Good:** a forgotten filter is contained by the database instead of leaking;
isolation is proven by a test that connects as a real NOBYPASSRLS role
(`test_rls_enforcement.py`); zero friction for contributors who run as superuser.

**Costs:** RLS is dormant unless deliberately activated, so the protection isn't
on by default in production yet (tracked: make the app role the default + run RLS
tests in CI). A few tables are intentionally outside RLS (identity/lookup tables
read before a tenant is known) and stay app-layer-filtered.
