"""Telegram channel adapter using the Bot API.

Ported from PropertyBot. Property-specific features (PropertyAlbum)
removed. General media support (images, albums, video, document, voice) retained.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Coroutine
from typing import Any, Protocol

import httpx
import structlog

from src.infrastructure.channels.base import ChannelAdapter, IncomingMessage, MessageType
from src.infrastructure.channels.retry import channel_send_retry

logger = structlog.get_logger()

_TG_API = "https://api.telegram.org/bot{token}/{method}"

_HTTP_TIMEOUT = 30.0

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags from text for plain-text fallback."""
    return _HTML_TAG_RE.sub("", text)


def _build_media_items(image_urls: list[str], caption: str, *, html: bool) -> list[dict[str, Any]]:
    """Build Telegram media items list, optionally with HTML parse_mode."""
    media: list[dict[str, Any]] = []
    for i, url in enumerate(image_urls):
        item: dict[str, Any] = {"type": "photo", "media": url}
        if i == 0 and caption:
            item["caption"] = (_strip_html(caption) if not html else caption)[:1024]
            if html:
                item["parse_mode"] = "HTML"
        media.append(item)
    return media


def _extract_tg_message_id(resp_json: dict[str, Any]) -> str:
    """Extract Telegram message_id from API response."""
    result = resp_json.get("result", {})
    if isinstance(result, dict):
        mid = result.get("message_id", "")
        return str(mid) if mid else ""
    return ""


class _TenantConfigLike(Protocol):
    """Protocol for tenant config with telegram_bot_token."""

    telegram_bot_token: str | None


