"""Unit tests for LoadThreadHistory use case."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.application.conversations.queries import LoadThreadHistory
from src.application.conversations.use_cases.load_thread_history import LoadThreadHistoryUseCase


@pytest.mark.asyncio
async def test_load_thread_history_no_conversation_returns_empty() -> None:
    """When thread_id maps to no conversation, return []."""
    uow = MagicMock()
    uow.conversations = MagicMock()
    uow.conversations.get_by_thread_id = AsyncMock(return_value=None)

    uc = LoadThreadHistoryUseCase(uow=uow)
    result = await uc.execute(LoadThreadHistory(thread_id="nonexistent-thread"))
    assert result == []


@pytest.mark.asyncio
async def test_load_thread_history_with_messages() -> None:
    """When a conversation exists, messages are mapped to DTOs."""
    conv = MagicMock()
    conv.id = uuid4()

    msg = MagicMock()
    msg.id = uuid4()
    msg.role = MagicMock()
    msg.role.value = "user"
    msg.content = "Hello"
    msg.hidden = False
    msg.tool_call_id = None
    msg.tool_args = None
    msg.tool_result = None
    msg.is_compressed = False
    msg.compressed_summary = None
    msg.is_checkpoint = False
    msg.token_count = 5
    msg.request_id = "r1"
    msg.created_at = MagicMock()

    uow = MagicMock()
    uow.conversations = MagicMock()
    uow.conversations.get_by_thread_id = AsyncMock(return_value=conv)
    uow.messages = MagicMock()
    uow.messages.list_for_conversation = AsyncMock(return_value=[msg])

    uc = LoadThreadHistoryUseCase(uow=uow)
    result = await uc.execute(LoadThreadHistory(thread_id="t-1", limit=10, include_hidden=True))
    assert len(result) == 1
    assert result[0].content == "Hello"
    assert result[0].role == "user"
