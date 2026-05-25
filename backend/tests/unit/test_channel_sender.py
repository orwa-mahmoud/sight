"""Unit tests for send_to_recipient — routes messages to WhatsApp or Telegram.

Mocks the cached adapter pool (get_whatsapp_adapter, get_telegram_adapter)
to avoid real HTTP calls.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.notifications.channel_sender import send_to_recipient
from src.infrastructure.notifications.context_loader import RecipientInfo


def _recipient(
    *,
    phone: str | None = "+971501234567",
    telegram_user_id: str | None = None,
) -> RecipientInfo:
    return RecipientInfo(
        id="rec-1",
        name="Test User",
        phone=phone,
        telegram_user_id=telegram_user_id,
    )


def _tenant_config(
    *,
    tenant_id: str = "t-1",
    whatsapp_phone_number_id: str = "wpn-1",
    whatsapp_access_token: str = "tok-wa",
) -> MagicMock:
    cfg = MagicMock()
    cfg.tenant_id = tenant_id
    cfg.whatsapp_phone_number_id = whatsapp_phone_number_id
    cfg.whatsapp_access_token = whatsapp_access_token
    return cfg


# ---------------------------------------------------------------------------
# WhatsApp channel
# ---------------------------------------------------------------------------


class TestSendWhatsApp:
    @pytest.mark.asyncio
    @patch("src.infrastructure.notifications.channel_sender.get_whatsapp_adapter")
    async def test_sends_whatsapp_text(self, mock_get_wa: AsyncMock) -> None:
        wa_adapter = AsyncMock()
        mock_get_wa.return_value = wa_adapter

        recipient = _recipient(phone="+123")
        config = _tenant_config()

        result = await send_to_recipient(recipient, "Hello", "whatsapp", config)

        assert result is True
        mock_get_wa.assert_awaited_once_with(
            "t-1",
            phone_number_id="wpn-1",
            access_token="tok-wa",
        )
        wa_adapter.send_text.assert_awaited_once_with("+123", "Hello")

    @pytest.mark.asyncio
    @patch("src.infrastructure.notifications.channel_sender.get_whatsapp_adapter")
    async def test_whatsapp_skipped_when_no_phone(self, mock_get_wa: AsyncMock) -> None:
        """Channel is whatsapp but recipient has no phone -> falls through to api_only."""
        recipient = _recipient(phone=None)
        config = _tenant_config()

        result = await send_to_recipient(recipient, "Hello", "whatsapp", config)

        assert result is True  # api_only returns True
        mock_get_wa.assert_not_awaited()


# ---------------------------------------------------------------------------
# Telegram channel
# ---------------------------------------------------------------------------


class TestSendTelegram:
    @pytest.mark.asyncio
    @patch("src.infrastructure.notifications.channel_sender.get_telegram_adapter")
    async def test_sends_telegram_via_telegram_user_id(self, mock_get_tg: AsyncMock) -> None:
        tg_adapter = AsyncMock()
        mock_get_tg.return_value = tg_adapter

        recipient = _recipient(phone=None, telegram_user_id="tg_42")
        config = _tenant_config()

        result = await send_to_recipient(recipient, "Hi TG", "telegram", config)

        assert result is True
        mock_get_tg.assert_awaited_once_with("t-1", tenant_config=config)
        tg_adapter.send_text.assert_awaited_once_with("tg_42", "Hi TG")

    @pytest.mark.asyncio
    @patch("src.infrastructure.notifications.channel_sender.get_telegram_adapter")
    async def test_sends_telegram_falls_back_to_phone(self, mock_get_tg: AsyncMock) -> None:
        """When telegram_user_id is None, phone is used as the tg_recipient."""
        tg_adapter = AsyncMock()
        mock_get_tg.return_value = tg_adapter

        recipient = _recipient(phone="+777", telegram_user_id=None)
        config = _tenant_config()

        result = await send_to_recipient(recipient, "Hi TG", "telegram", config)

        assert result is True
        tg_adapter.send_text.assert_awaited_once_with("+777", "Hi TG")

    @pytest.mark.asyncio
    @patch("src.infrastructure.notifications.channel_sender.get_telegram_adapter")
    async def test_telegram_no_identifier_falls_through(self, mock_get_tg: AsyncMock) -> None:
        """No telegram_user_id and no phone -> api_only path."""
        recipient = _recipient(phone=None, telegram_user_id=None)
        config = _tenant_config()

        result = await send_to_recipient(recipient, "Hi", "telegram", config)

        assert result is True
        mock_get_tg.assert_not_awaited()


# ---------------------------------------------------------------------------
# api_only fallback + error handling
# ---------------------------------------------------------------------------


class TestApiOnlyAndErrors:
    @pytest.mark.asyncio
    async def test_unknown_channel_returns_true(self) -> None:
        """Unknown channel (e.g. 'api') skips both blocks -> api_only."""
        recipient = _recipient()
        config = _tenant_config()
        result = await send_to_recipient(recipient, "msg", "api", config)
        assert result is True

    @pytest.mark.asyncio
    @patch("src.infrastructure.notifications.channel_sender.get_whatsapp_adapter")
    async def test_adapter_exception_returns_false(self, mock_get_wa: AsyncMock) -> None:
        """Any exception during delivery -> returns False (logged, not raised)."""
        mock_get_wa.side_effect = RuntimeError("connection failed")

        recipient = _recipient(phone="+123")
        config = _tenant_config()

        result = await send_to_recipient(recipient, "msg", "whatsapp", config)

        assert result is False

    @pytest.mark.asyncio
    @patch("src.infrastructure.notifications.channel_sender.get_whatsapp_adapter")
    async def test_send_text_exception_returns_false(self, mock_get_wa: AsyncMock) -> None:
        """Exception inside send_text -> returns False."""
        wa_adapter = AsyncMock()
        wa_adapter.send_text.side_effect = RuntimeError("API error")
        mock_get_wa.return_value = wa_adapter

        recipient = _recipient(phone="+123")
        config = _tenant_config()

        result = await send_to_recipient(recipient, "msg", "whatsapp", config)

        assert result is False
