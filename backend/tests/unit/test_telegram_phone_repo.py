"""Unit tests for PostgresTelegramPhoneRepository — get_or_register, set_phone.

Mocks AsyncSession. The repo uses PostgreSQL-specific INSERT ON CONFLICT,
so we verify that session.execute and session.flush are called correctly.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.infrastructure.persistence.postgres.repositories.telegram_phone_repo import (
    PostgresTelegramPhoneRepository,
)

# ---------------------------------------------------------------------------
# get_or_register
# ---------------------------------------------------------------------------


class TestGetOrRegister:
    @pytest.mark.asyncio
    async def test_registers_and_returns_phone_when_row_exists(self) -> None:
        """Row already exists -> returns the stored phone."""
        row = MagicMock(phone="+971501234567")

        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.get = AsyncMock(return_value=row)

        repo = PostgresTelegramPhoneRepository(session)
        phone = await repo.get_or_register("tg_123")

        assert phone == "+971501234567"
        session.execute.assert_awaited_once()  # the INSERT ON CONFLICT
        session.flush.assert_awaited_once()
        session.get.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_registers_and_returns_none_when_no_phone(self) -> None:
        """New registration -> phone is None."""
        row = MagicMock(phone=None)

        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.get = AsyncMock(return_value=row)

        repo = PostgresTelegramPhoneRepository(session)
        phone = await repo.get_or_register("tg_new")

        assert phone is None

    @pytest.mark.asyncio
    async def test_returns_none_when_row_not_found(self) -> None:
        """Edge case: get returns None (should not normally happen)."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()
        session.get = AsyncMock(return_value=None)

        repo = PostgresTelegramPhoneRepository(session)
        phone = await repo.get_or_register("tg_ghost")

        assert phone is None


# ---------------------------------------------------------------------------
# set_phone
# ---------------------------------------------------------------------------


class TestSetPhone:
    @pytest.mark.asyncio
    async def test_executes_upsert_and_flushes(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()

        repo = PostgresTelegramPhoneRepository(session)
        await repo.set_phone("tg_42", "+1234567890")

        session.execute.assert_awaited_once()
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_can_be_called_multiple_times(self) -> None:
        """set_phone is idempotent — upsert semantics."""
        session = AsyncMock()
        session.execute = AsyncMock()
        session.flush = AsyncMock()

        repo = PostgresTelegramPhoneRepository(session)
        await repo.set_phone("tg_42", "+111")
        await repo.set_phone("tg_42", "+222")

        assert session.execute.await_count == 2
        assert session.flush.await_count == 2
