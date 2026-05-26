"""Abstract base class for all channel adapters.

Ported from PropertyBot with PropertyAlbum-specific methods removed.
Keeps the full media extraction + structured send infrastructure.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

import structlog

from src.domain.shared.channel_result import ChannelSendResult
from src.domain.shared.media import ExtractedMedia, MediaGroup, extract_media

logger = structlog.get_logger()


class MessageType(StrEnum):
    TEXT = "text"
    VOICE = "voice"
    IMAGE = "image"
    DOCUMENT = "document"
    LOCATION = "location"


@dataclass
class IncomingMessage:
    """Unified incoming message from any channel."""

    channel: str
    sender_phone: str
    message_type: MessageType = MessageType.TEXT
    text: str = ""
    media_url: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
    thread_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class OutgoingMessage:
    """Unified outgoing message to any channel."""

    text: str = ""
    voice_audio: bytes | None = None
    media_url: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ChannelAdapter(ABC):
    """Abstract base for all channel adapters."""

    channel_name: str = "base"

    @abstractmethod
    async def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage: ...

    @abstractmethod
    async def send_text(self, recipient: str, text: str) -> dict[str, Any] | None: ...

    @abstractmethod
    async def send_voice(self, recipient: str, audio: bytes, mime_type: str = "audio/ogg") -> None: ...

    async def send_image(self, recipient: str, image_url: str, caption: str = "") -> dict[str, Any] | None:
        """Send an image message. Override in subclasses that support native media."""
        text = f"{caption}\n{image_url}" if caption else image_url
        return await self.send_text(recipient, text)

    async def send_video(self, recipient: str, video_url: str, caption: str = "") -> dict[str, Any] | None:
        """Send a video message. Override in subclasses that support native media."""
        text = f"{caption}\n{video_url}" if caption else video_url
        return await self.send_text(recipient, text)

    async def send_document(self, recipient: str, document_url: str, caption: str = "") -> dict[str, Any] | None:
        """Send a document message. Override in subclasses that support native media."""
        text = f"{caption}\n{document_url}" if caption else document_url
        return await self.send_text(recipient, text)

    async def send_media_group(self, recipient: str, image_urls: list[str], caption: str = "") -> dict[str, Any] | None:
        """Send multiple images as an album. Override in subclasses that support native albums.

        Default: sends first image with caption, rest without.
        """
        for i, url in enumerate(image_urls):
            await self.send_image(recipient, url, caption=caption if i == 0 else "")
        return None

    async def send_structured(
        self,
        recipient: str,
        clean_text: str,
        media: ExtractedMedia | None = None,
    ) -> ChannelSendResult:
        """Send pre-extracted text + media. Returns delivery result with channel response."""
        errors: list[str] = []
        text_response = await self._send_text_safe(recipient, clean_text, errors)

        if media:
            await self._send_media_items(recipient, media, errors)

        if errors:
            return ChannelSendResult(
                status="failed" if not text_response else "sent",
                error="; ".join(errors),
                errors=errors,
                channel_response=text_response,
            )
        return ChannelSendResult.sent(channel_response=text_response)

    async def _send_text_safe(self, recipient: str, clean_text: str, errors: list[str]) -> dict[str, Any] | None:
        """Send text, appending errors on failure. Returns response dict or None."""
        if not clean_text.strip():
            return None
        try:
            return await self.send_text(recipient, clean_text.strip())
        except Exception as e:
            errors.append(f"text: {e}")
            return None

    async def _send_media_items(self, recipient: str, media: ExtractedMedia, errors: list[str]) -> None:
        """Send all media items, collecting errors."""
        for group in media.images:
            await self._safe_send(errors, "image", self._send_image_group, recipient, group)
        for group in media.videos:
            for url in group.urls:
                await self._safe_send(errors, "video", self.send_video, recipient, url, caption=group.caption)
        for group in media.documents:
            for url in group.urls:
                await self._safe_send(errors, "document", self.send_document, recipient, url, caption=group.caption)

    @staticmethod
    async def _safe_send(errors: list[str], label: str, fn: Any, *args: Any, **kwargs: Any) -> None:
        """Call fn, appending to errors on failure."""
        try:
            await fn(*args, **kwargs)
        except Exception as e:
            errors.append(f"{label}: {e}")

    async def send_response(self, recipient: str, response_text: str) -> ChannelSendResult:
        """Extract media blocks from LLM response and send text + native media.

        Convenience method -- extracts media then delegates to send_structured.
        """
        clean_text, media = extract_media(response_text)
        return await self.send_structured(recipient, clean_text, media if media.has_any() else None)

    async def _send_image_group(self, recipient: str, group: MediaGroup) -> None:
        """Send an image group: album if multiple URLs, single image otherwise."""
        if len(group.urls) > 1:
            await self.send_media_group(recipient, group.urls, caption=group.caption)
        else:
            for url in group.urls:
                await self.send_image(recipient, url, caption=group.caption)

    async def handle_webhook(
        self,
        raw_payload: dict[str, Any],
        tenant_id: str,
        chat_fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]] | None = None,
    ) -> Any:
        """Full webhook handler: parse -> process -> respond."""
        incoming = await self.parse_incoming(raw_payload)
        return await self.process_message(incoming, tenant_id, chat_fn=chat_fn)

    async def process_message(
        self,
        incoming: IncomingMessage,
        tenant_id: str,
        stt_keys: Any | None = None,
        chat_fn: Callable[..., Coroutine[Any, Any, dict[str, Any]]] | None = None,
    ) -> str:
        """Process a unified incoming message through the agent.

        Args:
            incoming: Parsed incoming message.
            tenant_id: Tenant UUID string.
            stt_keys: Optional STT keys for voice transcription. If None and message
                      is voice, the raw "[Voice message]" placeholder is used.
            chat_fn: The chat_with_agent callable. Injected by the caller to avoid
                     infrastructure importing from bootstrap.
        """
        if chat_fn is None:
            raise ValueError("chat_fn must be provided -- inject chat_with_agent from the caller.")

        text = incoming.text
        # Voice transcription: when STT is implemented, handle it here.
        # For now, voice messages pass through as-is (text may be empty).

        result = await chat_fn(
            message=text,
            tenant_id=tenant_id,
            phone=incoming.sender_phone,
            channel=self.channel_name,
        )

        response_text = str(result.get("response", ""))
        if response_text:
            await self.send_response(incoming.sender_phone, response_text)

        return response_text
