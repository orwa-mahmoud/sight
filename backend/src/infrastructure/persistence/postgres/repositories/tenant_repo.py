"""PostgreSQL Tenant repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.tenants.entities import Tenant
from src.domain.tenants.value_objects import TenantStatus
from src.infrastructure.persistence.postgres.models.tenant import TenantModel


class PostgresTenantRepository:
    """Concrete tenant repository — implements the `TenantRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, tenant: Tenant) -> None:
        if tenant.is_new:
            self._session.add(self._to_model(tenant))
            tenant.mark_persisted()
            return
        model = await self._session.get(TenantModel, tenant.id)
        if model is None:
            # Treat as insert if missing — keeps save idempotent for replays.
            self._session.add(self._to_model(tenant))
            return
        model.name = tenant.name
        model.slug = tenant.slug
        model.status = tenant.status.value
        model.updated_at = tenant.updated_at

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        model = await self._session.get(TenantModel, tenant_id)
        return self._to_entity(model) if model else None

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(TenantModel).where(TenantModel.slug == slug.strip().lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[Tenant]:
        stmt = select(TenantModel).order_by(TenantModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    # ── Mapping helpers ────────────────────────────────────────────
    @staticmethod
    def _to_model(tenant: Tenant) -> TenantModel:
        return TenantModel(
            id=tenant.id,
            name=tenant.name,
            slug=tenant.slug,
            status=tenant.status.value,
            created_at=tenant.created_at,
            updated_at=tenant.updated_at,
        )

    @staticmethod
    def _to_entity(model: TenantModel) -> Tenant:
        return Tenant(
            id=model.id,
            name=model.name,
            slug=model.slug,
            status=TenantStatus(model.status),
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
