"""Notification routing port -- determines how to reach a recipient."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class ResolvedRoute:
    """Result of resolving how to reach a recipient."""

    channel: str  # "whatsapp", "telegram", "api"
    thread_id: str  # conversation thread_id to send in
    conversation_id: UUID | None = None  # existing conversation, if found
    tenant_id: UUID | None = None
    recipient_id: UUID | None = None


class NotificationRoutingError(Exception):
    """Raised when no delivery channel could be resolved for a recipient."""

    def __init__(self, reason: str, *, context_data: dict[str, Any] | None = None) -> None:
        self.reason = reason
        self.context_data = context_data or {}
        super().__init__(reason)


class NotificationRoutingPort(ABC):
    """Port for resolving the best delivery channel for a notification recipient.

    Generic -- works for any entity type. Caller provides tenant_id +
    recipient details directly.

    Fallback chain:
    1. Most recent conversation for this recipient+tenant -> send there
    2. Tenant has WhatsApp configured -> create WhatsApp thread
    3. Recipient has telegram_user_id -> create Telegram thread
    4. Raise NotificationRoutingError
    """

    @abstractmethod
    async def resolve_route(
        self,
        *,
        tenant_id: UUID,
        recipient_id: UUID,
        recipient_type: str,
    ) -> ResolvedRoute: ...
