"""ORM Base class — every model inherits from this so alembic autogenerate sees them."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


__all__ = ["Base"]
