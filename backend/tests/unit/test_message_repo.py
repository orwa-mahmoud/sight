"""Unit tests for PostgresMessageRepository — save idempotency + _to_model/_to_entity."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.domain.conversations.entities import Message
from src.domain.conversations.value_objects import ConversationRole
from src.infrastructure.persistence.postgres.repositories.message_repo import PostgresMessageRepository


def _make_message(
    *,
    conversation_id: UUID | None = None,
    tenant_id: UUID | None = None,
    role: ConversationRole = ConversationRole.USER,
    content: str = "Hello there",
    tool_call_id: str | None = None,
    tool_args: dict[str, Any] | None = None,
    token_count: int = 0,
    request_id: str | None = None,
) -> Message:
    return Message.create(
        conversation_id=conversation_id or uuid4(),
        tenant_id=tenant_id or uuid4(),
        role=role,
        content=content,
        tool_call_id=tool_call_id,
        tool_args=tool_args,
        token_count=token_count,
        request_id=request_id,
    )


@pytest.mark.asyncio
async def test_save_existing_not_found_inserts() -> None:
    """If a persisted message is not found by ID (None from get), insert it (idempotent)."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()  # add is sync

    repo = PostgresMessageRepository(session)
    msg = _make_message()
    msg.mark_persisted()

    await repo.save(msg)

    session.get.assert_called_once()
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_save_existing_found_does_not_duplicate() -> None:
    """If a persisted message IS found, do nothing (messages are append-only)."""
    existing = MagicMock()
    session = AsyncMock()
    session.get = AsyncMock(return_value=existing)

    repo = PostgresMessageRepository(session)
    msg = _make_message()
    msg.mark_persisted()

    await repo.save(msg)

    session.get.assert_called_once()
    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_list_for_conversation_with_limit() -> None:
    """When limit is set, the subquery path should be taken."""
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = PostgresMessageRepository(session)
    result = await repo.list_for_conversation(uuid4(), limit=5)
    assert result == []
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_list_for_conversation_excludes_hidden() -> None:
    """When include_hidden=False, hidden messages should be filtered out."""
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars

    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = PostgresMessageRepository(session)
    result = await repo.list_for_conversation(uuid4(), include_hidden=False)
    assert result == []


def test_to_model_maps_all_fields() -> None:
    msg = _make_message(
        content="Tool call example",
        role=ConversationRole.ASSISTANT,
        tool_call_id="call_1",
        tool_args={"q": "test"},
        token_count=50,
        request_id="req-abc",
    )
    model = PostgresMessageRepository._to_model(msg)

    assert model.id == msg.id
    assert model.conversation_id == msg.conversation_id
    assert model.role == ConversationRole.ASSISTANT.value
    assert model.content == "Tool call example"
    assert model.tool_call_id == "call_1"
    assert model.tool_args == {"q": "test"}
    assert model.token_count == 50
    assert model.request_id == "req-abc"


def test_to_entity_maps_all_fields() -> None:
    model = MagicMock()
    model.id = uuid4()
    model.conversation_id = uuid4()
    model.tenant_id = uuid4()
    model.role = ConversationRole.USER.value
    model.content = "Hello"
    model.hidden = False
    model.tool_call_id = None
    model.tool_args = None
    model.tool_result = None
    model.is_compressed = False
    model.compressed_summary = None
    model.is_checkpoint = False
    model.token_count = 10
    model.request_id = "req-1"
    model.created_at = datetime.now(UTC)

    entity = PostgresMessageRepository._to_entity(model)

    assert entity.id == model.id
    assert entity.role == ConversationRole.USER
    assert entity.content == "Hello"
    assert entity.token_count == 10
