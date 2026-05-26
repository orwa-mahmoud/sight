"""Unit tests for NotificationRoutingAdapter — 4-step fallback chain.

Mocks the async DB session to verify each fallback step independently.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.domain.notifications.ports import NotificationRoutingError
from src.infrastructure.notifications.routing import NotificationRoutingAdapter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_session_factory(session: AsyncMock) -> MagicMock:
    """Return an async_sessionmaker mock that yields *session* as a context manager."""
    factory = MagicMock()
    ctx = AsyncMock()
    ctx.__aenter__.return_value = session
    ctx.__aexit__.return_value = False
    factory.return_value = ctx
    return factory


def _scalar_result(value: object) -> AsyncMock:
    """Wrap a value in a Result mock with .scalar_one_or_none()."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


# ---------------------------------------------------------------------------
# _load_recipient_contact
# ---------------------------------------------------------------------------


class TestLoadRecipientContact:
    """Tests for _load_recipient_contact — resolves phone + telegram_user_id."""

    @pytest.mark.asyncio
    async def test_user_recipient_returns_phone_and_telegram(self) -> None:
        user = MagicMock(phone="+1234567890", telegram_user_id="tg_123")
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(user))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        phone, tg_uid = await adapter._load_recipient_contact(session, uuid4(), "owner", uuid4())

        assert phone == "+1234567890"
        assert tg_uid == "tg_123"

    @pytest.mark.asyncio
    async def test_user_recipient_not_found_raises(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        with pytest.raises(NotificationRoutingError, match=r"User .* not found"):
            await adapter._load_recipient_contact(session, uuid4(), "user", uuid4())

    @pytest.mark.asyncio
    async def test_contact_recipient_returns_phone_and_telegram(self) -> None:
        contact = MagicMock(phone="+9876543210", telegram_user_id="tg_456")
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(contact))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        phone, tg_uid = await adapter._load_recipient_contact(session, uuid4(), "contact", uuid4())

        assert phone == "+9876543210"
        assert tg_uid == "tg_456"

    @pytest.mark.asyncio
    async def test_contact_not_found_raises(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        with pytest.raises(NotificationRoutingError, match=r"Contact .* not found"):
            await adapter._load_recipient_contact(session, uuid4(), "contact", uuid4())


# ---------------------------------------------------------------------------
# _try_existing_conversation (Step 1)
# ---------------------------------------------------------------------------


class TestTryExistingConversation:
    @pytest.mark.asyncio
    async def test_returns_route_when_conversation_found(self) -> None:
        tenant_id = uuid4()
        participant_id = uuid4()
        conv_id = uuid4()
        conv = MagicMock(channel="whatsapp", thread_id="thread-1", id=conv_id)

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(conv))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter._try_existing_conversation(session, participant_id, tenant_id)

        assert route is not None
        assert route.channel == "whatsapp"
        assert route.thread_id == "thread-1"
        assert route.conversation_id == conv_id
        assert route.tenant_id == tenant_id
        assert route.recipient_id == participant_id

    @pytest.mark.asyncio
    async def test_returns_none_when_no_conversation(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter._try_existing_conversation(session, uuid4(), uuid4())

        assert route is None


# ---------------------------------------------------------------------------
# _try_whatsapp (Step 2)
# ---------------------------------------------------------------------------


class TestTryWhatsApp:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_phone(self) -> None:
        session = AsyncMock()
        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter._try_whatsapp(session, uuid4(), uuid4(), None, "contact")
        assert route is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_tenant_config(self) -> None:
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(None))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter._try_whatsapp(session, uuid4(), uuid4(), "+123", "contact")
        assert route is None

    @pytest.mark.asyncio
    async def test_returns_none_when_whatsapp_not_configured(self) -> None:
        config = MagicMock(whatsapp_phone_number_id=None, whatsapp_access_token=None)
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(config))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter._try_whatsapp(session, uuid4(), uuid4(), "+123", "contact")
        assert route is None

    @pytest.mark.asyncio
    async def test_returns_whatsapp_route_for_contact(self) -> None:
        tenant_id = uuid4()
        recipient_id = uuid4()
        phone = "+1234567890"
        config = MagicMock(whatsapp_phone_number_id="wapn123", whatsapp_access_token="tok")

        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(config))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter._try_whatsapp(session, tenant_id, recipient_id, phone, "contact")

        assert route is not None
        assert route.channel == "whatsapp"
        assert route.thread_id == f"contact:{tenant_id}:{phone}:whatsapp"
        assert route.tenant_id == tenant_id
        assert route.recipient_id == recipient_id

    @pytest.mark.asyncio
    async def test_returns_whatsapp_route_for_user(self) -> None:
        tenant_id = uuid4()
        config = MagicMock(whatsapp_phone_number_id="wapn123", whatsapp_access_token="tok")
        session = AsyncMock()
        session.execute = AsyncMock(return_value=_scalar_result(config))

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter._try_whatsapp(session, tenant_id, uuid4(), "+555", "owner")

        assert route is not None
        assert route.thread_id == f"user:{tenant_id}:+555:whatsapp"


# ---------------------------------------------------------------------------
# _try_telegram (Step 3) — synchronous, no DB
# ---------------------------------------------------------------------------


