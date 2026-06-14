"""SaveThreadMessage — append a message, creating the conversation if missing."""

from __future__ import annotations

from src.application.conversations.commands import SaveThreadMessage
from src.application.conversations.dtos import SaveMessageResult
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.entities import Conversation, Message


class SaveThreadMessageUseCase:
    """Idempotent thread → conversation lookup, then message insert."""

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: SaveThreadMessage) -> SaveMessageResult:
        conversation = await self._uow.conversations.get_by_thread_id(cmd.thread_id)
        if conversation is None:
            conversation = Conversation.start(
                tenant_id=cmd.tenant_id,
                thread_id=cmd.thread_id,
                channel=cmd.channel,
                participant_id=cmd.participant_id,
            )
            await self._uow.conversations.save(conversation)
            await self._uow.flush()

        message = Message.create(
            conversation_id=conversation.id,
            tenant_id=cmd.tenant_id,
            role=cmd.role,
            content=cmd.content,
            hidden=cmd.hidden,
            tool_call_id=cmd.tool_call_id,
            tool_args=cmd.tool_args,
            tool_result=cmd.tool_result,
            is_checkpoint=cmd.is_checkpoint,
            token_count=cmd.token_count,
            request_id=cmd.request_id,
            provider_message_id=cmd.provider_message_id,
        )

        if cmd.provider_message_id is not None:
            # Durable, concurrency-safe de-dup at the DB. A redelivered webhook
            # (or a race) hits the unique index and is skipped — not reprocessed.
            inserted = await self._uow.messages.insert_if_new(message)
            if not inserted:
                return SaveMessageResult(message_id=message.id, conversation_id=conversation.id, is_duplicate=True)
        else:
            await self._uow.messages.save(message)

        conversation.touch()
        await self._uow.conversations.save(conversation)
        self._uow.track(conversation)
        self._uow.track(message)
        return SaveMessageResult(message_id=message.id, conversation_id=conversation.id)
