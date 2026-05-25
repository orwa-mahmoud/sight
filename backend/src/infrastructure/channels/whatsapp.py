"""WhatsApp channel adapter using Meta Cloud API.

Ported from PropertyBot. Property-specific features (PropertyAlbum,
carousel, send_property_card) removed. General media support retained.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import time
from typing import TYPE_CHECKING, Any

import httpx
import structlog

from src.domain.shared.channel_result import ChannelSendResult
from src.domain.shared.media import ExtractedMedia
from src.infrastructure.channels.base import ChannelAdapter, IncomingMessage, MessageType
from src.infrastructure.channels.retry import (
    WHATSAPP_IMAGE_SEND_DELAY_SECONDS,
    WHATSAPP_MAX_IMAGES_PER_ALBUM,
    channel_send_retry,
)

if TYPE_CHECKING:
    from src.domain.tenant_config.entities import TenantConfig

logger = structlog.get_logger()

META_GRAPH_API = "https://graph.facebook.com/v23.0"

_HTTP_TIMEOUT = 30.0


def _extract_first_message(raw_payload: dict[str, Any]) -> dict[str, Any] | None:
    """Extract the first message dict from a Meta webhook payload, or None."""
    entries = raw_payload.get("entry", [])
    if not entries:
        return None
    changes_list = entries[0].get("changes", [])
    if not changes_list:
        return None
    messages = changes_list[0].get("value", {}).get("messages", [])
    return messages[0] if messages else None


class WhatsAppAdapter(ChannelAdapter):
    """WhatsApp channel adapter via Meta Cloud API."""

    channel_name = "whatsapp"

    def __init__(
        self,
        tenant_config: TenantConfig | None = None,
        *,
        phone_number_id: str = "",
        access_token: str = "",
    ):
        self._phone_number_id = phone_number_id
        self._access_token = access_token
        self._app_secret = ""
        self._verify_token = ""

        if tenant_config:
            self._phone_number_id = tenant_config.whatsapp_phone_number_id or ""
            self._access_token = tenant_config.whatsapp_access_token or ""
            self._verify_token = tenant_config.whatsapp_verify_token or ""

        if not self._phone_number_id or not self._access_token:
            logger.warning("whatsapp.no_credentials", msg="Meta WhatsApp credentials not configured")

        self._client = httpx.AsyncClient(
            headers=self._make_headers(),
            timeout=_HTTP_TIMEOUT,
        )

    def _make_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    @property
    def _headers(self) -> dict[str, str]:
        return self._make_headers()

    @property
    def _messages_url(self) -> str:
        return f"{META_GRAPH_API}/{self._phone_number_id}/messages"

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

    async def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        """Parse Meta Cloud API webhook payload."""
        msg = _extract_first_message(raw_payload)
        if msg is None:
            return IncomingMessage(channel="whatsapp", sender_phone="", text="")

        sender = msg.get("from", "")
        text, media_url, msg_type = await self._parse_message_content(msg)

        return IncomingMessage(
            channel="whatsapp",
            sender_phone=sender,
            message_type=msg_type,
            text=text,
            media_url=media_url,
            raw_payload=raw_payload,
        )

    async def _parse_message_content(self, msg: dict[str, Any]) -> tuple[str, str, MessageType]:
        """Extract text, media_url, and message type from a WhatsApp message."""
        msg_type_str = msg.get("type", "text")

        if msg_type_str == "text":
            return msg.get("text", {}).get("body", ""), "", MessageType.TEXT
        if msg_type_str == "audio":
            media_id = msg.get("audio", {}).get("id", "")
            media_url = await self._get_media_url(media_id) if media_id else ""
            return "", media_url, MessageType.VOICE
        if msg_type_str == "image":
            media_id = msg.get("image", {}).get("id", "")
            text = msg.get("image", {}).get("caption", "")
            media_url = await self._get_media_url(media_id) if media_id else ""
            return text, media_url, MessageType.IMAGE
        if msg_type_str == "interactive":
            interactive = msg.get("interactive", {})
            reply = interactive.get("button_reply") or interactive.get("list_reply") or {}
            return reply.get("title", ""), "", MessageType.TEXT
        if msg_type_str == "location":
            loc = msg.get("location", {})
            return f"Location: {loc.get('latitude', '')},{loc.get('longitude', '')}", "", MessageType.LOCATION
        return "", "", MessageType.TEXT

    async def _get_media_url(self, media_id: str) -> str:
        """Retrieve the download URL for a media object."""
        try:
            resp = await self._client.get(f"{META_GRAPH_API}/{media_id}")
            resp.raise_for_status()
            url: str = resp.json().get("url", "")
            return url
        except Exception as e:
            logger.error("whatsapp.media_url.error", error=str(e), media_id=media_id)
            return ""

    async def send_text(self, recipient: str, text: str) -> dict[str, Any] | None:
        """Send a text message via Meta Cloud API with retry on transient failures."""
        if not self._phone_number_id or not self._access_token:
            logger.warning("whatsapp.send.no_credentials", recipient=recipient)
            return None

        to_number = recipient.lstrip("+")
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "text",
            "text": {"body": text},
        }

        try:
            resp = await self._client.post(self._messages_url, json=payload)
            resp.raise_for_status()
            resp_json: dict[str, Any] = resp.json()
            logger.info("whatsapp.send.text", recipient=recipient, length=len(text))
            return resp_json
        except httpx.HTTPStatusError as e:
            body = e.response.text[:500] if e.response else ""
            logger.error(
                "whatsapp.send.error",
                error=str(e),
                recipient=recipient,
                response_body=body,
            )
            raise
        except Exception as e:
            logger.error("whatsapp.send.error", error=str(e), recipient=recipient)
            raise

    @channel_send_retry()
    async def send_image(  # type: ignore[override]
        self, recipient: str, image_url: str, caption: str = ""
    ) -> dict[str, Any] | None:
        """Send an image message via Meta Cloud API."""
        if not self._phone_number_id or not self._access_token:
            return None

        to_number = recipient.lstrip("+")
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "image",
            "image": {"link": image_url, "caption": caption},
        }

        try:
            resp = await self._client.post(self._messages_url, json=payload)
            resp.raise_for_status()
            resp_json: dict[str, Any] = resp.json()
            logger.info("whatsapp.send.image", recipient=recipient, url=image_url)
            return resp_json
        except httpx.HTTPStatusError as e:
            body = e.response.text[:500] if e.response else ""
            logger.error(
                "whatsapp.send_image.error",
                error=str(e),
                recipient=recipient,
                url=image_url,
                response_body=body,
            )
            raise
        except Exception as e:
            logger.error("whatsapp.send_image.error", error=str(e), recipient=recipient, url=image_url)
            raise

    async def send_media_group(self, recipient: str, image_urls: list[str], caption: str = "") -> None:
        """Send multiple images. WhatsApp has no album API -- send first with caption, rest without."""
        images = image_urls[:WHATSAPP_MAX_IMAGES_PER_ALBUM]
        if len(image_urls) > WHATSAPP_MAX_IMAGES_PER_ALBUM:
            logger.info(
                "whatsapp.album.capped",
                recipient=recipient,
                total=len(image_urls),
                sent=WHATSAPP_MAX_IMAGES_PER_ALBUM,
            )
        for i, url in enumerate(images):
            if i > 0:
                await asyncio.sleep(WHATSAPP_IMAGE_SEND_DELAY_SECONDS)
            await self.send_image(recipient, url, caption=caption if i == 0 else "")

    async def send_structured(
        self,
        recipient: str,
        clean_text: str,
        media: ExtractedMedia | None = None,
    ) -> ChannelSendResult:
        """Send pre-extracted text + media."""
        return await super().send_structured(recipient, clean_text, media)

    @channel_send_retry()
    async def send_video(  # type: ignore[override]
        self, recipient: str, video_url: str, caption: str = ""
    ) -> dict[str, Any] | None:
        """Send a video message via Meta Cloud API."""
        if not self._phone_number_id or not self._access_token:
            return None

        to_number = recipient.lstrip("+")
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "video",
            "video": {"link": video_url, "caption": caption},
        }

        try:
            resp = await self._client.post(self._messages_url, json=payload)
            resp.raise_for_status()
            resp_json: dict[str, Any] = resp.json()
            logger.info("whatsapp.send.video", recipient=recipient, url=video_url)
            return resp_json
        except httpx.HTTPStatusError as e:
            body = e.response.text[:500] if e.response else ""
            logger.error(
                "whatsapp.send_video.error",
                error=str(e),
                recipient=recipient,
                url=video_url,
                response_body=body,
            )
            raise
        except Exception as e:
            logger.error("whatsapp.send_video.error", error=str(e), recipient=recipient, url=video_url)
            raise

    @channel_send_retry()
    async def send_document(  # type: ignore[override]
        self, recipient: str, document_url: str, caption: str = ""
    ) -> dict[str, Any] | None:
        """Send a document message via Meta Cloud API."""
        if not self._phone_number_id or not self._access_token:
            return None

        to_number = recipient.lstrip("+")
        filename = document_url.rsplit("/", 1)[-1].split("?", maxsplit=1)[0] or "document"
        payload = {
            "messaging_product": "whatsapp",
            "to": to_number,
            "type": "document",
            "document": {"link": document_url, "caption": caption, "filename": filename},
        }

        try:
            resp = await self._client.post(self._messages_url, json=payload)
            resp.raise_for_status()
            resp_json: dict[str, Any] = resp.json()
            logger.info("whatsapp.send.document", recipient=recipient, url=document_url)
            return resp_json
        except httpx.HTTPStatusError as e:
            body = e.response.text[:500] if e.response else ""
            logger.error(
                "whatsapp.send_document.error",
                error=str(e),
                recipient=recipient,
                url=document_url,
                response_body=body,
            )
            raise
        except Exception as e:
            logger.error("whatsapp.send_document.error", error=str(e), recipient=recipient, url=document_url)
            raise

    @channel_send_retry()
    async def send_voice(self, recipient: str, audio: bytes, mime_type: str = "audio/ogg") -> None:
        """Send a voice message via Meta Cloud API (upload then send)."""
        if not self._phone_number_id or not self._access_token:
            logger.warning("whatsapp.send_voice.no_credentials", recipient=recipient)
            return

        try:
            media_id = await self._upload_media(audio, mime_type)
            if not media_id:
                await self.send_text(recipient, "[Voice message could not be sent]")
                return

            to_number = recipient.lstrip("+")
            payload: dict[str, Any] = {
                "messaging_product": "whatsapp",
                "to": to_number,
                "type": "audio",
                "audio": {"id": media_id},
            }

            resp = await self._client.post(self._messages_url, json=payload)
            resp.raise_for_status()
            logger.info("whatsapp.send.voice", recipient=recipient, size=len(audio))
        except Exception as e:
            logger.error("whatsapp.send_voice.error", error=str(e), recipient=recipient)
            await self.send_text(recipient, "[Voice message could not be sent]")

    @channel_send_retry()
    async def _upload_media(self, data: bytes, mime_type: str) -> str:
        """Upload media to Meta and return the media ID."""
        upload_url = f"{META_GRAPH_API}/{self._phone_number_id}/media"
        try:
            resp = await self._client.post(
                upload_url,
                headers={"Authorization": f"Bearer {self._access_token}"},
                data={"messaging_product": "whatsapp", "type": mime_type},
                files={"file": ("audio.ogg", data, mime_type)},
            )
            resp.raise_for_status()
            media_id: str = resp.json().get("id", "")
            return media_id
        except Exception as e:
            logger.error("whatsapp.upload_media.error", error=str(e))
            return ""

    @channel_send_retry()
    async def _post_with_retry(self, url: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST with automatic retry on transient network failures. Returns response JSON."""
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        result: dict[str, Any] = resp.json()
        return result

    @staticmethod
    def verify_signature(
        payload_body: bytes,
        signature: str,
        app_secret: str,
        timestamp: str | None = None,
        max_age_seconds: int = 300,
    ) -> bool:
        """Verify Meta webhook signature (X-Hub-Signature-256) with optional replay protection."""
        if not app_secret or not signature:
            logger.warning("whatsapp.verify_signature.missing", has_secret=bool(app_secret), has_sig=bool(signature))
            return False

        # Replay protection: reject webhooks older than max_age_seconds
        if timestamp:
            try:
                ts = int(timestamp)
                if abs(time.time() - ts) > max_age_seconds:
                    logger.warning("whatsapp.verify_signature.expired", timestamp=ts, max_age=max_age_seconds)
                    return False
            except (ValueError, TypeError):
                pass  # Non-numeric timestamp -- skip replay check, rely on signature

        expected = "sha256=" + hmac.new(app_secret.encode(), payload_body, hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, signature)
