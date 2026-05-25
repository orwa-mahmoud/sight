"""PostgreSQL implementation of TelegramPhoneRepository."""

from __future__ import annotations

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.models.telegram_phone import TelegramPhoneModel


class PostgresTelegramPhoneRepository:
    """PostgreSQL implementation — telegram_user_id -> phone lookup."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_register(self, telegram_user_id: str) -> str | None:
        """INSERT ON CONFLICT DO NOTHING, then read back.  Idempotent registration."""
        stmt = insert(TelegramPhoneModel).values(telegram_user_id=telegram_user_id, phone=None).on_conflict_do_nothing()
        await self._session.execute(stmt)
        await self._session.flush()

        row = await self._session.get(TelegramPhoneModel, telegram_user_id)
        return row.phone if row else None

    async def set_phone(self, telegram_user_id: str, phone: str) -> None:
        stmt = (
            insert(TelegramPhoneModel)
            .values(telegram_user_id=telegram_user_id, phone=phone)
            .on_conflict_do_update(
                index_elements=["telegram_user_id"],
                set_={"phone": phone},
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
