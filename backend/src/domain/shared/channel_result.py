"""Channel send result -- value object returned by all adapter send methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ChannelSendResult:
    """Result of sending a message through a channel adapter.

    Captures delivery status and the raw channel API response for tracking.
    """

    status: str = "sent"  # "sent" | "failed"
    external_message_id: str = ""  # wamid.xxx or telegram message_id
    channel_response: dict[str, Any] | None = None  # raw API response JSON
    error: str = ""  # error message if failed
    errors: list[str] = field(default_factory=list)  # per-item errors

    @property
    def is_sent(self) -> bool:
        return self.status == "sent"

    @classmethod
    def sent(
        cls,
        *,
        external_message_id: str = "",
        channel_response: dict[str, Any] | None = None,
    ) -> ChannelSendResult:
        return cls(
            status="sent",
            external_message_id=external_message_id,
            channel_response=channel_response,
        )

    @classmethod
    def failed(cls, *, error: str = "", channel_response: dict[str, Any] | None = None) -> ChannelSendResult:
        return cls(
            status="failed",
            error=error,
            channel_response=channel_response,
        )
