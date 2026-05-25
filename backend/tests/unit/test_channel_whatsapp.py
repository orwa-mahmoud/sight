"""Unit tests for src/infrastructure/channels/whatsapp.py.

All httpx calls are mocked -- no real network traffic.
"""

from __future__ import annotations

import hashlib
import hmac as hmac_mod
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from src.infrastructure.channels.whatsapp import (
    META_GRAPH_API,
    WhatsAppAdapter,
    _extract_first_message,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_adapter(phone_id: str = "pn123", token: str = "tok-abc") -> WhatsAppAdapter:
    """Create an adapter with mocked httpx client."""
    adapter = WhatsAppAdapter(phone_number_id=phone_id, access_token=token)
    adapter._client = AsyncMock(spec=httpx.AsyncClient)
    return adapter


def _ok_response(json_body: dict[str, Any] | None = None) -> MagicMock:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = 200
    resp.json.return_value = json_body or {"messages": [{"id": "wamid.123"}]}
    resp.raise_for_status = MagicMock()
    return resp


def _error_response(status: int = 500, body: str = "error") -> httpx.HTTPStatusError:
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status
    resp.text = body
    request = MagicMock(spec=httpx.Request)
    return httpx.HTTPStatusError("fail", request=request, response=resp)


def _whatsapp_payload(
    sender: str = "+123",
    msg_type: str = "text",
    text: str = "Hello",
    media_id: str = "",
    caption: str = "",
) -> dict[str, Any]:
    msg: dict[str, Any] = {"from": sender, "type": msg_type}
    if msg_type == "text":
        msg["text"] = {"body": text}
    elif msg_type == "audio":
        msg["audio"] = {"id": media_id}
    elif msg_type == "image":
        msg["image"] = {"id": media_id, "caption": caption}
    elif msg_type == "interactive":
        msg["interactive"] = {"button_reply": {"title": text}}
    elif msg_type == "location":
        msg["location"] = {"latitude": 25.2, "longitude": 55.3}
    return {"entry": [{"changes": [{"value": {"messages": [msg]}}]}]}


# ---------------------------------------------------------------------------
# _extract_first_message helper
# ---------------------------------------------------------------------------


class TestExtractFirstMessage:
    def test_valid_payload(self) -> None:
        payload = _whatsapp_payload()
        msg = _extract_first_message(payload)
        assert msg is not None
        assert msg["from"] == "+123"

    def test_empty_entries(self) -> None:
        assert _extract_first_message({}) is None
        assert _extract_first_message({"entry": []}) is None

    def test_no_changes(self) -> None:
        assert _extract_first_message({"entry": [{}]}) is None
        assert _extract_first_message({"entry": [{"changes": []}]}) is None

    def test_no_messages(self) -> None:
        payload = {"entry": [{"changes": [{"value": {}}]}]}
        assert _extract_first_message(payload) is None

    def test_empty_messages_list(self) -> None:
        payload = {"entry": [{"changes": [{"value": {"messages": []}}]}]}
        assert _extract_first_message(payload) is None


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------


class TestWhatsAppAdapterInit:
    def test_from_explicit_args(self) -> None:
        adapter = WhatsAppAdapter(phone_number_id="pn1", access_token="tok1")
        assert adapter._phone_number_id == "pn1"
        assert adapter._access_token == "tok1"

    def test_from_tenant_config(self) -> None:
        cfg = MagicMock()
        cfg.whatsapp_phone_number_id = "pn2"
        cfg.whatsapp_access_token = "tok2"
        cfg.whatsapp_verify_token = "vt2"
        adapter = WhatsAppAdapter(tenant_config=cfg)
        assert adapter._phone_number_id == "pn2"
        assert adapter._access_token == "tok2"
        assert adapter._verify_token == "vt2"

    def test_missing_credentials_logs_warning(self) -> None:
        # Should not raise, just logs
        adapter = WhatsAppAdapter()
        assert adapter._phone_number_id == ""

    def test_tenant_config_overrides_kwargs(self) -> None:
        cfg = MagicMock()
        cfg.whatsapp_phone_number_id = "from-cfg"
        cfg.whatsapp_access_token = "tok-cfg"
        cfg.whatsapp_verify_token = "vt-cfg"
        adapter = WhatsAppAdapter(tenant_config=cfg, phone_number_id="from-kwarg", access_token="tok-kwarg")
        assert adapter._phone_number_id == "from-cfg"


# ---------------------------------------------------------------------------
# parse_incoming
# ---------------------------------------------------------------------------


class TestParseIncoming:
    @pytest.mark.asyncio
    async def test_text_message(self) -> None:
        adapter = _make_adapter()
        incoming = await adapter.parse_incoming(_whatsapp_payload(text="Hi"))
        assert incoming.channel == "whatsapp"
        assert incoming.sender_phone == "+123"
        assert incoming.text == "Hi"
        assert incoming.message_type.value == "text"

    @pytest.mark.asyncio
    async def test_empty_payload(self) -> None:
        adapter = _make_adapter()
        incoming = await adapter.parse_incoming({})
        assert incoming.sender_phone == ""
        assert incoming.text == ""

    @pytest.mark.asyncio
    async def test_audio_message(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(return_value=_ok_response({"url": "https://media.url/audio"}))
        incoming = await adapter.parse_incoming(_whatsapp_payload(msg_type="audio", media_id="mid1"))
        assert incoming.message_type.value == "voice"
        assert incoming.media_url == "https://media.url/audio"

    @pytest.mark.asyncio
    async def test_image_message(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(return_value=_ok_response({"url": "https://media.url/img"}))
        incoming = await adapter.parse_incoming(
            _whatsapp_payload(msg_type="image", media_id="mid2", caption="Nice pic")
        )
        assert incoming.message_type.value == "image"
        assert incoming.text == "Nice pic"
        assert incoming.media_url == "https://media.url/img"

    @pytest.mark.asyncio
    async def test_interactive_message(self) -> None:
        adapter = _make_adapter()
        incoming = await adapter.parse_incoming(_whatsapp_payload(msg_type="interactive", text="Button clicked"))
        assert incoming.message_type.value == "text"
        assert incoming.text == "Button clicked"

    @pytest.mark.asyncio
    async def test_location_message(self) -> None:
        adapter = _make_adapter()
        incoming = await adapter.parse_incoming(_whatsapp_payload(msg_type="location"))
        assert incoming.message_type.value == "location"
        assert "25.2" in incoming.text
        assert "55.3" in incoming.text

    @pytest.mark.asyncio
    async def test_unknown_type(self) -> None:
        adapter = _make_adapter()
        payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "+1", "type": "sticker"}]}}]}]}
        incoming = await adapter.parse_incoming(payload)
        assert incoming.message_type.value == "text"
        assert incoming.text == ""

    @pytest.mark.asyncio
    async def test_audio_no_media_id(self) -> None:
        adapter = _make_adapter()
        payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "+1", "type": "audio", "audio": {}}]}}]}]}
        incoming = await adapter.parse_incoming(payload)
        assert incoming.media_url == ""

    @pytest.mark.asyncio
    async def test_image_no_media_id(self) -> None:
        adapter = _make_adapter()
        payload = {"entry": [{"changes": [{"value": {"messages": [{"from": "+1", "type": "image", "image": {}}]}}]}]}
        incoming = await adapter.parse_incoming(payload)
        assert incoming.media_url == ""


