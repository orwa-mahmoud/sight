"""PostgreSQL User repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.users.entities import User
from src.infrastructure.persistence.postgres.models.user import UserModel


class PostgresUserRepository:
    """Concrete user repository — implements the `UserRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, user: User) -> None:
        if user.is_new:
            self._session.add(self._to_model(user))
            user.mark_persisted()
            return
        model = await self._session.get(UserModel, user.id)
        if model is None:
            self._session.add(self._to_model(user))
            return
        model.email = user.email
        model.hashed_password = user.hashed_password
        model.full_name = user.full_name
        model.is_active = user.is_active
        model.is_platform_admin = user.is_platform_admin
        model.updated_at = user.updated_at

    async def get_by_id(self, user_id: UUID) -> User | None:
        model = await self._session.get(UserModel, user_id)
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(UserModel).where(UserModel.email == email.strip().lower())
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_all(self) -> list[User]:
        stmt = select(UserModel).order_by(UserModel.created_at.desc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    # ── Mapping helpers ────────────────────────────────────────────
    @staticmethod
    def _to_model(user: User) -> UserModel:
        return UserModel(
            id=user.id,
            email=user.email,
            hashed_password=user.hashed_password,
            full_name=user.full_name,
            is_active=user.is_active,
            is_platform_admin=user.is_platform_admin,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    @staticmethod
    def _to_entity(model: UserModel) -> User:
        return User(
            id=model.id,
            email=model.email,
            hashed_password=model.hashed_password,
            full_name=model.full_name,
            is_active=model.is_active,
            is_platform_admin=model.is_platform_admin,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
