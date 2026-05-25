"""Unit tests for the Telegram webhook handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ai.types import ChatResult
from src.domain.tenant_config.entities import TenantConfig
from src.drivers.api.webhooks.telegram import _send_telegram_reply, telegram_webhook


def _make_config(
    *,
    tenant_id=None,
    bot_token: str | None = "bot123",
    webhook_secret: str | None = "secret-abc",
) -> TenantConfig:
    """Build a minimal TenantConfig for testing."""
    cfg = TenantConfig.create_default(tenant_id=tenant_id or uuid4())
    cfg.telegram_bot_token = bot_token
    cfg.telegram_webhook_secret = webhook_secret
    return cfg


def _telegram_body(text: str = "hello", user_id: int = 42, chat_id: int = 99) -> dict:
    return {
        "message": {
            "from": {"id": user_id, "first_name": "Ali"},
            "chat": {"id": chat_id},
            "text": text,
        }
    }


@pytest.mark.asyncio
async def test_telegram_webhook_invalid_tenant_id() -> None:
    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body())
    resp = await telegram_webhook(tenant_id="not-a-uuid", request=request)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_telegram_webhook_no_message() -> None:
    request = MagicMock()
    request.json = AsyncMock(return_value={"update_id": 123})
    tid = str(uuid4())
    resp = await telegram_webhook(tenant_id=tid, request=request)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_telegram_webhook_empty_text() -> None:
    body = _telegram_body(text="")
    request = MagicMock()
    request.json = AsyncMock(return_value=body)
    tid = str(uuid4())
    resp = await telegram_webhook(tenant_id=tid, request=request)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_telegram_webhook_no_config_returns_404() -> None:
    tid = uuid4()
    mock_session = AsyncMock()
    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=None)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body())

    async def fake_get_session():
        yield mock_session

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
    ):
        resp = await telegram_webhook(
            tenant_id=str(tid),
            request=request,
            x_telegram_bot_api_secret_token="secret",
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_telegram_webhook_invalid_secret_returns_403() -> None:
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret="correct-secret")

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body())

    async def fake_get_session():
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
    ):
        resp = await telegram_webhook(
            tenant_id=str(tid),
            request=request,
            x_telegram_bot_api_secret_token="wrong-secret",
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_telegram_webhook_happy_path_with_reply() -> None:
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret="sec", bot_token="bot-tok-123")

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    chat_result = ChatResult(response="Hi there!", thread_id="t1", escalated=False, request_id="r1")

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body(chat_id=99))

    async def fake_get_session():
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch(
            "src.drivers.api.webhooks.telegram.chat_with_agent",
            new_callable=AsyncMock,
            return_value=chat_result,
        ),
        patch(
            "src.drivers.api.webhooks.telegram._send_telegram_reply",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        resp = await telegram_webhook(
            tenant_id=str(tid),
            request=request,
            x_telegram_bot_api_secret_token="sec",
        )
    assert resp.status_code == 200
    mock_send.assert_awaited_once_with(chat_id=99, text="Hi there!", bot_token="bot-tok-123")


@pytest.mark.asyncio
async def test_telegram_webhook_exception_rolls_back() -> None:
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret=None)

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body())

    async def fake_get_session():
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch(
            "src.drivers.api.webhooks.telegram.chat_with_agent",
            new_callable=AsyncMock,
            side_effect=RuntimeError("LLM down"),
        ),
    ):
        resp = await telegram_webhook(
            tenant_id=str(tid),
            request=request,
        )
    assert resp.status_code == 200
    mock_uow.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_telegram_reply_success() -> None:
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        await _send_telegram_reply(chat_id=42, text="hi", bot_token="tok123")
        mock_client.post.assert_awaited_once()
        call_args = mock_client.post.call_args
        assert "tok123" in call_args[0][0]
        assert call_args[1]["json"]["chat_id"] == 42


@pytest.mark.asyncio
async def test_send_telegram_reply_handles_error() -> None:
    with patch("httpx.AsyncClient") as mock_cls:
        mock_client = AsyncMock()
        mock_client.post.side_effect = RuntimeError("network error")
        mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)
        # Should not raise
        await _send_telegram_reply(chat_id=42, text="hi", bot_token="tok")
