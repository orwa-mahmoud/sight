"""Direct API channel adapter -- for REST API clients."""

from __future__ import annotations

from typing import Any

import structlog

from src.infrastructure.channels.base import ChannelAdapter, IncomingMessage, MessageType

logger = structlog.get_logger()


class DirectAPIAdapter(ChannelAdapter):
    """Direct API adapter for programmatic access."""

    channel_name = "api"

    async def parse_incoming(self, raw_payload: dict[str, Any]) -> IncomingMessage:
        """Parse a direct API request."""
        return IncomingMessage(
            channel="api",
            sender_phone=raw_payload.get("user_phone", ""),
            message_type=MessageType.TEXT,
            text=raw_payload.get("message", ""),
            thread_id=raw_payload.get("thread_id", ""),
            raw_payload=raw_payload,
        )

    async def send_text(self, recipient: str, text: str) -> None:
        """No-op for API channel -- response is returned in the HTTP response."""
        logger.debug("api.send.text", recipient=recipient, length=len(text))

    async def send_voice(self, recipient: str, audio: bytes, mime_type: str = "audio/ogg") -> None:
        """No-op for API channel."""
        logger.debug("api.send.voice", recipient=recipient, size=len(audio))
