"""Conversation + Message repository ports."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from src.domain.conversations.entities import Conversation, Message


class ConversationRepository(Protocol):
    async def save(self, conversation: Conversation) -> None: ...

    async def get_by_id(self, conversation_id: UUID) -> Conversation | None: ...

    async def get_by_thread_id(self, thread_id: str) -> Conversation | None: ...

    async def list_for_tenant(self, tenant_id: UUID, *, limit: int = 100, offset: int = 0) -> list[Conversation]: ...

    async def count_active_since(self, tenant_id: UUID, since: datetime) -> int: ...


class MessageRepository(Protocol):
    async def save(self, message: Message) -> None: ...

    async def list_for_conversation(
        self,
        conversation_id: UUID,
        *,
        limit: int | None = None,
        include_hidden: bool = True,
    ) -> list[Message]: ...

    async def list_since_last_checkpoint(self, conversation_id: UUID) -> list[Message]: ...

    async def sum_tokens_since_checkpoint(self, conversation_id: UUID) -> int: ...

    async def count_visible_since(self, tenant_id: UUID, since: datetime) -> int: ...
