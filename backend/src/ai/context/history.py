"""Conversation history loader — builds the message list the LLM sees.

Loads messages from the DB (source of truth), maps ConversationRole to
OpenAI-style chat roles, and injects a staleness hint if the conversation
went quiet for more than 30 minutes (PropertyBot's pattern, generalized).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.application.conversations.dtos import ThreadMessageDTO
from src.application.conversations.queries import LoadThreadHistory
from src.application.conversations.use_cases.load_thread_history import LoadThreadHistoryUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole

_ROLE_MAP: dict[str, LLMMessageRole] = {
    "user": LLMMessageRole.USER,
    "assistant": LLMMessageRole.ASSISTANT,
    "system": LLMMessageRole.SYSTEM,
    "tool": LLMMessageRole.TOOL,
}

STALE_THRESHOLD = timedelta(minutes=30)


async def load_history(
    *,
    thread_id: str,
    uow: UnitOfWork,
    limit: int | None = None,
) -> list[LLMMessage]:
    dtos = await LoadThreadHistoryUseCase(uow=uow).execute(
        LoadThreadHistory(thread_id=thread_id, limit=limit, include_hidden=True)
    )
    messages = _build_messages(dtos)
    if messages:
        _inject_staleness_hint(messages, dtos)
    return messages


def _build_messages(dtos: list[ThreadMessageDTO]) -> list[LLMMessage]:
    messages: list[LLMMessage] = []
    for dto in dtos:
        role = _ROLE_MAP.get(dto.role, LLMMessageRole.USER)
        if not dto.content and not dto.tool_call_id:
            continue
        if dto.hidden and not dto.is_checkpoint:
            continue
        messages.append(
            LLMMessage(
                role=role,
                content=dto.compressed_summary if dto.is_compressed and dto.compressed_summary else dto.content,
                tool_call_id=dto.tool_call_id,
            )
        )
    return messages


def _inject_staleness_hint(messages: list[LLMMessage], dtos: list[ThreadMessageDTO]) -> None:
    last_ts = None
    for dto in reversed(dtos):
        if dto.created_at:
            last_ts = dto.created_at
            break
    if not last_ts:
        return
    gap = datetime.now(UTC) - last_ts
    if gap < STALE_THRESHOLD:
        return
    hint = _format_gap(gap)
    messages.insert(
        0,
        LLMMessage(
            role=LLMMessageRole.SYSTEM,
            content=(
                f"The last message in this conversation was {hint} ago. "
                "This is a returning conversation — do not re-introduce yourself. "
                "Greet them back naturally and pick up where you left off."
            ),
        ),
    )


def _format_gap(gap: timedelta) -> str:
    total_minutes = int(gap.total_seconds() // 60)
    if total_minutes < 60:
        return f"{total_minutes} minutes"
    hours = total_minutes // 60
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''}"
    days = hours // 24
    return f"{days} day{'s' if days != 1 else ''}"
