"""Unit tests for the conversation history loader."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from src.ai.context.history import STALE_THRESHOLD, _format_gap, _inject_staleness_hint
from src.application.conversations.dtos import ThreadMessageDTO
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole


def _make_dto(
    role: str = "user",
    content: str = "hello",
    created_at: datetime | None = None,
    hidden: bool = False,
    is_checkpoint: bool = False,
) -> ThreadMessageDTO:
    from uuid import uuid4  # noqa: PLC0415

    return ThreadMessageDTO(
        id=uuid4(),
        role=role,
        content=content,
        hidden=hidden,
        tool_call_id=None,
        tool_args=None,
        tool_result=None,
        is_compressed=False,
        compressed_summary=None,
        is_checkpoint=is_checkpoint,
        token_count=5,
        request_id=None,
        created_at=created_at or datetime.now(UTC),
    )


def test_format_gap_minutes() -> None:
    assert _format_gap(timedelta(minutes=15)) == "15 minutes"


def test_format_gap_hours() -> None:
    assert _format_gap(timedelta(hours=3)) == "3 hours"


def test_format_gap_single_hour() -> None:
    assert _format_gap(timedelta(hours=1)) == "1 hour"


def test_format_gap_days() -> None:
    assert _format_gap(timedelta(days=2)) == "2 days"


def test_staleness_hint_injected_when_stale() -> None:
    old_time = datetime.now(UTC) - STALE_THRESHOLD - timedelta(minutes=5)
    dtos = [_make_dto(created_at=old_time)]
    messages: list[LLMMessage] = [LLMMessage(role=LLMMessageRole.USER, content="hi")]
    _inject_staleness_hint(messages, dtos)
    assert len(messages) == 2
    assert messages[0].role == LLMMessageRole.SYSTEM
    assert "returning conversation" in messages[0].content


def test_staleness_hint_not_injected_when_recent() -> None:
    recent = datetime.now(UTC) - timedelta(minutes=5)
    dtos = [_make_dto(created_at=recent)]
    messages: list[LLMMessage] = [LLMMessage(role=LLMMessageRole.USER, content="hi")]
    _inject_staleness_hint(messages, dtos)
    assert len(messages) == 1


def test_staleness_hint_no_timestamps() -> None:
    dtos: list[ThreadMessageDTO] = []
    messages: list[LLMMessage] = [LLMMessage(role=LLMMessageRole.USER, content="hi")]
    _inject_staleness_hint(messages, dtos)
    assert len(messages) == 1
