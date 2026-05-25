"""Unit tests for the remove_key_fact AI tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.ai.tools.remove_key_fact import run_remove_key_fact


@pytest.mark.asyncio
async def test_remove_key_fact_empty_key() -> None:
    uow = MagicMock()
    result = await run_remove_key_fact(
        arguments={"key": "  "},
        tenant_id=uuid4(),
        contact_id=uuid4(),
        uow=uow,
    )
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_remove_key_fact_not_found() -> None:
    uow = MagicMock()
    uow.key_facts.get = AsyncMock(return_value=None)

    result = await run_remove_key_fact(
        arguments={"key": "name"},
        tenant_id=uuid4(),
        contact_id=uuid4(),
        uow=uow,
    )
    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_remove_key_fact_success() -> None:
    fact = MagicMock()
    fact.id = uuid4()

    uow = MagicMock()
    uow.key_facts.get = AsyncMock(return_value=fact)
    uow.key_facts.delete = AsyncMock()

    result = await run_remove_key_fact(
        arguments={"key": "  Name  "},
        tenant_id=uuid4(),
        contact_id=uuid4(),
        uow=uow,
    )
    assert result["status"] == "removed"
    assert result["key"] == "name"
    uow.key_facts.delete.assert_awaited_once_with(fact.id)
