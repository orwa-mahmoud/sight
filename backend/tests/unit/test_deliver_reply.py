"""Unit tests for _deliver_reply in questions routes."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest

from src.application.questions.dtos import QuestionDTO
from src.drivers.api.v1.questions.routes import _deliver_reply


def _make_dto(
    *,
    owner_reply: str | None = "Thanks!",
    contact_id: UUID | None = None,
    channel: str | None = "whatsapp",
    tenant_id: UUID | None = None,
) -> QuestionDTO:
    return QuestionDTO(
        id=uuid4(),
        conversation_id=uuid4(),
        channel=channel or "",
        contact_id=contact_id,
        question_text="Help?",
        ai_answer_attempt="Trying...",
        status="resolved",
        owner_reply=owner_reply,
        replied_by_user_id=uuid4(),
        replied_at=None,
        created_at=None,  # type: ignore[arg-type]
        updated_at=None,  # type: ignore[arg-type]
        tenant_id=tenant_id or uuid4(),
    )


@pytest.mark.asyncio
async def test_deliver_reply_no_reply_returns_early() -> None:
    dto = _make_dto(owner_reply=None)
    uow = MagicMock()
    await _deliver_reply(dto, uow)
    uow.contacts.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_reply_no_contact_returns_early() -> None:
    dto = _make_dto(contact_id=None)
    uow = MagicMock()
    await _deliver_reply(dto, uow)
    uow.contacts.get_by_id.assert_not_called()


@pytest.mark.asyncio
async def test_deliver_reply_whatsapp_sends() -> None:
    tid = uuid4()
    cid = uuid4()
    dto = _make_dto(contact_id=cid, channel="whatsapp", tenant_id=tid)

    contact = MagicMock()
    contact.phone = "+971501234567"
    contact.tenant_id = tid
    config = MagicMock()
    config.whatsapp_access_token = "token"
    config.telegram_bot_token = None

    uow = MagicMock()
    uow.contacts.get_by_id = AsyncMock(return_value=contact)
    uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)

    with patch("src.drivers.api.v1.questions.routes.get_whatsapp_adapter") as mock_get_wa:
        wa_instance = AsyncMock()
        mock_get_wa.return_value = wa_instance
        await _deliver_reply(dto, uow)
        wa_instance.send_text.assert_awaited_once_with("+971501234567", "Thanks!")


@pytest.mark.asyncio
async def test_deliver_reply_telegram_sends() -> None:
    tid = uuid4()
    cid = uuid4()
    dto = _make_dto(contact_id=cid, channel="telegram", tenant_id=tid)

    contact = MagicMock()
    contact.phone = "+971501234567"
    contact.telegram_user_id = "123456789"
    contact.tenant_id = tid
    config = MagicMock()
    config.whatsapp_access_token = None
    config.telegram_bot_token = "bot-token"

    uow = MagicMock()
    uow.contacts.get_by_id = AsyncMock(return_value=contact)
    uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=config)

    with patch("src.drivers.api.v1.questions.routes.get_telegram_adapter") as mock_get_tg:
        tg_instance = AsyncMock()
        mock_get_tg.return_value = tg_instance
        await _deliver_reply(dto, uow)
        tg_instance.send_text.assert_awaited_once()


@pytest.mark.asyncio
async def test_deliver_reply_exception_caught() -> None:
    tid = uuid4()
    cid = uuid4()
    dto = _make_dto(contact_id=cid, channel="whatsapp", tenant_id=tid)

    uow = MagicMock()
    uow.contacts.get_by_id = AsyncMock(side_effect=RuntimeError("db down"))

    await _deliver_reply(dto, uow)


@pytest.mark.asyncio
async def test_deliver_reply_foreign_tenant_contact_not_delivered() -> None:
    """A reply must never be sent to a contact owned by a different tenant."""
    dto = _make_dto(contact_id=uuid4(), channel="whatsapp", tenant_id=uuid4())

    contact = MagicMock()
    contact.phone = "+971501234567"
    contact.tenant_id = uuid4()  # belongs to a DIFFERENT tenant than the DTO

    uow = MagicMock()
    uow.contacts.get_by_id = AsyncMock(return_value=contact)
    uow.tenant_configs.get_by_tenant_id = AsyncMock()

    with patch("src.drivers.api.v1.questions.routes.get_whatsapp_adapter") as mock_get_wa:
        await _deliver_reply(dto, uow)
        mock_get_wa.assert_not_called()  # returned early — no cross-tenant delivery
