"""Unit tests for src/infrastructure/channels/base.py.

Covers ChannelAdapter ABC via a concrete test subclass, plus IncomingMessage,
OutgoingMessage, MessageType dataclasses, and the send_structured / send_response
media dispatch logic.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.domain.shared.media import ExtractedMedia, MediaGroup
from src.infrastructure.channels.base import (
    ChannelAdapter,
    IncomingMessage,
    MessageType,
    OutgoingMessage,
)

# ---------------------------------------------------------------------------
# Concrete test subclass
# ---------------------------------------------------------------------------


class _StubAdapter(ChannelAdapter):
    """Minimal concrete adapter for testing base-class methods."""

    channel_name = "stub"

    def __init__(self) -> None:
        self.sent_texts: list[tuple[str, str]] = []
        self.sent_voices: list[tuple[str, bytes, str]] = []
        self._send_text_response: dict[str, Any] | None = {"ok": True}
        self._send_text_error: Exception | None = None

    async def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        return IncomingMessage(channel="stub", sender_phone="", text=raw_payload.get("text", ""))

    async def send_text(self, recipient: str, text: str) -> dict[str, Any] | None:
        if self._send_text_error:
            raise self._send_text_error
        self.sent_texts.append((recipient, text))
        return self._send_text_response

    async def send_voice(self, recipient: str, audio: bytes, mime_type: str = "audio/ogg") -> None:
        self.sent_voices.append((recipient, audio, mime_type))


# ---------------------------------------------------------------------------
# MessageType
# ---------------------------------------------------------------------------


class TestMessageType:
    def test_values(self) -> None:
        assert MessageType.TEXT == "text"
        assert MessageType.VOICE == "voice"
        assert MessageType.IMAGE == "image"
        assert MessageType.DOCUMENT == "document"
        assert MessageType.LOCATION == "location"

    def test_is_str_enum(self) -> None:
        assert isinstance(MessageType.TEXT, str)


# ---------------------------------------------------------------------------
# IncomingMessage
# ---------------------------------------------------------------------------


class TestIncomingMessage:
    def test_defaults(self) -> None:
        msg = IncomingMessage(channel="whatsapp", sender_phone="+123")
        assert msg.message_type == MessageType.TEXT
        assert msg.text == ""
        assert msg.media_url == ""
        assert msg.raw_payload == {}
        assert msg.thread_id == ""
        assert msg.metadata == {}

    def test_full_construction(self) -> None:
        msg = IncomingMessage(
            channel="telegram",
            sender_phone="+999",
            message_type=MessageType.VOICE,
            text="hello",
            media_url="https://example.com/audio.ogg",
            raw_payload={"key": "val"},
            thread_id="t1",
            metadata={"extra": 1},
        )
        assert msg.channel == "telegram"
        assert msg.message_type == MessageType.VOICE
        assert msg.metadata["extra"] == 1


# ---------------------------------------------------------------------------
# OutgoingMessage
# ---------------------------------------------------------------------------


class TestOutgoingMessage:
    def test_defaults(self) -> None:
        msg = OutgoingMessage()
        assert msg.text == ""
        assert msg.voice_audio is None
        assert msg.media_url == ""
        assert msg.metadata == {}


# ---------------------------------------------------------------------------
# Default send_image / send_video / send_document (fallback to send_text)
# ---------------------------------------------------------------------------


class TestDefaultMediaFallbacks:
    @pytest.mark.asyncio
    async def test_send_image_without_caption(self) -> None:
        adapter = _StubAdapter()
        await adapter.send_image("+1", "https://img.png")
        assert adapter.sent_texts == [("+1", "https://img.png")]

    @pytest.mark.asyncio
    async def test_send_image_with_caption(self) -> None:
        adapter = _StubAdapter()
        await adapter.send_image("+1", "https://img.png", caption="Look!")
        assert adapter.sent_texts == [("+1", "Look!\nhttps://img.png")]

    @pytest.mark.asyncio
    async def test_send_video_fallback(self) -> None:
        adapter = _StubAdapter()
        await adapter.send_video("+1", "https://vid.mp4", caption="Video")
        assert adapter.sent_texts == [("+1", "Video\nhttps://vid.mp4")]

    @pytest.mark.asyncio
    async def test_send_document_fallback(self) -> None:
        adapter = _StubAdapter()
        await adapter.send_document("+1", "https://doc.pdf")
        assert adapter.sent_texts == [("+1", "https://doc.pdf")]


# ---------------------------------------------------------------------------
# Default send_media_group
# ---------------------------------------------------------------------------


class TestDefaultSendMediaGroup:
    @pytest.mark.asyncio
    async def test_sends_first_with_caption_rest_without(self) -> None:
        adapter = _StubAdapter()
        urls = ["https://a.png", "https://b.png", "https://c.png"]
        result = await adapter.send_media_group("+1", urls, caption="Album")
        assert result is None
        assert len(adapter.sent_texts) == 3
        # First image gets caption
        assert adapter.sent_texts[0] == ("+1", "Album\nhttps://a.png")
        # Subsequent images have no caption
        assert adapter.sent_texts[1] == ("+1", "https://b.png")

    @pytest.mark.asyncio
    async def test_empty_urls(self) -> None:
        adapter = _StubAdapter()
        result = await adapter.send_media_group("+1", [])
        assert result is None
        assert adapter.sent_texts == []


# ---------------------------------------------------------------------------
# send_structured
# ---------------------------------------------------------------------------


class TestSendStructured:
    @pytest.mark.asyncio
    async def test_text_only_no_media(self) -> None:
        adapter = _StubAdapter()
        result = await adapter.send_structured("+1", "Hello!")
        assert result.is_sent
        assert result.channel_response == {"ok": True}
        assert adapter.sent_texts == [("+1", "Hello!")]

    @pytest.mark.asyncio
    async def test_blank_text_skips_send(self) -> None:
        adapter = _StubAdapter()
        result = await adapter.send_structured("+1", "   ")
        assert result.is_sent
        assert adapter.sent_texts == []

    @pytest.mark.asyncio
    async def test_text_with_images(self) -> None:
        adapter = _StubAdapter()
        media = ExtractedMedia(images=[MediaGroup(urls=["https://img.png"], caption="pic")])
        result = await adapter.send_structured("+1", "Check this:", media)
        assert result.is_sent
        # text + one image
        assert len(adapter.sent_texts) == 2

    @pytest.mark.asyncio
    async def test_text_send_error_collects_error(self) -> None:
        adapter = _StubAdapter()
        adapter._send_text_error = RuntimeError("boom")
        result = await adapter.send_structured("+1", "Hello!")
        assert result.status == "failed"
        assert "text: boom" in result.error

    @pytest.mark.asyncio
    async def test_text_succeeds_but_media_fails(self) -> None:
        adapter = _StubAdapter()
        media = ExtractedMedia(videos=[MediaGroup(urls=["https://v.mp4"])])
        # Patch send_video to fail
        adapter.send_video = AsyncMock(side_effect=RuntimeError("video fail"))  # type: ignore[method-assign]
        result = await adapter.send_structured("+1", "text", media)
        # text succeeded so status is "sent" with error info
        assert result.status == "sent"
        assert "video: video fail" in result.error

    @pytest.mark.asyncio
    async def test_media_documents(self) -> None:
        adapter = _StubAdapter()
        media = ExtractedMedia(documents=[MediaGroup(urls=["https://d.pdf"], caption="doc")])
        result = await adapter.send_structured("+1", "Here:", media)
        assert result.is_sent
        # text + document fallback via send_text
        assert len(adapter.sent_texts) == 2


# ---------------------------------------------------------------------------
# _send_image_group
# ---------------------------------------------------------------------------


class TestSendImageGroup:
    @pytest.mark.asyncio
    async def test_single_url_calls_send_image(self) -> None:
        adapter = _StubAdapter()
        group = MediaGroup(urls=["https://a.png"], caption="cap")
        await adapter._send_image_group("+1", group)
        assert adapter.sent_texts == [("+1", "cap\nhttps://a.png")]

    @pytest.mark.asyncio
    async def test_multiple_urls_calls_send_media_group(self) -> None:
        adapter = _StubAdapter()
        group = MediaGroup(urls=["https://a.png", "https://b.png"], caption="cap")
        await adapter._send_image_group("+1", group)
        # First with caption, second without
        assert len(adapter.sent_texts) == 2


# ---------------------------------------------------------------------------
# send_response (extract_media integration)
# ---------------------------------------------------------------------------


class TestSendResponse:
    @pytest.mark.asyncio
    async def test_plain_text_no_media(self) -> None:
        adapter = _StubAdapter()
        result = await adapter.send_response("+1", "Just text")
        assert result.is_sent
        assert adapter.sent_texts == [("+1", "Just text")]

    @pytest.mark.asyncio
    async def test_with_media_blocks(self) -> None:
        adapter = _StubAdapter()
        text = "Hello\n<<<IMAGES>>>\nhttps://a.png\n<<</IMAGES>>>"
        result = await adapter.send_response("+1", text)
        assert result.is_sent
        # text "Hello" + image
        assert len(adapter.sent_texts) == 2


# ---------------------------------------------------------------------------
# _safe_send
# ---------------------------------------------------------------------------


class TestSafeSend:
    @pytest.mark.asyncio
    async def test_success_no_errors(self) -> None:
        errors: list[str] = []
        fn = AsyncMock()
        await ChannelAdapter._safe_send(errors, "img", fn, "a", "b")
        fn.assert_awaited_once_with("a", "b")
        assert errors == []

    @pytest.mark.asyncio
    async def test_failure_appends_error(self) -> None:
        errors: list[str] = []
        fn = AsyncMock(side_effect=RuntimeError("oops"))
        await ChannelAdapter._safe_send(errors, "img", fn, "a")
        assert len(errors) == 1
        assert "img: oops" in errors[0]


# ---------------------------------------------------------------------------
# handle_webhook
# ---------------------------------------------------------------------------


class TestHandleWebhook:
    @pytest.mark.asyncio
    async def test_delegates_to_parse_and_process(self) -> None:
        adapter = _StubAdapter()
        chat_fn = AsyncMock(return_value={"response": "Reply"})
        result = await adapter.handle_webhook({"text": "hi"}, "tenant-1", chat_fn=chat_fn)
        assert result == "Reply"
        assert adapter.sent_texts  # reply was sent


# ---------------------------------------------------------------------------
# process_message
# ---------------------------------------------------------------------------


class TestProcessMessage:
    @pytest.mark.asyncio
    async def test_raises_without_chat_fn(self) -> None:
        adapter = _StubAdapter()
        msg = IncomingMessage(channel="stub", sender_phone="+1", text="hi")
        with pytest.raises(ValueError, match="chat_fn must be provided"):
            await adapter.process_message(msg, "t1")

    @pytest.mark.asyncio
    async def test_calls_chat_fn_and_sends_reply(self) -> None:
        adapter = _StubAdapter()
        chat_fn = AsyncMock(return_value={"response": "Answer"})
        msg = IncomingMessage(channel="stub", sender_phone="+1", text="q")
        result = await adapter.process_message(msg, "t1", chat_fn=chat_fn)
        assert result == "Answer"
        chat_fn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_empty_response_skips_send(self) -> None:
        adapter = _StubAdapter()
        chat_fn = AsyncMock(return_value={"response": ""})
        msg = IncomingMessage(channel="stub", sender_phone="+1", text="q")
        result = await adapter.process_message(msg, "t1", chat_fn=chat_fn)
        assert result == ""
        assert adapter.sent_texts == []
