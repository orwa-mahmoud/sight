"""PostgreSQL Message repository — append-only with checkpoint-aware queries."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.conversations.entities import Message
from src.domain.conversations.value_objects import ConversationRole
from src.infrastructure.persistence.postgres.models.message import MessageModel


class PostgresMessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, message: Message) -> None:
        if message.is_new:
            self._session.add(self._to_model(message))
            message.mark_persisted()
            return
        # Messages are append-only in v1 — log + insert if missing to stay idempotent.
        existing = await self._session.get(MessageModel, message.id)
        if existing is None:
            self._session.add(self._to_model(message))

    async def insert_if_new(self, message: Message) -> bool:
        """Insert an inbound message, skipping if (conversation_id, provider_message_id)
        already exists. Returns True if inserted, False if it was a duplicate.

        Concurrency-safe: the partial unique index serializes concurrent inserts of
        the same provider id (the second blocks, then conflicts), so two duplicate
        webhooks racing can't both win — no SELECT-then-insert window to lose.
        """
        model = self._to_model(message)
        values = {col.name: getattr(model, col.name) for col in MessageModel.__table__.columns}
        stmt = (
            pg_insert(MessageModel)
            .values(**values)
            .on_conflict_do_nothing(
                index_elements=["conversation_id", "provider_message_id"],
                index_where=MessageModel.provider_message_id.isnot(None),
            )
            .returning(MessageModel.id)
        )
        inserted = (await self._session.execute(stmt)).scalar_one_or_none() is not None
        if inserted:
            message.mark_persisted()
        return inserted

    async def list_for_conversation(
        self,
        conversation_id: UUID,
        *,
        limit: int | None = None,
        include_hidden: bool = True,
    ) -> list[Message]:
        stmt = select(MessageModel).where(MessageModel.conversation_id == conversation_id)
        if not include_hidden:
            stmt = stmt.where(MessageModel.hidden.is_(False))
        stmt = stmt.order_by(MessageModel.created_at.asc(), MessageModel.id.asc())
        if limit:
            # Take the most recent N then reverse to chronological order. The id
            # tiebreaker makes the cut deterministic when rows share a created_at
            # (same-tick inserts), so "the most recent N" is stable.
            sub = stmt.order_by(desc(MessageModel.created_at), desc(MessageModel.id)).limit(limit).subquery()
            stmt = (
                select(MessageModel)
                .join(sub, MessageModel.id == sub.c.id)
                .order_by(MessageModel.created_at.asc(), MessageModel.id.asc())
            )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def list_since_last_checkpoint(self, conversation_id: UUID) -> list[Message]:
        """Return messages strictly newer than the most recent checkpoint row,
        plus the checkpoint itself at the head so the summarizer has its prior state."""
        checkpoint_stmt = (
            select(MessageModel.created_at)
            .where(
                MessageModel.conversation_id == conversation_id,
                MessageModel.is_checkpoint.is_(True),
            )
            .order_by(desc(MessageModel.created_at))
            .limit(1)
        )
        checkpoint_at = (await self._session.execute(checkpoint_stmt)).scalar_one_or_none()

        stmt = select(MessageModel).where(MessageModel.conversation_id == conversation_id)
        if checkpoint_at is not None:
            stmt = stmt.where(MessageModel.created_at >= checkpoint_at)
        stmt = stmt.order_by(MessageModel.created_at.asc(), MessageModel.id.asc())
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def sum_tokens_since_checkpoint(self, conversation_id: UUID) -> int:
        """Sum token_count of post-checkpoint messages to drive the next checkpoint trigger."""
        checkpoint_stmt = (
            select(MessageModel.created_at)
            .where(
                MessageModel.conversation_id == conversation_id,
                MessageModel.is_checkpoint.is_(True),
            )
            .order_by(desc(MessageModel.created_at))
            .limit(1)
        )
        checkpoint_at = (await self._session.execute(checkpoint_stmt)).scalar_one_or_none()

        stmt = select(func.coalesce(func.sum(MessageModel.token_count), 0)).where(
            MessageModel.conversation_id == conversation_id,
            MessageModel.is_checkpoint.is_(False),
        )
        if checkpoint_at is not None:
            stmt = stmt.where(MessageModel.created_at > checkpoint_at)
        result = await self._session.execute(stmt)
        return int(result.scalar_one())

    async def count_visible_since(self, tenant_id: UUID, since: datetime) -> int:
        result = await self._session.execute(
            select(func.count(MessageModel.id)).where(
                MessageModel.tenant_id == tenant_id,
                MessageModel.created_at >= since,
                MessageModel.hidden.is_(False),
            )
        )
        return int(result.scalar_one())

    # ── Mapping helpers ────────────────────────────────────────────
    @staticmethod
    def _to_model(m: Message) -> MessageModel:
        return MessageModel(
            id=m.id,
            conversation_id=m.conversation_id,
            tenant_id=m.tenant_id,
            role=m.role.value,
            content=m.content,
            hidden=m.hidden,
            tool_call_id=m.tool_call_id,
            tool_args=m.tool_args,
            tool_result=m.tool_result,
            is_compressed=m.is_compressed,
            compressed_summary=m.compressed_summary,
            is_checkpoint=m.is_checkpoint,
            token_count=m.token_count,
            request_id=m.request_id,
            provider_message_id=m.provider_message_id,
            created_at=m.created_at,
        )

    @staticmethod
    def _to_entity(m: MessageModel) -> Message:
        return Message(
            id=m.id,
            conversation_id=m.conversation_id,
            tenant_id=m.tenant_id,
            role=ConversationRole(m.role),
            content=m.content,
            hidden=m.hidden,
            tool_call_id=m.tool_call_id,
            tool_args=m.tool_args,
            tool_result=m.tool_result,
            is_compressed=m.is_compressed,
            compressed_summary=m.compressed_summary,
            is_checkpoint=m.is_checkpoint,
            token_count=m.token_count,
            request_id=m.request_id,
            provider_message_id=m.provider_message_id,
            created_at=m.created_at,
        )
