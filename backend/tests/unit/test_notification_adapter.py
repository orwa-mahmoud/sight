"""Unit tests for channel notification adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.channels.notification_adapter import ChannelNotificationAdapter


def _config(wa_token="", wa_phone="", tg_token=""):
    c = MagicMock()
    c.whatsapp_access_token = wa_token
    c.whatsapp_phone_number_id = wa_phone
    c.telegram_bot_token = tg_token
    return c


@pytest.mark.asyncio
async def test_unsupported_channel():
    adapter = ChannelNotificationAdapter(_config())
    result = await adapter.send_text(recipient="x", channel="email", message="hi")
    assert result is False


@pytest.mark.asyncio
async def test_whatsapp_not_configured():
    adapter = ChannelNotificationAdapter(_config())
    result = await adapter.send_text(recipient="+123", channel="whatsapp", message="hi")
    assert result is False


@pytest.mark.asyncio
async def test_telegram_not_configured():
    adapter = ChannelNotificationAdapter(_config())
    result = await adapter.send_text(recipient="123", channel="telegram", message="hi")
    assert result is False
