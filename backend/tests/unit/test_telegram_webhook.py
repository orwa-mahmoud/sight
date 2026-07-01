"""Unit tests for the Telegram webhook handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.ai.types import ChatResult
from src.domain.tenant_config.entities import TenantConfig
from src.drivers.api.webhooks.telegram import _nontext_ids, _parse_telegram_contact, telegram_webhook


def test_nontext_ids_returns_chat_and_message_id_for_media() -> None:
    body = {"message": {"message_id": 5, "from": {"id": 1}, "chat": {"id": 99}, "voice": {"file_id": "x"}}}
    assert _nontext_ids(body) == ("99", "99:5")


def test_nontext_ids_none_for_text_message() -> None:
    assert _nontext_ids({"message": {"chat": {"id": 99}, "text": "hi"}}) is None


def test_nontext_ids_none_for_empty_or_service_message() -> None:
    # Empty text / no recognized content (e.g. a service message) — don't reply.
    assert _nontext_ids({"message": {"chat": {"id": 99}, "text": ""}}) is None
    assert _nontext_ids({"message": {"chat": {"id": 99}, "new_chat_member": {}}}) is None
    assert _nontext_ids({}) is None


def test_parse_contact_accepts_own_shared_number() -> None:
    body = {
        "message": {
            "message_id": 5,
            "from": {"id": 42},
            "chat": {"id": 99},
            "contact": {"phone_number": "+971500000000", "user_id": 42},
        }
    }
    assert _parse_telegram_contact(body) == ("42", "+971500000000", "99", "99:5")


def test_parse_contact_rejects_someone_elses_card() -> None:
    # A contact whose user_id != sender id is a forwarded third-party card — never
    # bind another person's number to this user.
    body = {
        "message": {
            "message_id": 5,
            "from": {"id": 42},
            "chat": {"id": 99},
            "contact": {"phone_number": "+971500000000", "user_id": 999},
        }
    }
    assert _parse_telegram_contact(body) is None


def test_parse_contact_none_for_text_or_missing_phone() -> None:
    assert _parse_telegram_contact({"message": {"from": {"id": 1}, "text": "hi"}}) is None
    assert _parse_telegram_contact({"message": {"from": {"id": 1}, "contact": {"user_id": 1}}}) is None


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
async def test_telegram_webhook_malformed_body_returns_400() -> None:
    request = MagicMock()
    request.json = AsyncMock(side_effect=ValueError("not json"))  # malformed body
    resp = await telegram_webhook(tenant_id=str(uuid4()), request=request)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_telegram_webhook_non_dict_body_returns_400() -> None:
    request = MagicMock()
    request.json = AsyncMock(return_value=["not", "a", "dict"])  # valid JSON, wrong shape
    resp = await telegram_webhook(tenant_id=str(uuid4()), request=request)
    assert resp.status_code == 400


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
    mock_uow.tenants = MagicMock()
    mock_uow.tenants.get_by_id = AsyncMock(return_value=None)

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
    mock_uow.tenants = MagicMock()
    mock_uow.tenants.get_by_id = AsyncMock(return_value=None)

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
    mock_uow.tenants = MagicMock()
    mock_uow.tenants.get_by_id = AsyncMock(return_value=None)
    mock_uow.telegram_phones = MagicMock()
    mock_uow.telegram_phones.get_phone = AsyncMock(return_value="+971500000000")  # already linked → no prompt

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
    mock_uow.tenants = MagicMock()
    mock_uow.tenants.get_by_id = AsyncMock(return_value=None)

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body(chat_id=99))

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch(
            "src.drivers.api.webhooks.telegram.was_message_processed",
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
    mock_uow.tenants = MagicMock()
    mock_uow.tenants.get_by_id = AsyncMock(return_value=None)

    request = MagicMock()
    # A voice message — no text.
    request.json = AsyncMock(
        return_value={"message": {"message_id": 7, "from": {"id": 1}, "chat": {"id": 99}, "voice": {"file_id": "x"}}}
    )

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch("src.drivers.api.webhooks.telegram.chat_with_agent", new_callable=AsyncMock) as mock_chat,
        patch(
            "src.drivers.api.webhooks.telegram.was_message_processed",
            new_callable=AsyncMock,
            return_value=False,
        ),
        patch("src.drivers.api.webhooks.telegram.mark_message_processed", new_callable=AsyncMock) as mock_mark,
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

    # Non-text content is acknowledged with a text-only notice, not run through the
    # agent, and de-duplicated (marked processed) so a redelivery isn't answered twice.
    assert resp.status_code == 200
    mock_chat.assert_not_called()
    mock_send.assert_awaited_once()
    call = mock_send.await_args
    assert call is not None
    assert "text" in call.args[1].lower()
    mock_mark.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_webhook_exception_rolls_back() -> None:
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret="test-sec")

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()
    mock_uow.tenants = MagicMock()
    mock_uow.tenants.get_by_id = AsyncMock(return_value=None)

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body())

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch("src.drivers.api.webhooks.telegram.was_message_processed", new_callable=AsyncMock, return_value=False),
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
    # A processing failure asks Telegram to redeliver (503) rather than acking a
    # lost reply, and the transaction is rolled back.
    assert resp.status_code == 503
    mock_uow.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_telegram_webhook_saves_shared_contact_phone() -> None:
    """A shared-contact message persists the phone and acknowledges (keyboard removed)."""
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret="sec", bot_token="bot-tok-123")

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()
    mock_uow.tenants = MagicMock()
    mock_uow.tenants.get_by_id = AsyncMock(return_value=None)
    mock_uow.telegram_phones = MagicMock()
    mock_uow.telegram_phones.set_phone = AsyncMock()

    request = MagicMock()
    request.json = AsyncMock(
        return_value={
            "message": {
                "message_id": 7,
                "from": {"id": 42},
                "chat": {"id": 99},
                "contact": {"phone_number": "+971500000000", "user_id": 42},
            }
        }
    )

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch("src.drivers.api.webhooks.telegram.was_message_processed", new_callable=AsyncMock, return_value=False),
        patch("src.drivers.api.webhooks.telegram.mark_message_processed", new_callable=AsyncMock),
        patch("src.drivers.api.webhooks.telegram.chat_with_agent", new_callable=AsyncMock) as mock_chat,
        patch("src.infrastructure.channels.telegram.TelegramAdapter.send_text", new_callable=AsyncMock) as mock_send,
    ):
        resp = await telegram_webhook(tenant_id=str(tid), request=request, x_telegram_bot_api_secret_token="sec")

    assert resp.status_code == 200
    mock_uow.telegram_phones.set_phone.assert_awaited_once_with("42", "+971500000000")
    mock_chat.assert_not_called()  # a contact share is not an agent turn
    # Acknowledged, and the request_contact keyboard removed.
    call = mock_send.await_args
    assert call is not None
    assert call.kwargs.get("remove_keyboard") is True


@pytest.mark.asyncio
async def test_telegram_webhook_prompts_for_phone_when_unlinked() -> None:
    """An unresolved user (no stored phone) gets the reply AND the share-phone prompt."""
    tid = uuid4()
    config = _make_config(tenant_id=tid, webhook_secret="sec", bot_token="bot-tok-123")

    mock_uow = MagicMock()
    mock_uow.tenant_configs = MagicMock()
    mock_uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)
    mock_uow.commit = AsyncMock()
    mock_uow.rollback = AsyncMock()
    mock_uow.tenants = MagicMock()
    mock_uow.tenants.get_by_id = AsyncMock(return_value=None)
    mock_uow.telegram_phones = MagicMock()
    mock_uow.telegram_phones.get_phone = AsyncMock(return_value=None)  # not linked yet

    request = MagicMock()
    request.json = AsyncMock(return_value=_telegram_body(chat_id=99))
    chat_result = ChatResult(response="Answer.", thread_id="t1", escalated=False, request_id="r1")

    async def fake_get_session():  # type: ignore[no-untyped-def]
        yield AsyncMock()

    with (
        patch("src.drivers.api.webhooks.telegram.get_session", fake_get_session),
        patch("src.drivers.api.webhooks.telegram.UnitOfWork", return_value=mock_uow),
        patch("src.drivers.api.webhooks.telegram.was_message_processed", new_callable=AsyncMock, return_value=False),
        patch("src.drivers.api.webhooks.telegram.mark_message_processed", new_callable=AsyncMock),
        patch("src.drivers.api.webhooks.telegram.chat_with_agent", new_callable=AsyncMock, return_value=chat_result),
        patch("src.infrastructure.channels.telegram.TelegramAdapter.send_text", new_callable=AsyncMock),
        patch(
            "src.infrastructure.channels.telegram.TelegramAdapter.send_contact_request", new_callable=AsyncMock
        ) as mock_prompt,
    ):
        resp = await telegram_webhook(tenant_id=str(tid), request=request, x_telegram_bot_api_secret_token="sec")

    assert resp.status_code == 200
    mock_prompt.assert_awaited_once()  # the share-phone button was offered


@pytest.mark.asyncio
async def test_telegram_adapter_send_text_no_token() -> None:
    from src.infrastructure.channels.telegram import TelegramAdapter

    adapter = TelegramAdapter()
    result = await adapter.send_text("123", "hello")
    assert result is None
