"""Unit tests for gateway validation paths (no LLM call needed)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.shared.exceptions import InvalidOperationError


@pytest.mark.asyncio
async def test_gateway_rejects_missing_config() -> None:
    uow = MagicMock()
    uow.tenant_configs = MagicMock()
    uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=None)

    with pytest.raises(InvalidOperationError, match="configuration not found"):
        await chat_with_agent(
            ChatInput(
                message="hi",
                tenant_id=uuid4(),
                channel=ConversationChannel.WEB,
                sender_identifier="test@x.com",
            ),
            uow=uow,
        )


@pytest.mark.asyncio
async def test_gateway_rejects_empty_api_key() -> None:
    mock_config = MagicMock()
    mock_config.llm_api_key = ""

    uow = MagicMock()
    uow.tenant_configs = MagicMock()
    uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=mock_config)

    with pytest.raises(InvalidOperationError, match="API key not configured"):
        await chat_with_agent(
            ChatInput(
                message="hi",
                tenant_id=uuid4(),
                channel=ConversationChannel.WEB,
                sender_identifier="test@x.com",
            ),
            uow=uow,
        )
