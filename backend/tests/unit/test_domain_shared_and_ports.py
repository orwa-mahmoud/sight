"""Unit tests for uncovered domain/shared files and abstract ports.

Covers:
- domain/shared/channel_result.py   -- ChannelSendResult value object
- domain/shared/media.py            -- MediaGroup, ExtractedMedia, extract_media()
- domain/notifications/entities.py  -- NotificationFailure entity
- domain/notifications/ports.py     -- ResolvedRoute, NotificationRoutingError, NotificationRoutingPort
- domain/notifications/repositories.py -- NotificationFailureRepository ABC
- domain/telegram/repositories.py   -- TelegramPhoneRepository Protocol
- domain/contacts/repositories.py   -- ContactRepository Protocol
- domain/contacts/entities.py       -- Contact.link_telegram (lines 62-63)
- ai/utils/sender.py                -- resolve_sender Telegram + error paths
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.domain.contacts.entities import Contact
from src.domain.contacts.repositories import ContactRepository
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.notifications.entities import NotificationFailure
from src.domain.notifications.ports import (
    NotificationRoutingError,
    NotificationRoutingPort,
    ResolvedRoute,
)
from src.domain.notifications.repositories import NotificationFailureRepository
from src.domain.shared.channel_result import ChannelSendResult
from src.domain.shared.media import (
    ExtractedMedia,
    MediaGroup,
    extract_media,
)
from src.domain.telegram.repositories import TelegramPhoneRepository

# =====================================================================
# 1. ChannelSendResult
# =====================================================================


class TestChannelSendResult:
    """ChannelSendResult value object: factories, defaults, properties."""

    def test_default_values(self) -> None:
        r = ChannelSendResult()
        assert r.status == "sent"
        assert r.external_message_id == ""
        assert r.channel_response is None
        assert r.error == ""
        assert r.errors == []

    def test_is_sent_true_for_sent_status(self) -> None:
        r = ChannelSendResult(status="sent")
        assert r.is_sent is True

    def test_is_sent_false_for_failed_status(self) -> None:
        r = ChannelSendResult(status="failed")
        assert r.is_sent is False

    def test_sent_factory_defaults(self) -> None:
        r = ChannelSendResult.sent()
        assert r.status == "sent"
        assert r.is_sent is True
        assert r.external_message_id == ""
        assert r.channel_response is None

    def test_sent_factory_with_args(self) -> None:
        resp = {"messages": [{"id": "wamid.123"}]}
        r = ChannelSendResult.sent(external_message_id="wamid.123", channel_response=resp)
        assert r.is_sent is True
        assert r.external_message_id == "wamid.123"
        assert r.channel_response == resp

    def test_failed_factory_defaults(self) -> None:
        r = ChannelSendResult.failed()
        assert r.status == "failed"
        assert r.is_sent is False
        assert r.error == ""

    def test_failed_factory_with_error(self) -> None:
        resp = {"error": {"code": 131026}}
        r = ChannelSendResult.failed(error="rate limited", channel_response=resp)
        assert r.is_sent is False
        assert r.error == "rate limited"
        assert r.channel_response == resp

    def test_frozen_raises_on_mutation(self) -> None:
        r = ChannelSendResult.sent()
        with pytest.raises(AttributeError):
            r.status = "failed"  # type: ignore[misc]

    def test_errors_list_independent(self) -> None:
        """Each instance gets its own errors list (field default_factory)."""
        a = ChannelSendResult()
        b = ChannelSendResult()
        assert a.errors is not b.errors


# =====================================================================
# 2. Media (MediaGroup, ExtractedMedia, extract_media)
# =====================================================================


class TestMediaGroup:
    def test_default_empty(self) -> None:
        g = MediaGroup()
        assert g.urls == []
        assert g.caption == ""

    def test_with_values(self) -> None:
        g = MediaGroup(urls=["https://example.com/a.jpg"], caption="A photo")
        assert len(g.urls) == 1
        assert g.caption == "A photo"


class TestExtractedMedia:
    def test_has_any_false_when_empty(self) -> None:
        m = ExtractedMedia()
        assert m.has_any() is False

    def test_has_any_true_with_images(self) -> None:
        m = ExtractedMedia(images=[MediaGroup(urls=["https://x.com/1.jpg"])])
        assert m.has_any() is True

    def test_has_any_true_with_videos(self) -> None:
        m = ExtractedMedia(videos=[MediaGroup(urls=["https://x.com/1.mp4"])])
        assert m.has_any() is True

    def test_has_any_true_with_documents(self) -> None:
        m = ExtractedMedia(documents=[MediaGroup(urls=["https://x.com/1.pdf"])])
        assert m.has_any() is True

    def test_to_dict_empty(self) -> None:
        d = ExtractedMedia().to_dict()
        assert d == {"images": [], "videos": [], "documents": []}

    def test_to_dict_with_caption(self) -> None:
        m = ExtractedMedia(
            images=[MediaGroup(urls=["https://x.com/a.jpg"], caption="Photo")],
            videos=[MediaGroup(urls=["https://x.com/b.mp4"])],
        )
        d = m.to_dict()
        assert len(d["images"]) == 1
        assert d["images"][0]["urls"] == ["https://x.com/a.jpg"]
        assert d["images"][0]["caption"] == "Photo"
        # video has no caption -- key should be absent
        assert "caption" not in d["videos"][0]
        assert d["documents"] == []


class TestExtractMedia:
    """Tests for the top-level extract_media() function."""

    def test_no_media_returns_empty(self) -> None:
        cleaned, media = extract_media("Hello, how can I help?")
        assert cleaned == "Hello, how can I help?"
        assert media.has_any() is False

    def test_images_block_extracted(self) -> None:
        text = "Here are images:\n<<<IMAGES>>>\nhttps://cdn.test/1.jpg\nhttps://cdn.test/2.jpg\n<<</IMAGES>>>\nDone."
        cleaned, media = extract_media(text)
        assert media.has_any() is True
        assert len(media.images) == 1
        assert media.images[0].urls == ["https://cdn.test/1.jpg", "https://cdn.test/2.jpg"]
        assert "<<<IMAGES>>>" not in cleaned
        assert "Done." in cleaned

    def test_videos_block_extracted(self) -> None:
        text = "Watch:\n<<<VIDEOS>>>\nhttps://cdn.test/v.mp4\n<<</VIDEOS>>>"
        _, media = extract_media(text)
        assert len(media.videos) == 1
        assert media.videos[0].urls == ["https://cdn.test/v.mp4"]

    def test_documents_block_extracted(self) -> None:
        text = "<<<DOCUMENTS>>>\nhttps://cdn.test/doc.pdf\n<<</DOCUMENTS>>>"
        _, media = extract_media(text)
        assert len(media.documents) == 1
        assert media.documents[0].urls == ["https://cdn.test/doc.pdf"]

    def test_block_with_caption(self) -> None:
        text = "<<<IMAGES>>>\nBeautiful sunset\nhttps://cdn.test/sunset.jpg\n<<</IMAGES>>>"
        _, media = extract_media(text)
        assert media.images[0].caption == "Beautiful sunset"
        assert media.images[0].urls == ["https://cdn.test/sunset.jpg"]

    def test_truncated_closing_tag(self) -> None:
        """LLM sometimes writes >> instead of >>> for the closing tag."""
        text = "<<<IMAGES>>>\nhttps://cdn.test/a.jpg\n<<</IMAGES>>"
        _, media = extract_media(text)
        assert len(media.images) == 1
        assert media.images[0].urls == ["https://cdn.test/a.jpg"]

    def test_multiple_blocks_same_kind(self) -> None:
        text = (
            "<<<IMAGES>>>\nhttps://cdn.test/1.jpg\n<<</IMAGES>>>\n<<<IMAGES>>>\nhttps://cdn.test/2.jpg\n<<</IMAGES>>>"
        )
        _, media = extract_media(text)
        assert len(media.images) == 2

    def test_fallback_markdown_images(self) -> None:
        text = "Check out ![photo](https://cdn.test/pic.jpg) and ![another](https://cdn.test/pic2.jpg)"
        cleaned, media = extract_media(text)
        assert media.has_any() is True
        assert len(media.images) == 1
        assert "https://cdn.test/pic.jpg" in media.images[0].urls
        assert "https://cdn.test/pic2.jpg" in media.images[0].urls
        # Markdown syntax should be stripped
        assert "![photo]" not in cleaned

    def test_fallback_dedup_markdown_images(self) -> None:
        text = "![a](https://cdn.test/x.jpg) and ![b](https://cdn.test/x.jpg)"
        _, media = extract_media(text)
        assert len(media.images[0].urls) == 1  # deduped

    def test_no_fallback_when_blocks_found(self) -> None:
        """When blocks are found, markdown fallback is skipped."""
        text = "<<<IMAGES>>>\nhttps://cdn.test/block.jpg\n<<</IMAGES>>>\n![alt](https://cdn.test/md.jpg)"
        _, media = extract_media(text)
        # Block image present, markdown image should NOT be extracted via fallback
        assert len(media.images) == 1
        assert media.images[0].urls == ["https://cdn.test/block.jpg"]

    def test_empty_block_ignored(self) -> None:
        text = "<<<IMAGES>>>\n\n<<</IMAGES>>>"
        _, media = extract_media(text)
        assert media.has_any() is False

    def test_block_without_urls_ignored(self) -> None:
        text = "<<<IMAGES>>>\nJust a caption, no URLs here\n<<</IMAGES>>>"
        _, media = extract_media(text)
        # Block parsed but no URLs -> group not added
        assert len(media.images) == 0

    def test_unclosed_block_ignored(self) -> None:
        """A block with no closing tag should be ignored."""
        text = "<<<IMAGES>>>\nhttps://cdn.test/a.jpg"
        _, media = extract_media(text)
        assert media.has_any() is False

    def test_excessive_newlines_collapsed(self) -> None:
        text = "Before\n\n\n\n\n<<<IMAGES>>>\nhttps://cdn.test/1.jpg\n<<</IMAGES>>>\n\n\n\nAfter"
        cleaned, _ = extract_media(text)
        assert "\n\n\n" not in cleaned

    def test_mixed_kinds(self) -> None:
        text = (
            "<<<IMAGES>>>\nhttps://cdn.test/img.jpg\n<<</IMAGES>>>"
            "<<<VIDEOS>>>\nhttps://cdn.test/vid.mp4\n<<</VIDEOS>>>"
            "<<<DOCUMENTS>>>\nhttps://cdn.test/doc.pdf\n<<</DOCUMENTS>>>"
        )
        _, media = extract_media(text)
        assert len(media.images) == 1
        assert len(media.videos) == 1
        assert len(media.documents) == 1


# =====================================================================
# 3. NotificationFailure entity
# =====================================================================


class TestNotificationFailure:
    def test_create_generates_id_and_timestamp(self) -> None:
        tid = uuid4()
        rid = uuid4()
        f = NotificationFailure.create(
            tenant_id=tid,
            recipient_id=rid,
            recipient_type="contact",
            reason="no channel configured",
        )
        assert isinstance(f.id, UUID)
        assert f.tenant_id == tid
        assert f.recipient_id == rid
        assert f.recipient_type == "contact"
        assert f.reason == "no channel configured"
        assert f.context_data == {}
        assert f.entity_type == ""
        assert f.entity_id == ""
        assert isinstance(f.created_at, datetime)

    def test_create_with_optional_fields(self) -> None:
        f = NotificationFailure.create(
            tenant_id=uuid4(),
            recipient_id=uuid4(),
            recipient_type="owner",
            reason="timeout",
            entity_type="question",
            entity_id="q-123",
            context_data={"attempt": 3},
        )
        assert f.entity_type == "question"
        assert f.entity_id == "q-123"
        assert f.context_data == {"attempt": 3}

    def test_frozen_raises_on_mutation(self) -> None:
        f = NotificationFailure.create(
            tenant_id=uuid4(),
            recipient_id=uuid4(),
            recipient_type="user",
            reason="fail",
        )
        with pytest.raises(AttributeError):
            f.reason = "changed"  # type: ignore[misc]


# =====================================================================
# 4. Notification ports: ResolvedRoute, NotificationRoutingError,
#    NotificationRoutingPort ABC
# =====================================================================


class TestResolvedRoute:
    def test_defaults(self) -> None:
        r = ResolvedRoute(channel="whatsapp", thread_id="t-123")
        assert r.channel == "whatsapp"
        assert r.thread_id == "t-123"
        assert r.conversation_id is None
        assert r.tenant_id is None
        assert r.recipient_id is None

    def test_with_all_fields(self) -> None:
        cid = uuid4()
        tid = uuid4()
        rid = uuid4()
        r = ResolvedRoute(
            channel="telegram",
            thread_id="tg-456",
            conversation_id=cid,
            tenant_id=tid,
            recipient_id=rid,
        )
        assert r.conversation_id == cid
        assert r.tenant_id == tid
        assert r.recipient_id == rid

    def test_frozen(self) -> None:
        r = ResolvedRoute(channel="api", thread_id="x")
        with pytest.raises(AttributeError):
            r.channel = "whatsapp"  # type: ignore[misc]


class TestNotificationRoutingError:
    def test_basic_error(self) -> None:
        err = NotificationRoutingError("no route found")
        assert str(err) == "no route found"
        assert err.reason == "no route found"
        assert err.context_data == {}

    def test_error_with_context(self) -> None:
        err = NotificationRoutingError("fail", context_data={"tenant": "abc"})
        assert err.context_data == {"tenant": "abc"}

    def test_is_exception(self) -> None:
        err = NotificationRoutingError("boom")
        assert isinstance(err, Exception)


class FakeRoutingPort(NotificationRoutingPort):
    """Concrete implementation to exercise the ABC."""

    async def resolve_route(
        self,
        *,
        tenant_id: UUID,
        recipient_id: UUID,
        recipient_type: str,
    ) -> ResolvedRoute:
        return ResolvedRoute(channel="whatsapp", thread_id="fake-thread")


class TestNotificationRoutingPort:
    def test_abc_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            NotificationRoutingPort()  # type: ignore[abstract]

    async def test_fake_implementation_satisfies_abc(self) -> None:
        port = FakeRoutingPort()
        route = await port.resolve_route(
            tenant_id=uuid4(),
            recipient_id=uuid4(),
            recipient_type="contact",
        )
        assert route.channel == "whatsapp"
        assert route.thread_id == "fake-thread"


# =====================================================================
# 5. NotificationFailureRepository ABC
# =====================================================================


class FakeNotificationFailureRepo(NotificationFailureRepository):
    """Concrete implementation to cover the ABC."""

    def __init__(self) -> None:
        self.saved: list[NotificationFailure] = []

    async def save(self, failure: NotificationFailure) -> None:
        self.saved.append(failure)


class TestNotificationFailureRepository:
    def test_abc_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError):
            NotificationFailureRepository()  # type: ignore[abstract]

    async def test_fake_save(self) -> None:
        repo = FakeNotificationFailureRepo()
        f = NotificationFailure.create(
            tenant_id=uuid4(),
            recipient_id=uuid4(),
            recipient_type="contact",
            reason="test",
        )
        await repo.save(f)
        assert len(repo.saved) == 1
        assert repo.saved[0] is f


# =====================================================================
# 6. TelegramPhoneRepository Protocol
# =====================================================================


class FakeTelegramPhoneRepo:
    """Satisfies TelegramPhoneRepository protocol."""

    def __init__(self) -> None:
        self.store: dict[str, str | None] = {}

    async def get_or_register(self, telegram_user_id: str) -> str | None:
        if telegram_user_id not in self.store:
            self.store[telegram_user_id] = None
        return self.store[telegram_user_id]

    async def set_phone(self, telegram_user_id: str, phone: str) -> None:
        self.store[telegram_user_id] = phone


class TestTelegramPhoneRepository:
    def test_protocol_satisfied(self) -> None:
        repo: TelegramPhoneRepository = FakeTelegramPhoneRepo()
        assert repo is not None

    async def test_get_or_register_returns_none_first_time(self) -> None:
        repo = FakeTelegramPhoneRepo()
        result = await repo.get_or_register("12345")
        assert result is None
        assert "12345" in repo.store

    async def test_set_phone_then_get(self) -> None:
        repo = FakeTelegramPhoneRepo()
        await repo.set_phone("12345", "+971501234567")
        result = await repo.get_or_register("12345")
        assert result == "+971501234567"


# =====================================================================
# 7. ContactRepository Protocol
# =====================================================================


class FakeContactRepo:
    """Satisfies ContactRepository protocol."""

    def __init__(self) -> None:
        self.store: dict[UUID, Contact] = {}

    async def get_or_create_by_phone(
        self,
        tenant_id: UUID,
        phone: str,
        name: str | None = None,
    ) -> Contact:
        for c in self.store.values():
            if c.tenant_id == tenant_id and c.phone == phone:
                return c
        c = Contact.create(tenant_id=tenant_id, phone=phone, name=name)
        self.store[c.id] = c
        return c

    async def get_by_telegram_user_id(
        self,
        tenant_id: UUID,
        telegram_user_id: str,
    ) -> Contact | None:
        for c in self.store.values():
            if c.tenant_id == tenant_id and c.telegram_user_id == telegram_user_id:
                return c
        return None

    async def save(self, contact: Contact) -> None:
        self.store[contact.id] = contact

    async def get_by_id(self, contact_id: UUID) -> Contact | None:
        return self.store.get(contact_id)


class TestContactRepository:
    def test_protocol_satisfied(self) -> None:
        repo: ContactRepository = FakeContactRepo()
        assert repo is not None

    async def test_get_or_create_creates_new(self) -> None:
        repo = FakeContactRepo()
        tid = uuid4()
        c = await repo.get_or_create_by_phone(tid, "+971501234567", "Ali")
        assert c.phone == "+971501234567"
        assert c.name == "Ali"
        assert c.tenant_id == tid

    async def test_get_or_create_returns_existing(self) -> None:
        repo = FakeContactRepo()
        tid = uuid4()
        c1 = await repo.get_or_create_by_phone(tid, "+971501234567")
        c2 = await repo.get_or_create_by_phone(tid, "+971501234567")
        assert c1.id == c2.id

    async def test_get_by_telegram_user_id(self) -> None:
        repo = FakeContactRepo()
        tid = uuid4()
        c = await repo.get_or_create_by_phone(tid, "+971501234567")
        c.link_telegram("tg_99")
        await repo.save(c)
        found = await repo.get_by_telegram_user_id(tid, "tg_99")
        assert found is not None
        assert found.id == c.id

    async def test_get_by_telegram_user_id_not_found(self) -> None:
        repo = FakeContactRepo()
        result = await repo.get_by_telegram_user_id(uuid4(), "nonexistent")
        assert result is None

    async def test_get_by_id(self) -> None:
        repo = FakeContactRepo()
        tid = uuid4()
        c = await repo.get_or_create_by_phone(tid, "+971501234567")
        await repo.save(c)
        found = await repo.get_by_id(c.id)
        assert found is not None
        assert found.id == c.id

    async def test_get_by_id_not_found(self) -> None:
        repo = FakeContactRepo()
        assert await repo.get_by_id(uuid4()) is None


# =====================================================================
# 8. Contact.link_telegram (lines 62-63)
# =====================================================================


class TestContactLinkTelegram:
    def test_link_telegram_sets_user_id_and_updates_timestamp(self) -> None:
        c = Contact.create(tenant_id=uuid4(), phone="+971501234567")
        original_updated_at = c.updated_at
        assert c.telegram_user_id is None

        c.link_telegram("tg_user_42")

        assert c.telegram_user_id == "tg_user_42"
        assert c.updated_at >= original_updated_at

    def test_link_telegram_overwrites_existing(self) -> None:
        c = Contact.create(tenant_id=uuid4(), phone="+971501234567", telegram_user_id="old")
        c.link_telegram("new")
        assert c.telegram_user_id == "new"


# =====================================================================
# 9. resolve_sender (ai/utils/sender.py)
# =====================================================================


def _make_uow_mock(
    *,
    phone: str | None = None,
    existing_contact: Contact | None = None,
) -> MagicMock:
    """Build a MagicMock UoW with telegram_phones and contacts stubs."""
    uow = MagicMock()
    uow.telegram_phones = MagicMock()
    uow.telegram_phones.get_or_register = AsyncMock(return_value=phone)
    uow.contacts = MagicMock()

    if existing_contact:
        uow.contacts.get_or_create_by_phone = AsyncMock(return_value=existing_contact)
    else:
        # Default: create a fresh contact on the fly
        async def _create(tenant_id: UUID, phone: str, name: str | None = None) -> Contact:
            return Contact.create(tenant_id=tenant_id, phone=phone, name=name)

        uow.contacts.get_or_create_by_phone = AsyncMock(side_effect=_create)

    uow.contacts.save = AsyncMock()
    return uow


class TestResolveSender:
    """Tests for resolve_sender covering Telegram, WhatsApp, and fallback paths."""

    async def test_whatsapp_creates_contact(self) -> None:
        from src.ai.utils.sender import resolve_sender

        uow = _make_uow_mock()
        result = await resolve_sender(
            tenant_id=uuid4(),
            channel=ConversationChannel.WHATSAPP,
            sender_identifier="+971501234567",
            sender_name="Ali",
            uow=uow,
        )
        assert result is not None
        assert isinstance(result, UUID)
        uow.contacts.get_or_create_by_phone.assert_awaited_once()

    async def test_api_channel_uses_phone_path(self) -> None:
        from src.ai.utils.sender import resolve_sender

        uow = _make_uow_mock()
        result = await resolve_sender(
            tenant_id=uuid4(),
            channel=ConversationChannel.API,
            sender_identifier="api-user-key",
            uow=uow,
        )
        assert result is not None
        uow.contacts.get_or_create_by_phone.assert_awaited_once()

    async def test_telegram_no_phone_returns_none(self) -> None:
        """Line 74-79: Telegram user has no phone -> return None."""
        from src.ai.utils.sender import resolve_sender

        uow = _make_uow_mock(phone=None)
        result = await resolve_sender(
            tenant_id=uuid4(),
            channel=ConversationChannel.TELEGRAM,
            sender_identifier="tg_12345",
            uow=uow,
        )
        assert result is None
        uow.telegram_phones.get_or_register.assert_awaited_once_with("tg_12345")

    async def test_telegram_with_phone_creates_and_links(self) -> None:
        """Lines 81-92: Telegram user has phone -> create contact and link."""
        from src.ai.utils.sender import resolve_sender

        tid = uuid4()
        uow = _make_uow_mock(phone="+971501234567")

        result = await resolve_sender(
            tenant_id=tid,
            channel=ConversationChannel.TELEGRAM,
            sender_identifier="tg_12345",
            sender_name="Ahmed",
            uow=uow,
        )
        assert result is not None
        uow.contacts.get_or_create_by_phone.assert_awaited_once_with(tenant_id=tid, phone="+971501234567", name="Ahmed")
        # Contact was new, so link_telegram should trigger a save
        uow.contacts.save.assert_awaited_once()

    async def test_telegram_already_linked_skips_save(self) -> None:
        """Line 88: telegram_user_id already matches -> no save needed."""
        from src.ai.utils.sender import resolve_sender

        tid = uuid4()
        existing = Contact.create(tenant_id=tid, phone="+971501234567", telegram_user_id="tg_12345")
        uow = _make_uow_mock(phone="+971501234567", existing_contact=existing)

        result = await resolve_sender(
            tenant_id=tid,
            channel=ConversationChannel.TELEGRAM,
            sender_identifier="tg_12345",
            uow=uow,
        )
        assert result == existing.id
        uow.contacts.save.assert_not_awaited()

    async def test_phone_sender_exception_returns_none(self) -> None:
        """Lines 110-112: _resolve_phone_sender catches exceptions -> None."""
        from src.ai.utils.sender import resolve_sender

        uow = _make_uow_mock()
        uow.contacts.get_or_create_by_phone = AsyncMock(side_effect=RuntimeError("DB down"))

        result = await resolve_sender(
            tenant_id=uuid4(),
            channel=ConversationChannel.WHATSAPP,
            sender_identifier="+971501234567",
            uow=uow,
        )
        assert result is None

    async def test_web_channel_uses_phone_path(self) -> None:
        """Fallback path: WEB channel treated like phone."""
        from src.ai.utils.sender import resolve_sender

        uow = _make_uow_mock()
        result = await resolve_sender(
            tenant_id=uuid4(),
            channel=ConversationChannel.WEB,
            sender_identifier="web-visitor-123",
            uow=uow,
        )
        assert result is not None
        uow.contacts.get_or_create_by_phone.assert_awaited_once()
