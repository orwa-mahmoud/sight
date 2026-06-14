"""encrypt telegram_webhook_secret at rest

Revision ID: c1a619c45aaf
Revises: a83dce9a149a
Create Date: 2026-06-14 19:26:59.017869

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op
from src.infrastructure.auth.crypto import _ENC_PREFIX, encrypt_value

# revision identifiers, used by Alembic.
revision: str = "c1a619c45aaf"
down_revision: str | Sequence[str] | None = "a83dce9a149a"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Backfill: encrypt any telegram_webhook_secret still stored as plaintext.

    Every other tenant secret was already encrypted at rest; this field was the
    one persisted in the clear. Idempotent — rows already carrying the 'enc:'
    prefix are skipped, and when ENCRYPTION_KEY is unset (dev/CI) encrypt_value is
    a no-op, so this changes nothing there.
    """
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            "SELECT id, telegram_webhook_secret FROM tenant_configs "
            "WHERE telegram_webhook_secret IS NOT NULL "
            "AND telegram_webhook_secret <> '' "
            "AND telegram_webhook_secret NOT LIKE :prefix"
        ),
        {"prefix": _ENC_PREFIX + "%"},
    ).fetchall()
    for row in rows:
        bind.execute(
            sa.text("UPDATE tenant_configs SET telegram_webhook_secret = :v WHERE id = :id"),
            {"v": encrypt_value(row.telegram_webhook_secret), "id": row.id},
        )


def downgrade() -> None:
    # Intentionally a no-op: we do not rewrite secrets back to plaintext on
    # downgrade. Reads tolerate both encrypted and plaintext values.
    pass
