"""Unit tests for the Telegram webhook handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.ai.types import ChatResult
from src.domain.tenant_config.entities import TenantConfig
from src.drivers.api.webhooks.telegram import _nontext_chat_id, telegram_webhook


def test_nontext_chat_id_returns_chat_for_media() -> None:
    body = {"message": {"from": {"id": 1}, "chat": {"id": 99}, "voice": {"file_id": "x"}}}
    assert _nontext_chat_id(body) == "99"


def test_nontext_chat_id_none_for_text_message() -> None:
    assert _nontext_chat_id({"message": {"chat": {"id": 99}, "text": "hi"}}) is None


def test_nontext_chat_id_none_for_empty_or_service_message() -> None:
    # Empty text / no recognized content (e.g. a service message) — don't reply.
    assert _nontext_chat_id({"message": {"chat": {"id": 99}, "text": ""}}) is None
    assert _nontext_chat_id({"message": {"chat": {"id": 99}, "new_chat_member": {}}}) is None
    assert _nontext_chat_id({}) is None


def _make_config(
    *,
    tenant_id: UUID | None = None,
    bot_token: str | None = "bot123",
    webhook_secret: str | None = "secret-abc",
) -> TenantConfig:
    cfg = TenantConfig.create_default(tenant_id=tenant_id or uuid4())
    cfg.telegram_bot_token = bot_token
    cfg.telegram_webhook_secret = webhook_secret
    return cfg


def _telegram_body(text: str = "hello", user_id: int = 42, chat_id: int = 99) -> dict[str, object]:
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
    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=None)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body())

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

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

    async def fake_get_session():  # type: ignore[no-untyped-def]
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

    async def fake_get_session():  # type: ignore[no-untyped-def]
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
            "src.infrastructure.channels.telegram.TelegramAdapter.send_text",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        resp = await telegram_webhook(
            tenant_id=str(tid),
            request=request,
            x_telegram_bot_api_secret_token="sec",
        )
    assert resp.status_code == 200
    mock_send.assert_awaited_once_with("99", "Hi there!")


@pytest.mark.asyncio
async def test_telegram_webhook_skips_duplicate_delivery() -> None:
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret="sec", bot_token="bot-tok-123")

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body(chat_id=99))

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch(
            "src.drivers.api.webhooks.telegram.is_duplicate_message",
            new_callable=AsyncMock,
            return_value=True,
        ),
        patch("src.drivers.api.webhooks.telegram.chat_with_agent", new_callable=AsyncMock) as mock_chat,
    ):
        resp = await telegram_webhook(
            tenant_id=str(tid),
            request=request,
            x_telegram_bot_api_secret_token="sec",
        )

    # A duplicate is acknowledged (200) but never reprocessed or re-billed.
    assert resp.status_code == 200
    mock_chat.assert_not_called()


@pytest.mark.asyncio
async def test_telegram_webhook_acknowledges_non_text_message() -> None:
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret="sec", bot_token="bot-tok-123")

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    request = MagicMock()
    # A voice message — no text.
    request.json = AsyncMock(
        return_value={"message": {"from": {"id": 1}, "chat": {"id": 99}, "voice": {"file_id": "x"}}}
    )

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch("src.drivers.api.webhooks.telegram.chat_with_agent", new_callable=AsyncMock) as mock_chat,
        patch(
            "src.infrastructure.channels.telegram.TelegramAdapter.send_text",
            new_callable=AsyncMock,
        ) as mock_send,
    ):
        resp = await telegram_webhook(
            tenant_id=str(tid),
            request=request,
            x_telegram_bot_api_secret_token="sec",
        )

    # Non-text content is acknowledged with a text-only notice, not run through the agent.
    assert resp.status_code == 200
    mock_chat.assert_not_called()
    mock_send.assert_awaited_once()
    call = mock_send.await_args
    assert call is not None
    assert "text" in call.args[1].lower()


@pytest.mark.asyncio
async def test_telegram_webhook_exception_rolls_back() -> None:
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret="test-sec")

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body())

    async def fake_get_session():  # type: ignore[no-untyped-def]
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
            x_telegram_bot_api_secret_token="test-sec",
        )
    assert resp.status_code == 200
    mock_uow.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_adapter_send_text_no_token() -> None:
    from src.infrastructure.channels.telegram import TelegramAdapter

    adapter = TelegramAdapter()
    result = await adapter.send_text("123", "hello")
    assert result is None
