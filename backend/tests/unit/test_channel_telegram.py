# mypy: disable-error-code="method-assign"
"""Unit tests for src/infrastructure/channels/telegram.py.

All httpx calls are mocked -- no real network traffic.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.infrastructure.channels.telegram import (
    TelegramAdapter,
    _build_media_items,
    _extract_tg_message_id,
    _strip_html,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(token: str = "bot-tok-123") -> TelegramAdapter:
    """Create a TelegramAdapter with a mocked httpx client."""
    cfg = MagicMock()
    cfg.telegram_bot_token = token
    adapter = TelegramAdapter(tenant_config=cfg)
    adapter._client = AsyncMock(spec=httpx.AsyncClient)
    return adapter


def _ok_response(json_body: dict[str, Any] | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = json_body or {"ok": True, "result": {"message_id": 42}}
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(status: int = 500) -> httpx.HTTPStatusError:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = "error"
    request = MagicMock(spec=httpx.Request)
    return httpx.HTTPStatusError("fail", request=request, response=resp)


def _telegram_payload(
    text: str = "Hello",
    user_id: int = 42,
    chat_id: int = 99,
    msg_type: str = "text",
    file_id: str = "",
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "from": {"id": user_id, "first_name": "Ali"},
        "chat": {"id": chat_id},
    }
    if msg_type == "text":
        message["text"] = text
    elif msg_type == "voice":
        message["text"] = text
        message["voice"] = {"file_id": file_id}
    elif msg_type == "audio":
        message["text"] = text
        message["audio"] = {"file_id": file_id}
    elif msg_type == "photo":
        message["text"] = text
        message["photo"] = [{"file_id": "small"}, {"file_id": file_id}]
    return {"message": message}


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


class TestStripHtml:
    def test_removes_tags(self) -> None:
        assert _strip_html("<b>bold</b> and <i>italic</i>") == "bold and italic"

    def test_plain_text_unchanged(self) -> None:
        assert _strip_html("no tags") == "no tags"

    def test_empty_string(self) -> None:
        assert _strip_html("") == ""


class TestBuildMediaItems:
    def test_html_mode(self) -> None:
        items = _build_media_items(["https://a.png", "https://b.png"], "Cap <b>bold</b>", html=True)
        assert len(items) == 2
        assert items[0]["caption"] == "Cap <b>bold</b>"
        assert items[0]["parse_mode"] == "HTML"
        assert "caption" not in items[1]

    def test_plain_mode_strips_html(self) -> None:
        items = _build_media_items(["https://a.png"], "<b>Bold</b> cap", html=False)
        assert items[0]["caption"] == "Bold cap"
        assert "parse_mode" not in items[0]

    def test_no_caption(self) -> None:
        items = _build_media_items(["https://a.png"], "", html=True)
        assert "caption" not in items[0]

    def test_caption_truncated_to_1024(self) -> None:
        long_cap = "x" * 2000
        items = _build_media_items(["https://a.png"], long_cap, html=True)
        assert len(items[0]["caption"]) == 1024


class TestExtractTgMessageId:
    def test_dict_result(self) -> None:
        assert _extract_tg_message_id({"result": {"message_id": 123}}) == "123"

    def test_no_message_id(self) -> None:
        assert _extract_tg_message_id({"result": {}}) == ""

    def test_non_dict_result(self) -> None:
        assert _extract_tg_message_id({"result": [1, 2]}) == ""

    def test_empty_response(self) -> None:
        assert _extract_tg_message_id({}) == ""


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestTelegramAdapterInit:
    def test_with_token(self) -> None:
        cfg = MagicMock()
        cfg.telegram_bot_token = "my-token"
        adapter = TelegramAdapter(tenant_config=cfg)
        assert adapter._token == "my-token"

    def test_no_config(self) -> None:
        adapter = TelegramAdapter()
        assert adapter._token == ""

    def test_empty_token(self) -> None:
        cfg = MagicMock()
        cfg.telegram_bot_token = ""
        adapter = TelegramAdapter(tenant_config=cfg)
        assert adapter._token == ""

    def test_none_config(self) -> None:
        adapter = TelegramAdapter(tenant_config=None)
        assert adapter._token == ""


# ---------------------------------------------------------------------------
# parse_incoming
# ---------------------------------------------------------------------------


class TestParseIncoming:
    @pytest.mark.asyncio
    async def test_text_message(self) -> None:
        adapter = _make_adapter()
        incoming = await adapter.parse_incoming(_telegram_payload(text="Hi"))
        assert incoming.channel == "telegram"
        assert incoming.sender_phone == "99"
        assert incoming.text == "Hi"
        assert incoming.message_type.value == "text"
        assert incoming.metadata["telegram_chat_id"] == "99"
        assert incoming.metadata["telegram_user_id"] == "42"

    @pytest.mark.asyncio
    async def test_voice_message(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(return_value=_ok_response({"result": {"file_path": "voice/file.oga"}}))
        incoming = await adapter.parse_incoming(_telegram_payload(msg_type="voice", file_id="fid1"))
        assert incoming.message_type.value == "voice"
        assert "voice/file.oga" in incoming.media_url

    @pytest.mark.asyncio
    async def test_audio_message(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(return_value=_ok_response({"result": {"file_path": "audio/song.mp3"}}))
        incoming = await adapter.parse_incoming(_telegram_payload(msg_type="audio", file_id="fid2"))
        assert incoming.message_type.value == "voice"

    @pytest.mark.asyncio
    async def test_photo_message(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(return_value=_ok_response({"result": {"file_path": "photos/img.jpg"}}))
        incoming = await adapter.parse_incoming(_telegram_payload(msg_type="photo", file_id="fid3"))
        assert incoming.message_type.value == "image"
        assert "photos/img.jpg" in incoming.media_url

    @pytest.mark.asyncio
    async def test_empty_payload(self) -> None:
        adapter = _make_adapter()
        incoming = await adapter.parse_incoming({})
        assert incoming.sender_phone == ""
        assert incoming.text == ""

    @pytest.mark.asyncio
    async def test_voice_no_file_id(self) -> None:
        adapter = _make_adapter()
        payload = {"message": {"from": {"id": 1}, "chat": {"id": 2}, "voice": {}}}
        incoming = await adapter.parse_incoming(payload)
        assert incoming.message_type.value == "voice"
        assert incoming.media_url == ""


# ---------------------------------------------------------------------------
# send_text
# ---------------------------------------------------------------------------


class TestSendText:
    @pytest.mark.asyncio
    async def test_success_html(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        result = await adapter.send_text("99", "Hello <b>world</b>")
        assert result is not None
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        adapter = TelegramAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_text("99", "Hi")
        assert result is None

    @pytest.mark.asyncio
    async def test_html_fallback_on_400(self) -> None:
        adapter = _make_adapter()
        # First call fails with 400 (bad HTML), second succeeds (plain text fallback)
        adapter._client.post = AsyncMock(
            side_effect=[_error_response(400), _ok_response({"ok": True, "result": {"message_id": 1}})]
        )
        await adapter.send_text("99", "<invalid>tag</bad>")
        # Should have called twice: original + fallback
        assert adapter._client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_non_400_error_re_raised(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=_error_response(500))
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.send_text("99", "hi")

    @pytest.mark.asyncio
    async def test_long_text_chunked(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        long_text = "x" * 5000  # > 4096 -> 2 chunks
        await adapter.send_text("99", long_text)
        assert adapter._client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_remove_keyboard(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        await adapter.send_text("99", "Hi", remove_keyboard=True)
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["reply_markup"] == {"remove_keyboard": True}

    @pytest.mark.asyncio
    async def test_generic_exception_handled(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=RuntimeError("net"))
        with pytest.raises(RuntimeError, match="net"):
            await adapter.send_text("99", "hi")


# ---------------------------------------------------------------------------
# send_contact_request
# ---------------------------------------------------------------------------


class TestSendContactRequest:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        await adapter.send_contact_request("99")
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["reply_markup"]["keyboard"][0][0]["request_contact"] is True

    @pytest.mark.asyncio
    async def test_custom_text(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        await adapter.send_contact_request("99", text="Share your number")
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["text"] == "Share your number"

    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        adapter = TelegramAdapter()
        adapter._client = AsyncMock()
        await adapter.send_contact_request("99")
        adapter._client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_error_handled(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=RuntimeError("fail"))
        # Should not raise
        await adapter.send_contact_request("99")


# ---------------------------------------------------------------------------
# send_image
# ---------------------------------------------------------------------------


class TestSendImage:
    @pytest.mark.asyncio
    async def test_success_with_caption(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        result = await adapter.send_image("99", "https://img.png", caption="Pic")
        assert result is not None
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["photo"] == "https://img.png"
        assert payload["caption"] == "Pic"
        assert payload["parse_mode"] == "HTML"

    @pytest.mark.asyncio
    async def test_success_no_caption(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        await adapter.send_image("99", "https://img.png")
        payload = adapter._client.post.call_args.kwargs["json"]
        assert "caption" not in payload

    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        adapter = TelegramAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_image("99", "https://img.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_caption_truncated(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        await adapter.send_image("99", "https://img.png", caption="x" * 2000)
        payload = adapter._client.post.call_args.kwargs["json"]
        assert len(payload["caption"]) == 1024


# ---------------------------------------------------------------------------
# send_media_group
# ---------------------------------------------------------------------------


class TestSendMediaGroup:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response({"ok": True, "result": []}))
        result = await adapter.send_media_group("99", ["https://a.png", "https://b.png"], caption="Album")
        assert result is not None

    @pytest.mark.asyncio
    async def test_html_fallback_on_400(self) -> None:
        adapter = _make_adapter()
        # First call: 400 (HTML rejected), second call: success
        adapter._client.post = AsyncMock(side_effect=[_error_response(400), _ok_response({"ok": True, "result": []})])
        await adapter.send_media_group("99", ["https://a.png"], caption="<b>Bold</b>")
        # Should retry with plain text
        assert adapter._client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_non_400_error(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=_error_response(500))
        result = await adapter.send_media_group("99", ["https://a.png"])
        assert result is None

    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        adapter = TelegramAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_media_group("99", ["https://a.png"])
        assert result is None

    @pytest.mark.asyncio
    async def test_empty_urls(self) -> None:
        adapter = _make_adapter()
        result = await adapter.send_media_group("99", [])
        assert result is None

    @pytest.mark.asyncio
    async def test_generic_error(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=RuntimeError("net"))
        result = await adapter.send_media_group("99", ["https://a.png"])
        assert result is None

    @pytest.mark.asyncio
    async def test_plain_fallback_error(self) -> None:
        adapter = _make_adapter()
        # Both HTML and plain attempts fail
        adapter._client.post = AsyncMock(side_effect=[_error_response(400), _error_response(500)])
        result = await adapter.send_media_group("99", ["https://a.png"], caption="Cap")
        assert result is None


# ---------------------------------------------------------------------------
# send_video
# ---------------------------------------------------------------------------


class TestSendVideo:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        result = await adapter.send_video("99", "https://v.mp4", caption="Vid")
        assert result is not None
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["video"] == "https://v.mp4"

    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        adapter = TelegramAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_video("99", "https://v.mp4")
        assert result is None


# ---------------------------------------------------------------------------
# send_document
# ---------------------------------------------------------------------------


class TestSendDocumentTelegram:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        result = await adapter.send_document("99", "https://d.pdf", caption="Doc")
        assert result is not None
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["document"] == "https://d.pdf"

    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        adapter = TelegramAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_document("99", "https://d.pdf")
        assert result is None


# ---------------------------------------------------------------------------
# send_voice
# ---------------------------------------------------------------------------


class TestSendVoiceTelegram:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        await adapter.send_voice("99", b"audio-bytes")
        adapter._client.post.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        adapter = TelegramAdapter()
        adapter._client = AsyncMock()
        await adapter.send_voice("99", b"data")
        adapter._client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_error_handled(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=RuntimeError("fail"))
        # Should not raise
        await adapter.send_voice("99", b"data")


# ---------------------------------------------------------------------------
# get_file_url
# ---------------------------------------------------------------------------


class TestGetFileUrl:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(return_value=_ok_response({"result": {"file_path": "voice/audio.oga"}}))
        url = await adapter.get_file_url("fid1")
        assert url == f"https://api.telegram.org/file/bot{adapter._token}/voice/audio.oga"

    @pytest.mark.asyncio
    async def test_no_token(self) -> None:
        adapter = TelegramAdapter()
        url = await adapter.get_file_url("fid1")
        assert url == ""

    @pytest.mark.asyncio
    async def test_error_returns_empty(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(side_effect=RuntimeError("net"))
        url = await adapter.get_file_url("fid1")
        assert url == ""

    @pytest.mark.asyncio
    async def test_no_file_path(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(return_value=_ok_response({"result": {}}))
        url = await adapter.get_file_url("fid1")
        assert url == ""


# ---------------------------------------------------------------------------
# handle_webhook
# ---------------------------------------------------------------------------


class TestHandleWebhookTelegram:
    @pytest.mark.asyncio
    async def test_no_message_key_skips(self) -> None:
        adapter = _make_adapter()
        # Should not raise -- just skips
        await adapter.handle_webhook({"update_id": 123}, "tenant-1")

    @pytest.mark.asyncio
    async def test_with_message_delegates(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        chat_fn = AsyncMock(return_value={"response": "Reply"})
        payload = _telegram_payload(text="hi")
        await adapter.handle_webhook(payload, "tenant-1", chat_fn=chat_fn)
        chat_fn.assert_awaited_once()


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestCloseTelegram:
    @pytest.mark.asyncio
    async def test_close(self) -> None:
        adapter = _make_adapter()
        adapter._client.aclose = AsyncMock()
        await adapter.close()
        adapter._client.aclose.assert_awaited_once()


# ---------------------------------------------------------------------------
# _api_url
# ---------------------------------------------------------------------------


class TestApiUrl:
    def test_format(self) -> None:
        adapter = _make_adapter(token="BOT-TOKEN")
        assert adapter._api_url("sendMessage") == "https://api.telegram.org/botBOT-TOKEN/sendMessage"