# ---------------------------------------------------------------------------
# _get_media_url
# ---------------------------------------------------------------------------


class TestGetMediaUrl:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(return_value=_ok_response({"url": "https://cdn.meta.com/file"}))
        url = await adapter._get_media_url("mid1")
        assert url == "https://cdn.meta.com/file"

    @pytest.mark.asyncio
    async def test_error_returns_empty(self) -> None:
        adapter = _make_adapter()
        adapter._client.get = AsyncMock(side_effect=RuntimeError("network"))
        url = await adapter._get_media_url("mid1")
        assert url == ""


# ---------------------------------------------------------------------------
# send_text
# ---------------------------------------------------------------------------


class TestSendText:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response({"messages": [{"id": "wamid.1"}]}))
        result = await adapter.send_text("+123", "Hello")
        assert result == {"messages": [{"id": "wamid.1"}]}
        call_kwargs = adapter._client.post.call_args
        payload = call_kwargs.kwargs["json"]
        assert payload["to"] == "123"  # stripped +
        assert payload["text"]["body"] == "Hello"

    @pytest.mark.asyncio
    async def test_no_credentials(self) -> None:
        adapter = WhatsAppAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_text("+1", "hi")
        assert result is None
        adapter._client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=_error_response(500))
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.send_text("+1", "hi")

    @pytest.mark.asyncio
    async def test_generic_error_raises(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=RuntimeError("net"))
        with pytest.raises(RuntimeError):
            await adapter.send_text("+1", "hi")


