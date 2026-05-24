"""PostgreSQL UserTenant repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.entities import UserTenant
from src.domain.users.value_objects import UserTenantRole
from src.infrastructure.persistence.postgres.models.user_tenant import UserTenantModel


class PostgresUserTenantRepository:
    """Concrete user-tenant join repository — implements `UserTenantRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, link: UserTenant) -> None:
        if link.is_new:
            self._session.add(self._to_model(link))
            link.mark_persisted()
            return
        model = await self._session.get(UserTenantModel, link.id)
        if model is None:
            self._session.add(self._to_model(link))
            return
        model.role = link.role.value

    async def list_for_user(self, user_id: UUID) -> list[UserTenant]:
        stmt = select(UserTenantModel).where(UserTenantModel.user_id == user_id).order_by(UserTenantModel.joined_at)
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get(self, user_id: UUID, tenant_id: UUID) -> UserTenant | None:
        stmt = select(UserTenantModel).where(
            UserTenantModel.user_id == user_id,
            UserTenantModel.tenant_id == tenant_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    # ── Mapping helpers ────────────────────────────────────────────
    @staticmethod
    def _to_model(link: UserTenant) -> UserTenantModel:
        return UserTenantModel(
            id=link.id,
            user_id=link.user_id,
            tenant_id=link.tenant_id,
            role=link.role.value,
            joined_at=link.joined_at,
        )

    @staticmethod
    def _to_entity(model: UserTenantModel) -> UserTenant:
        return UserTenant(
            id=model.id,
            user_id=model.user_id,
            tenant_id=model.tenant_id,
            role=UserTenantRole(model.role),
            joined_at=model.joined_at,
        )
