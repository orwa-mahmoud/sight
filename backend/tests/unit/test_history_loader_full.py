"""Full tests for the history loader — covers the _build_messages path."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from src.ai.context.history import _build_messages
from src.application.conversations.dtos import ThreadMessageDTO


def _dto(
    role: str = "user",
    content: str = "hello",
    hidden: bool = False,
    is_checkpoint: bool = False,
    tool_call_id: str | None = None,
    compressed: bool = False,
    compressed_summary: str | None = None,
) -> ThreadMessageDTO:
    return ThreadMessageDTO(
        id=uuid4(),
        role=role,
        content=content,
        hidden=hidden,
        tool_call_id=tool_call_id,
        tool_args=None,
        tool_result=None,
        is_compressed=compressed,
        compressed_summary=compressed_summary,
        is_checkpoint=is_checkpoint,
        token_count=5,
        request_id=None,
        created_at=datetime.now(UTC),
    )


def test_build_messages_basic() -> None:
    dtos = [_dto("user", "hi"), _dto("assistant", "hello")]
    msgs = _build_messages(dtos)
    assert len(msgs) == 2
    assert msgs[0].content == "hi"
    assert msgs[1].content == "hello"


def test_build_messages_skips_hidden_non_checkpoint() -> None:
    dtos = [_dto("user", "hi"), _dto("tool", "result", hidden=True)]
    msgs = _build_messages(dtos)
    assert len(msgs) == 1


def test_build_messages_includes_checkpoint() -> None:
    dtos = [_dto("assistant", "checkpoint text", hidden=True, is_checkpoint=True)]
    msgs = _build_messages(dtos)
    assert len(msgs) == 1


def test_build_messages_uses_compressed_summary() -> None:
    dtos = [_dto("assistant", "original", compressed=True, compressed_summary="summary version")]
    msgs = _build_messages(dtos)
    assert msgs[0].content == "summary version"


def test_build_messages_skips_empty_content_no_tool() -> None:
    dtos = [_dto("assistant", "")]
    msgs = _build_messages(dtos)
    assert len(msgs) == 0


def test_build_messages_keeps_empty_content_with_tool_call_id() -> None:
    dtos = [_dto("assistant", "", tool_call_id="call_1")]
    msgs = _build_messages(dtos)
    assert len(msgs) == 1