# ---------------------------------------------------------------------------
# send_image
# ---------------------------------------------------------------------------


class TestSendImage:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        result = await adapter.send_image("+1", "https://img.png", caption="Look")
        assert result is not None
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["type"] == "image"
        assert payload["image"]["link"] == "https://img.png"
        assert payload["image"]["caption"] == "Look"

    @pytest.mark.asyncio
    async def test_no_credentials(self) -> None:
        adapter = WhatsAppAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_image("+1", "https://img.png")
        assert result is None

    @pytest.mark.asyncio
    async def test_http_error_raises(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=_error_response(400, "bad request"))
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.send_image("+1", "https://img.png")


# ---------------------------------------------------------------------------
# send_media_group
# ---------------------------------------------------------------------------


class TestSendMediaGroup:
    @pytest.mark.asyncio
    async def test_caps_at_max_images(self) -> None:
        adapter = _make_adapter()
        adapter.send_image = AsyncMock()  # type: ignore[method-assign]
        urls = [f"https://img{i}.png" for i in range(10)]
        await adapter.send_media_group("+1", urls, caption="Album")
        # capped at WHATSAPP_MAX_IMAGES_PER_ALBUM (5)
        assert adapter.send_image.await_count == 5

    @pytest.mark.asyncio
    async def test_first_gets_caption_rest_dont(self) -> None:
        adapter = _make_adapter()
        adapter.send_image = AsyncMock()  # type: ignore[method-assign]
        await adapter.send_media_group("+1", ["https://a.png", "https://b.png"], caption="Cap")
        calls = adapter.send_image.call_args_list
        assert calls[0].args == ("+1", "https://a.png")
        assert calls[0].kwargs == {"caption": "Cap"}
        assert calls[1].kwargs == {"caption": ""}


# ---------------------------------------------------------------------------
# send_video
# ---------------------------------------------------------------------------


class TestSendVideo:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        result = await adapter.send_video("+1", "https://v.mp4", caption="vid")
        assert result is not None
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["type"] == "video"

    @pytest.mark.asyncio
    async def test_no_credentials(self) -> None:
        adapter = WhatsAppAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_video("+1", "https://v.mp4")
        assert result is None


# ---------------------------------------------------------------------------
# send_document
# ---------------------------------------------------------------------------


