"""Telegram phone lookup — repository port."""

from __future__ import annotations

from typing import Protocol


class TelegramPhoneRepository(Protocol):
    """Port for telegram_user_id -> phone lookup table."""

    async def get_or_register(self, telegram_user_id: str) -> str | None:
        """Get phone for a telegram_user_id.

        If not found, insert with phone=NULL.  Returns phone or None.
        """
        ...

    async def set_phone(self, telegram_user_id: str, phone: str) -> None:
        """Set/update phone for a telegram_user_id (contact shared)."""
        ...