class TelegramAdapter(ChannelAdapter):
    """Telegram channel adapter using the Bot API."""

    channel_name = "telegram"

    def __init__(self, tenant_config: _TenantConfigLike | None = None):
        self._token = ""
        if tenant_config and tenant_config.telegram_bot_token:
            self._token = tenant_config.telegram_bot_token
        if not self._token:
            logger.warning("telegram.no_token", msg="Telegram bot token not configured for this tenant")

        self._client = httpx.AsyncClient(timeout=_HTTP_TIMEOUT)

    def _api_url(self, method: str) -> str:
        return _TG_API.format(token=self._token, method=method)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        """Parse Telegram webhook update payload."""
        message = raw_payload.get("message", {})
        from_user = message.get("from", {})
        chat = message.get("chat", {})

        msg_type = MessageType.TEXT
        text = message.get("text", "")
        media_url = ""

        if "voice" in message:
            msg_type = MessageType.VOICE
            file_id = message["voice"].get("file_id", "")
            if file_id:
                media_url = await self.get_file_url(file_id)
        elif "audio" in message:
            msg_type = MessageType.VOICE
            file_id = message["audio"].get("file_id", "")
            if file_id:
                media_url = await self.get_file_url(file_id)
        elif message.get("photo"):
            msg_type = MessageType.IMAGE
            file_id = message["photo"][-1].get("file_id", "")
            if file_id:
                media_url = await self.get_file_url(file_id)

        chat_id = str(chat.get("id", ""))

        return IncomingMessage(
            channel="telegram",
            sender_phone=chat_id,
            message_type=msg_type,
            text=text,
            media_url=media_url,
            raw_payload=raw_payload,
            metadata={
                "telegram_chat_id": chat_id,
                "telegram_user_id": str(from_user.get("id", "")),
            },
        )

    async def send_text(self, recipient: str, text: str, remove_keyboard: bool = False) -> dict[str, Any] | None:
        """Send a text message via Telegram with retry on transient failures.

        Falls back to plain text (no HTML parsing) if Telegram rejects the HTML.
        """
        if not self._token:
            logger.warning("telegram.send.no_token", recipient=recipient)
            return None

        last_resp: dict[str, Any] | None = None
        chunks = [text[i : i + 4096] for i in range(0, len(text), 4096)]

        for chunk in chunks:
            payload: dict[str, Any] = {
                "chat_id": recipient,
                "text": chunk,
                "parse_mode": "HTML",
            }
            if remove_keyboard:
                payload["reply_markup"] = {"remove_keyboard": True}
            try:
                resp_json: dict[str, Any] = await self._post_with_retry("sendMessage", payload)
                last_resp = resp_json
                logger.info("telegram.send.text", chat_id=recipient, length=len(chunk))
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 400:
                    logger.warning("telegram.send.html_fallback", chat_id=recipient)
                    last_resp = await self._send_text_plain(recipient, chunk, remove_keyboard)
                else:
                    logger.error("telegram.send.error", error=str(e), chat_id=recipient)
                    raise
            except Exception as e:
                logger.error("telegram.send.error", error=str(e), chat_id=recipient)
                raise

        return last_resp

    async def _send_text_plain(self, recipient: str, text: str, remove_keyboard: bool = False) -> dict[str, Any] | None:
        """Fallback: send text with HTML tags stripped and no parse_mode."""
        plain = _strip_html(text)
        payload: dict[str, Any] = {"chat_id": recipient, "text": plain}
        if remove_keyboard:
            payload["reply_markup"] = {"remove_keyboard": True}
        try:
            resp_json: dict[str, Any] = await self._post_with_retry("sendMessage", payload)
            logger.info("telegram.send.text_plain", chat_id=recipient, length=len(plain))
            return resp_json
        except Exception as e:
            logger.error("telegram.send.plain_error", error=str(e), chat_id=recipient)
            return None

    @channel_send_retry()
    async def send_contact_request(self, recipient: str, text: str | None = None) -> None:
        """Send a message with a 'Share Your Phone Number' button."""
        if not self._token:
            logger.warning("telegram.send_contact_request.no_token", recipient=recipient)
            return

        if not text:
            text = "To help you better, I need your phone number.\n\nPlease tap the button below to share your contact."

        try:
            response = await self._client.post(
                self._api_url("sendMessage"),
                json={
                    "chat_id": recipient,
                    "text": text,
                    "reply_markup": {
                        "keyboard": [[{"text": "Share My Phone Number", "request_contact": True}]],
                        "one_time_keyboard": True,
                        "resize_keyboard": True,
                    },
                },
            )
            response.raise_for_status()
            logger.info("telegram.send.contact_request", chat_id=recipient)
        except Exception as e:
            logger.error("telegram.send_contact_request.error", error=str(e), chat_id=recipient)

    @channel_send_retry()
    async def send_image(self, recipient: str, image_url: str, caption: str = "") -> dict[str, Any] | None:
        """Send an image via Telegram sendPhoto API."""
        if not self._token:
            logger.warning("telegram.send_image.no_token", recipient=recipient)
            return None

        payload: dict[str, Any] = {"chat_id": recipient, "photo": image_url}
        if caption:
            payload["caption"] = caption[:1024]
            payload["parse_mode"] = "HTML"

        resp = await self._client.post(self._api_url("sendPhoto"), json=payload)
        resp.raise_for_status()
        resp_json: dict[str, Any] = resp.json()
        logger.info("telegram.send.image", chat_id=recipient, url=image_url)
        return resp_json

    async def send_media_group(self, recipient: str, image_urls: list[str], caption: str = "") -> dict[str, Any] | None:
        """Send multiple images as a Telegram album via sendMediaGroup.

        Falls back to plain-text caption if Telegram rejects the HTML.
        """
        if not self._token:
            logger.warning("telegram.send_media_group.no_token", recipient=recipient)
            return None
        if not image_urls:
            return None

        media = _build_media_items(image_urls, caption, html=True)
        payload: dict[str, Any] = {"chat_id": recipient, "media": media}
        try:
            resp_json: dict[str, Any] = await self._post_with_retry("sendMediaGroup", payload)
            logger.info("telegram.send.media_group", chat_id=recipient, count=len(image_urls))
            return resp_json
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 400:
                return await self._send_media_group_plain(recipient, image_urls, caption)
            logger.error("telegram.send_media_group.error", error=str(e), chat_id=recipient)
        except Exception as e:
            logger.error("telegram.send_media_group.error", error=str(e), chat_id=recipient)
        return None

    async def _send_media_group_plain(
        self, recipient: str, image_urls: list[str], caption: str
    ) -> dict[str, Any] | None:
        """Fallback: send media group with plain-text caption."""
        logger.warning("telegram.send_media_group.html_fallback", chat_id=recipient)
        plain_media = _build_media_items(image_urls, caption, html=False)
        plain_payload: dict[str, Any] = {"chat_id": recipient, "media": plain_media}
        try:
            resp_json: dict[str, Any] = await self._post_with_retry("sendMediaGroup", plain_payload)
            logger.info("telegram.send.media_group_plain", chat_id=recipient, count=len(image_urls))
            return resp_json
        except Exception as e2:
            logger.error("telegram.send_media_group.plain_error", error=str(e2), chat_id=recipient)
            return None

    @channel_send_retry()
    async def send_video(self, recipient: str, video_url: str, caption: str = "") -> dict[str, Any] | None:
        """Send a video via Telegram sendVideo API."""
        if not self._token:
            logger.warning("telegram.send_video.no_token", recipient=recipient)
            return None

        payload: dict[str, Any] = {"chat_id": recipient, "video": video_url}
        if caption:
            payload["caption"] = caption[:1024]
            payload["parse_mode"] = "HTML"

        resp = await self._client.post(self._api_url("sendVideo"), json=payload)
        resp.raise_for_status()
        resp_json: dict[str, Any] = resp.json()
        logger.info("telegram.send.video", chat_id=recipient, url=video_url)
        return resp_json

    @channel_send_retry()
    async def send_document(self, recipient: str, document_url: str, caption: str = "") -> dict[str, Any] | None:
        """Send a document via Telegram sendDocument API."""
        if not self._token:
            logger.warning("telegram.send_document.no_token", recipient=recipient)
            return None

        payload: dict[str, Any] = {"chat_id": recipient, "document": document_url}
        if caption:
            payload["caption"] = caption[:1024]
            payload["parse_mode"] = "HTML"

        resp = await self._client.post(self._api_url("sendDocument"), json=payload)
        resp.raise_for_status()
        resp_json: dict[str, Any] = resp.json()
        logger.info("telegram.send.document", chat_id=recipient, url=document_url)
        return resp_json

    @channel_send_retry()
    async def send_voice(self, recipient: str, audio: bytes, mime_type: str = "audio/ogg") -> None:
        """Send a voice message via Telegram."""
        if not self._token:
            logger.warning("telegram.send_voice.no_token", recipient=recipient)
            return

        try:
            response = await self._client.post(
                self._api_url("sendVoice"),
                data={"chat_id": recipient},
                files={"voice": ("voice.ogg", audio, mime_type)},
            )
            response.raise_for_status()
            logger.info("telegram.send.voice", chat_id=recipient, size=len(audio))
        except Exception as e:
            logger.error("telegram.send_voice.error", error=str(e), chat_id=recipient)

    @channel_send_retry()
    async def _post_with_retry(self, method: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST with automatic retry on transient network failures. Returns response JSON."""
        resp = await self._client.post(self._api_url(method), json=payload)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    async def get_file_url(self, file_id: str) -> str:
        """Get the download URL for a Telegram file."""
        if not self._token:
            return ""

        try:
            response = await self._client.get(
                self._api_url("getFile"),
                params={"file_id": file_id},
            )
            response.raise_for_status()
            file_path = response.json().get("result", {}).get("file_path", "")
            if file_path:
                return f"https://api.telegram.org/file/bot{self._token}/{file_path}"
        except Exception as e:
            logger.error("telegram.get_file.error", error=str(e), file_id=file_id)

        return ""

    async def handle_webhook(
        self,
        raw_payload: dict[str, Any],
        tenant_id: str,
        chat_fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]] | None = None,
    ) -> None:
        """Handle Telegram webhook update."""
        if "message" not in raw_payload:
            logger.debug("telegram.webhook.skip", update_type=list(raw_payload.keys()))
            return

        incoming = await self.parse_incoming(raw_payload)
        await self.process_message(incoming, tenant_id, chat_fn=chat_fn)