class TestSendDocument:
    @pytest.mark.asyncio
    async def test_success_extracts_filename(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        await adapter.send_document("+1", "https://cdn.com/file/report.pdf?token=abc", caption="Report")
        payload = adapter._client.post.call_args.kwargs["json"]
        assert payload["document"]["filename"] == "report.pdf"
        assert payload["document"]["caption"] == "Report"

    @pytest.mark.asyncio
    async def test_no_credentials(self) -> None:
        adapter = WhatsAppAdapter()
        adapter._client = AsyncMock()
        result = await adapter.send_document("+1", "https://doc.pdf")
        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_filename(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response())
        await adapter.send_document("+1", "https://cdn.com/?x=1")
        payload = adapter._client.post.call_args.kwargs["json"]
        # URL without a clear filename falls back to "document" or query part
        assert payload["document"]["filename"]


# ---------------------------------------------------------------------------
# send_voice
# ---------------------------------------------------------------------------


class TestSendVoice:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        # upload returns media id
        upload_resp = _ok_response({"id": "media-123"})
        send_resp = _ok_response()
        adapter._client.post = AsyncMock(side_effect=[upload_resp, send_resp])
        await adapter.send_voice("+1", b"audio-data")
        assert adapter._client.post.await_count == 2

    @pytest.mark.asyncio
    async def test_no_credentials(self) -> None:
        adapter = WhatsAppAdapter()
        adapter._client = AsyncMock()
        await adapter.send_voice("+1", b"data")
        adapter._client.post.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_upload_fails_sends_fallback_text(self) -> None:
        adapter = _make_adapter()
        # Upload fails
        adapter._upload_media = AsyncMock(return_value="")  # type: ignore[method-assign]
        adapter.send_text = AsyncMock()  # type: ignore[method-assign]
        await adapter.send_voice("+1", b"data")
        adapter.send_text.assert_awaited_once()


# ---------------------------------------------------------------------------
# _upload_media
# ---------------------------------------------------------------------------


class TestUploadMedia:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(return_value=_ok_response({"id": "m-456"}))
        media_id = await adapter._upload_media(b"audio", "audio/ogg")
        assert media_id == "m-456"

    @pytest.mark.asyncio
    async def test_error_returns_empty(self) -> None:
        adapter = _make_adapter()
        adapter._client.post = AsyncMock(side_effect=RuntimeError("fail"))
        media_id = await adapter._upload_media(b"audio", "audio/ogg")
        assert media_id == ""


# ---------------------------------------------------------------------------
# verify_signature
# ---------------------------------------------------------------------------


class TestVerifySignature:
    def test_valid_signature(self) -> None:
        body = b'{"test":"data"}'
        secret = "my-secret"
        sig = "sha256=" + hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert WhatsAppAdapter.verify_signature(body, sig, secret) is True

    def test_invalid_signature(self) -> None:
        assert WhatsAppAdapter.verify_signature(b"body", "sha256=wrong", "secret") is False

    def test_missing_secret(self) -> None:
        assert WhatsAppAdapter.verify_signature(b"body", "sha256=abc", "") is False

    def test_missing_signature(self) -> None:
        assert WhatsAppAdapter.verify_signature(b"body", "", "secret") is False

    def test_replay_protection_expired(self) -> None:
        body = b"body"
        secret = "sec"
        sig = "sha256=" + hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
        old_ts = str(int(time.time()) - 600)  # 10 min ago
        assert WhatsAppAdapter.verify_signature(body, sig, secret, timestamp=old_ts, max_age_seconds=300) is False

    def test_replay_protection_valid_timestamp(self) -> None:
        body = b"body"
        secret = "sec"
        sig = "sha256=" + hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
        ts = str(int(time.time()))
        assert WhatsAppAdapter.verify_signature(body, sig, secret, timestamp=ts) is True

    def test_non_numeric_timestamp_ignored(self) -> None:
        body = b"body"
        secret = "sec"
        sig = "sha256=" + hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
        # Non-numeric timestamp should not cause failure -- falls through to signature check
        assert WhatsAppAdapter.verify_signature(body, sig, secret, timestamp="not-a-number") is True


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


class TestProperties:
    def test_messages_url(self) -> None:
        adapter = WhatsAppAdapter(phone_number_id="pn999", access_token="tok")
        assert adapter._messages_url == f"{META_GRAPH_API}/pn999/messages"

    def test_headers(self) -> None:
        adapter = WhatsAppAdapter(phone_number_id="pn", access_token="tok-x")
        hdrs = adapter._headers
        assert hdrs["Authorization"] == "Bearer tok-x"
        assert hdrs["Content-Type"] == "application/json"


# ---------------------------------------------------------------------------
# close
# ---------------------------------------------------------------------------


class TestClose:
    @pytest.mark.asyncio
    async def test_close(self) -> None:
        adapter = _make_adapter()
        adapter._client.aclose = AsyncMock()
        await adapter.close()
        adapter._client.aclose.assert_awaited_once()