class TestTryTelegram:
    def test_returns_none_when_no_telegram_id(self) -> None:
        adapter = NotificationRoutingAdapter(_mock_session_factory(AsyncMock()))
        route = adapter._try_telegram(uuid4(), uuid4(), None, "contact")
        assert route is None

    def test_returns_telegram_route_for_contact(self) -> None:
        tenant_id = uuid4()
        recipient_id = uuid4()
        adapter = NotificationRoutingAdapter(_mock_session_factory(AsyncMock()))
        route = adapter._try_telegram(tenant_id, recipient_id, "tg_42", "contact")

        assert route is not None
        assert route.channel == "telegram"
        assert route.thread_id == f"contact:{tenant_id}:tg_42:telegram"
        assert route.tenant_id == tenant_id
        assert route.recipient_id == recipient_id

    def test_returns_telegram_route_for_user(self) -> None:
        tenant_id = uuid4()
        adapter = NotificationRoutingAdapter(_mock_session_factory(AsyncMock()))
        route = adapter._try_telegram(tenant_id, uuid4(), "tg_99", "user")

        assert route is not None
        assert route.thread_id == f"user:{tenant_id}:tg_99:telegram"


# ---------------------------------------------------------------------------
# resolve_route — full fallback chain integration
# ---------------------------------------------------------------------------


class TestResolveRoute:
    @pytest.mark.asyncio
    async def test_step1_existing_conversation_wins(self) -> None:
        """If an existing conversation is found, it is returned immediately."""
        tenant_id = uuid4()
        recipient_id = uuid4()
        conv_id = uuid4()

        contact = MagicMock(phone="+123", telegram_user_id="tg_1")
        conv = MagicMock(channel="telegram", thread_id="conv-thread", id=conv_id)

        # First execute: _load_recipient_contact (contact lookup)
        # Second execute: _try_existing_conversation
        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[_scalar_result(contact), _scalar_result(conv)],
        )

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter.resolve_route(
            tenant_id=tenant_id,
            recipient_id=recipient_id,
            recipient_type="contact",
        )

        assert route.channel == "telegram"
        assert route.thread_id == "conv-thread"
        assert route.conversation_id == conv_id

    @pytest.mark.asyncio
    async def test_step2_whatsapp_fallback(self) -> None:
        """No conversation -> falls back to WhatsApp if configured."""
        tenant_id = uuid4()
        recipient_id = uuid4()
        contact = MagicMock(phone="+555", telegram_user_id=None)
        config = MagicMock(whatsapp_phone_number_id="wp1", whatsapp_access_token="tok")

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(contact),  # _load_recipient_contact
                _scalar_result(None),  # _try_existing_conversation (no conv)
                _scalar_result(config),  # _try_whatsapp (config lookup)
            ],
        )

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter.resolve_route(
            tenant_id=tenant_id,
            recipient_id=recipient_id,
            recipient_type="contact",
        )

        assert route.channel == "whatsapp"
        assert "whatsapp" in route.thread_id

    @pytest.mark.asyncio
    async def test_step3_telegram_fallback(self) -> None:
        """No conversation, no WhatsApp -> falls back to Telegram if recipient has tg_id."""
        tenant_id = uuid4()
        recipient_id = uuid4()
        contact = MagicMock(phone=None, telegram_user_id="tg_77")

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(contact),  # _load_recipient_contact
                _scalar_result(None),  # _try_existing_conversation (no conv)
                # _try_whatsapp skipped because phone is None
            ],
        )

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        route = await adapter.resolve_route(
            tenant_id=tenant_id,
            recipient_id=recipient_id,
            recipient_type="contact",
        )

        assert route.channel == "telegram"
        assert "telegram" in route.thread_id

    @pytest.mark.asyncio
    async def test_step4_raises_when_all_fail(self) -> None:
        """No conversation, no phone, no telegram -> NotificationRoutingError."""
        tenant_id = uuid4()
        recipient_id = uuid4()
        contact = MagicMock(phone=None, telegram_user_id=None)

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[
                _scalar_result(contact),  # _load_recipient_contact
                _scalar_result(None),  # _try_existing_conversation
            ],
        )

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        with pytest.raises(NotificationRoutingError, match="No delivery channel"):
            await adapter.resolve_route(
                tenant_id=tenant_id,
                recipient_id=recipient_id,
                recipient_type="contact",
            )

    @pytest.mark.asyncio
    async def test_error_includes_context_data(self) -> None:
        """NotificationRoutingError carries context data for debugging."""
        tenant_id = uuid4()
        recipient_id = uuid4()
        contact = MagicMock(phone=None, telegram_user_id=None)

        session = AsyncMock()
        session.execute = AsyncMock(
            side_effect=[_scalar_result(contact), _scalar_result(None)],
        )

        adapter = NotificationRoutingAdapter(_mock_session_factory(session))
        with pytest.raises(NotificationRoutingError) as exc_info:
            await adapter.resolve_route(
                tenant_id=tenant_id,
                recipient_id=recipient_id,
                recipient_type="contact",
            )

        assert exc_info.value.context_data["tenant_id"] == str(tenant_id)
        assert exc_info.value.context_data["recipient_id"] == str(recipient_id)
        assert exc_info.value.context_data["recipient_type"] == "contact"
