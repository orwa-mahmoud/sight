"""Unit tests for the remove_key_fact AI tool."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ai.tools.remove_key_fact import run_remove_key_fact


@pytest.mark.asyncio
async def test_remove_key_fact_empty_key() -> None:
    result = await run_remove_key_fact(
        arguments={"key": "  "},
        tenant_id=uuid4(),
        participant_identifier="+971",
        session=MagicMock(),
    )
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_remove_key_fact_not_found() -> None:
    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value=None)

    with patch("src.ai.tools.remove_key_fact.PostgresKeyFactRepository", return_value=mock_repo):
        result = await run_remove_key_fact(
            arguments={"key": "name"},
            tenant_id=uuid4(),
            participant_identifier="+971",
            session=MagicMock(),
        )
    assert result["status"] == "not_found"


@pytest.mark.asyncio
async def test_remove_key_fact_success() -> None:
    fact = MagicMock()
    fact.id = uuid4()

    mock_repo = MagicMock()
    mock_repo.get = AsyncMock(return_value=fact)
    mock_repo.delete = AsyncMock()

    with patch("src.ai.tools.remove_key_fact.PostgresKeyFactRepository", return_value=mock_repo):
        result = await run_remove_key_fact(
            arguments={"key": "  Name  "},
            tenant_id=uuid4(),
            participant_identifier="+971",
            session=MagicMock(),
        )
    assert result["status"] == "removed"
    assert result["key"] == "name"
    mock_repo.delete.assert_awaited_once_with(fact.id)
