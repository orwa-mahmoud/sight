"""Conversation + Message aggregates.

A `Conversation` is the per-thread root; messages belong to it. `thread_id`
is the natural key derived from channel-specific identifiers (e.g. WhatsApp
phone + tenant) so channel webhooks can resolve the thread without a UUID.

Messages carry full provider-shape data:
- `tool_call_id`, `tool_args`, `tool_result` keep tool exchanges in their
  native format so the LLM sees them as `tool_use` / `tool_result` blocks
  on subsequent turns (avoids PropertyBot's lossy paraphrase pattern).
- `is_compressed` + `compressed_summary` are set when older tool turns
  get rolled up by the tiered-compression loader, while `tool_args` /
  `tool_result` are retained in JSONB for UUID-driven recovery if needed.
- `is_checkpoint` marks structured-state summary rows (PropertyBot's
  checkpoint pattern, generalized).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from src.domain.conversations.events import ConversationStarted, MessageSaved
from src.domain.conversations.value_objects import ConversationChannel, ConversationRole
from src.domain.shared.entities import BaseEntity


@dataclass(eq=False, kw_only=True)
class Conversation(BaseEntity):
    tenant_id: UUID
    thread_id: str
    channel: ConversationChannel
    participant_id: UUID | None
    created_at: datetime
    updated_at: datetime
    last_message_at: datetime | None = None

    @classmethod
    def start(
        cls,
        *,
        tenant_id: UUID,
        thread_id: str,
        channel: ConversationChannel,
        participant_id: UUID | None = None,
    ) -> Conversation:
        now = datetime.now(UTC)
        conv = cls(
            id=uuid4(),
            tenant_id=tenant_id,
            thread_id=thread_id,
            channel=channel,
            participant_id=participant_id,
            created_at=now,
            updated_at=now,
            last_message_at=None,
        )
        conv._is_new = True
        conv._emit(
            ConversationStarted(
                conversation_id=conv.id,
                tenant_id=tenant_id,
                thread_id=thread_id,
                channel=channel.value,
            )
        )
        return conv

    def touch(self) -> None:
        """Bump updated_at + last_message_at when a new message is saved."""
        now = datetime.now(UTC)
        self.updated_at = now
        self.last_message_at = now


@dataclass(eq=False, kw_only=True)
class Message(BaseEntity):
    conversation_id: UUID
    tenant_id: UUID
    role: ConversationRole
    content: str
    hidden: bool = False
    # ── Tool call shape (set when role=ASSISTANT emits tool_calls) ───
    tool_call_id: str | None = None
    tool_args: dict[str, Any] | None = None
    # ── Tool result (set when role=TOOL) ─────────────────────────────
    tool_result: dict[str, Any] | None = None
    # ── Tiered compression (set when rolled up) ──────────────────────
    is_compressed: bool = False
    compressed_summary: str | None = None
    # ── Structured checkpoint state (PropertyBot's pattern) ──────────
    is_checkpoint: bool = False
    # ── Approximate token count (set by caller for budget tracking) ──
    token_count: int = 0
    # ── End-to-end tracing ───────────────────────────────────────────
    request_id: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def create(
        cls,
        *,
        conversation_id: UUID,
        tenant_id: UUID,
        role: ConversationRole,
        content: str,
        hidden: bool = False,
        tool_call_id: str | None = None,
        tool_args: dict[str, Any] | None = None,
        tool_result: dict[str, Any] | None = None,
        is_checkpoint: bool = False,
        token_count: int = 0,
        request_id: str | None = None,
    ) -> Message:
        msg = cls(
            id=uuid4(),
            conversation_id=conversation_id,
            tenant_id=tenant_id,
            role=role,
            content=content,
            hidden=hidden,
            tool_call_id=tool_call_id,
            tool_args=tool_args,
            tool_result=tool_result,
            is_checkpoint=is_checkpoint,
            token_count=token_count,
            request_id=request_id,
            created_at=datetime.now(UTC),
        )
        msg._is_new = True
        msg._emit(
            MessageSaved(
                message_id=msg.id,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                role=role.value,
                request_id=request_id,
            )
        )
        return msg
