# Tenant Isolation

Frontdesk is multi-tenant: every tenant's data (conversations, documents,
contacts, questions, key facts, usage, invitations, config) must be invisible to
every other tenant. This document describes how isolation is enforced today and
the roadmap to defense-in-depth.

## How isolation works today (application layer)

1. **Tenant is never trusted from the client.** It is resolved from the
   authenticated context — the JWT `sub` → user → `user_tenants` link — or, for
   channel webhooks, from the URL path. See `drivers/api/dependencies.py`.
2. **Every repository query filters by `tenant_id`.** Reads and writes are
   scoped in the SQL `WHERE` clause (e.g. `conversation_repo`, `document_repo`,
   `invitation_repo`).
3. **The only cross-tenant view is the platform-admin console** (`/api/v1/admin`),
   guarded by `require_platform_admin`. Regular tenant users get 403.
4. **Owner vs. staff** within a tenant: owner-only routes (settings mutations,
   invitations, tenant management) are guarded by `require_owner`.

Regression coverage: `tests/integration/test_tenant_isolation.py` asserts a
tenant cannot read or act on another tenant's data. Treat a failure there as a
release blocker.

## The gap app-layer alone leaves

App-layer enforcement is correct but relies on every present and future query
remembering to filter by `tenant_id`. A single missed filter is a cross-tenant
leak with nothing to catch it at the database boundary.

## Defense in depth: Row-Level Security (RLS) — implemented, opt-in

RLS makes the database itself refuse cross-tenant rows, beneath the app-layer
filters. It is **implemented** but **inert until you switch the app off the
superuser role** (activation below), so it ships disabled-by-default and the
existing test suite (which connects as `postgres`) is unaffected.

What's in the codebase:

- **Policies** (migration `a83dce9a149a`): `ENABLE ROW LEVEL SECURITY` + a
  `tenant_isolation` policy on the core tenant-data tables — `conversations`,
  `messages`, `contacts`, `documents`, `chunks`, `questions`, `key_facts`,
  `token_usages`. Predicate:
  `tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid`
  (unset/empty scope → matches nothing, i.e. fail-closed).
- **Scope wiring**: `UnitOfWork.set_tenant_scope()` →
  `infrastructure/persistence/postgres/rls.py` runs `set_config(..., is_local)`
  (transaction-local, pool-safe). It is set where the tenant becomes known:
  `get_current_user` (all authenticated routes), the AI gateway
  `chat_with_agent` (chat API + channel webhooks), and per-tenant inside the
  platform-admin cross-tenant listing.
- **Role script**: `scripts/create_app_role.sql` creates the least-privilege
  `frontdesk_app` role (`NOSUPERUSER NOBYPASSRLS`).
- **Proof**: `tests/integration/test_rls_enforcement.py` connects as a real
  NOBYPASSRLS role and asserts a query only sees the scoped tenant's rows (and
  zero when unscoped). Treat its failure as a release blocker.

### Tables intentionally NOT under RLS

`users`, `tenants`, `telegram_phones` (identity/lookup, read before a tenant is
known), `user_tenants` (read during auth, before scope is set), `tenant_configs`
(read by channel webhooks before auth) and `invitations` (read by unauthenticated
token for preview/accept). These stay app-layer-filtered; `tenant_configs`
secrets are additionally encrypted at rest.

### Activating RLS

1. Create the role: `psql -U postgres -d <db> -v app_password="'…'" -f
   scripts/create_app_role.sql` (run against every environment).
2. Point `DATABASE_URL` / `DATABASE_URL_SYNC` at `frontdesk_app`.
3. Keep running migrations as the owning superuser (`postgres`).
4. Validate each flow end-to-end under the new role before production — the
   wiring covers the known paths, but a new flow that reads an RLS table without
   first setting scope will (correctly) see nothing.

A future platform-admin DB path could use a `BYPASSRLS` role as the single,
auditable exception instead of re-scoping per tenant.
