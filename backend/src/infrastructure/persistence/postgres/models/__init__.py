"""ORM Base + model registry.

Every model is imported here so that `Base.metadata` is fully populated
before Alembic's autogenerate runs.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# ── Model imports (must come after Base to avoid circulars) ───────
from src.infrastructure.persistence.postgres.models.tenant import TenantModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.user import UserModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.user_tenant import UserTenantModel  # noqa: E402

__all__ = ["Base", "TenantModel", "UserModel", "UserTenantModel"]
