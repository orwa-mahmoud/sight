"""enable row-level security on tenant data tables

Revision ID: a83dce9a149a
Revises: 719d9a6da3ed
Create Date: 2026-06-02 13:48:55.224608

"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a83dce9a149a"
down_revision: str | Sequence[str] | None = "719d9a6da3ed"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Tenant-scoped data tables that get Row-Level Security. Excluded on purpose:
#   - users / tenants / telegram_phones: identity/lookup, read before a tenant
#     is known (login, registration).
#   - user_tenants: read during auth, before the tenant scope is set.
#   - tenant_configs: read by channel webhooks before auth (signature check).
#   - invitations: legitimately read by unauthenticated token (preview/accept).
#   - outbox_events: infrastructure outbox, not user-facing reads.
# These rely on the app-layer tenant filter (+ encryption at rest for secrets).
_RLS_TABLES = (
    "conversations",
    "messages",
    "contacts",
    "documents",
    "chunks",
    "questions",
    "key_facts",
    "token_usages",
)

# NULLIF(..., '') keeps an unset or empty `app.current_tenant` from raising on the
# uuid cast — it becomes NULL, so the policy matches no rows (fail-closed).
_POLICY_PREDICATE = "tenant_id = NULLIF(current_setting('app.current_tenant', true), '')::uuid"


def upgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(
            f"CREATE POLICY tenant_isolation ON {table} USING ({_POLICY_PREDICATE}) WITH CHECK ({_POLICY_PREDICATE})"
        )


def downgrade() -> None:
    for table in _RLS_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
