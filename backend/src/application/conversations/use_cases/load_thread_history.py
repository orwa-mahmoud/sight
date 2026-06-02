"""LoadThreadHistory — fetch messages for a thread as DTOs."""

from __future__ import annotations

from src.application.conversations.dtos import ThreadMessageDTO
from src.application.conversations.queries import LoadThreadHistory
from src.application.shared.unit_of_work import UnitOfWork


class LoadThreadHistoryUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, query: LoadThreadHistory) -> list[ThreadMessageDTO]:
        conversation = await self._uow.conversations.get_by_thread_id(query.thread_id)
        if conversation is None:
            return []

        if query.from_last_checkpoint:
            # Bounded load: checkpoint summary (if any) + messages since it.
            messages = await self._uow.messages.list_since_last_checkpoint(conversation.id)
        else:
            messages = await self._uow.messages.list_for_conversation(
                conversation.id,
                limit=query.limit,
                include_hidden=query.include_hidden,
            )
        return [
            ThreadMessageDTO(
                id=m.id,
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
                created_at=m.created_at,
            )
            for m in messages
        ]
