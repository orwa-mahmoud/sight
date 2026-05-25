"""Unit tests for channel notification adapter — WhatsApp/Telegram send with mocked httpx."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.channels.notification_adapter import ChannelNotificationAdapter


def _config(wa_token="", wa_phone="", tg_token=""):
    c = MagicMock()
    c.whatsapp_access_token = wa_token
    c.whatsapp_phone_number_id = wa_phone
    c.telegram_bot_token = tg_token
    return c


@pytest.mark.asyncio
@patch("src.infrastructure.channels.notification_adapter.httpx.AsyncClient")
async def test_whatsapp_send_success(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_cls.return_value = mock_client

    adapter = ChannelNotificationAdapter(_config(wa_token="token-123", wa_phone="phone-456"))
    result = await adapter.send_text(recipient="+9711234567", channel="whatsapp", message="Hello!")

    assert result is True
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "phone-456" in call_args[0][0]
    assert call_args[1]["headers"]["Authorization"] == "Bearer token-123"
    body = call_args[1]["json"]
    assert body["to"] == "+9711234567"
    assert body["text"]["body"] == "Hello!"


@pytest.mark.asyncio
@patch("src.infrastructure.channels.notification_adapter.httpx.AsyncClient")
async def test_whatsapp_send_exception_returns_false(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=Exception("network error"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_cls.return_value = mock_client

    adapter = ChannelNotificationAdapter(_config(wa_token="token", wa_phone="phone"))
    result = await adapter.send_text(recipient="+123", channel="whatsapp", message="test")

    assert result is False


@pytest.mark.asyncio
@patch("src.infrastructure.channels.notification_adapter.httpx.AsyncClient")
async def test_telegram_send_success(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_cls.return_value = mock_client

    adapter = ChannelNotificationAdapter(_config(tg_token="bot-token-abc"))
    result = await adapter.send_text(recipient="chat123", channel="telegram", message="Hi!")

    assert result is True
    mock_client.post.assert_called_once()
    call_args = mock_client.post.call_args
    assert "bot-token-abc" in call_args[0][0]
    body = call_args[1]["json"]
    assert body["chat_id"] == "chat123"
    assert body["text"] == "Hi!"


@pytest.mark.asyncio
@patch("src.infrastructure.channels.notification_adapter.httpx.AsyncClient")
async def test_telegram_send_exception_returns_false(mock_client_cls: MagicMock) -> None:
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=RuntimeError("timeout"))
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client_cls.return_value = mock_client

    adapter = ChannelNotificationAdapter(_config(tg_token="bot-token"))
    result = await adapter.send_text(recipient="123", channel="telegram", message="test")

    assert result is False
