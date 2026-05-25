"""Unit tests for PostgresTokenUsageRepository — save idempotency, list_for_tenant with since, aggregate."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.domain.llm_usage.entities import TokenUsage
from src.infrastructure.persistence.postgres.repositories.token_usage_repo import PostgresTokenUsageRepository


def _make_usage(
    *,
    tenant_id: UUID | None = None,
    provider: str = "openai",
    model: str = "gpt-4o-mini",
    input_tokens: int = 100,
    output_tokens: int = 50,
    cache_read_tokens: int = 0,
    source: str = "asker",
) -> TokenUsage:
    return TokenUsage.record(
        tenant_id=tenant_id or uuid4(),
        provider=provider,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_read_tokens=cache_read_tokens,
        source=source,
    )


@pytest.mark.asyncio
async def test_save_existing_not_found_inserts() -> None:
    """When a persisted usage row is not found by ID, insert it (upsert semantics)."""
    session = AsyncMock()
    session.get = AsyncMock(return_value=None)
    session.add = MagicMock()  # add is sync

    repo = PostgresTokenUsageRepository(session)
    usage = _make_usage()
    usage.mark_persisted()

    await repo.save(usage)

    session.get.assert_called_once()
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_save_existing_found_does_nothing() -> None:
    """When a persisted usage row IS found, do nothing (append-only)."""
    existing = MagicMock()
    session = AsyncMock()
    session.get = AsyncMock(return_value=existing)

    repo = PostgresTokenUsageRepository(session)
    usage = _make_usage()
    usage.mark_persisted()

    await repo.save(usage)

    session.add.assert_not_called()


@pytest.mark.asyncio
async def test_list_for_tenant_with_since_filter() -> None:
    """When since is provided, the query should include a date filter."""
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = []
    mock_result = MagicMock()
    mock_result.scalars.return_value = mock_scalars
    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = PostgresTokenUsageRepository(session)
    since = datetime(2024, 1, 1, tzinfo=UTC)
    result = await repo.list_for_tenant(uuid4(), since=since)

    assert result == []
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_aggregate_for_tenant_with_since() -> None:
    """aggregate_for_tenant with 'since' param executes and returns UsageStats."""
    mock_row = (100, 50, 10, Decimal("0.01"), Decimal("0.001"), Decimal("0.005"), 5)
    mock_result = MagicMock()
    mock_result.one.return_value = mock_row
    session = AsyncMock()
    session.execute = AsyncMock(return_value=mock_result)

    repo = PostgresTokenUsageRepository(session)
    since = datetime(2024, 6, 1, tzinfo=UTC)
    stats = await repo.aggregate_for_tenant(uuid4(), since=since)

    assert stats.total_input_tokens == 100
    assert stats.total_output_tokens == 50
    assert stats.total_cache_read_tokens == 10
    assert stats.total_input_cost == Decimal("0.01")
    assert stats.total_calls == 5


def test_to_model_maps_all_fields() -> None:
    usage = _make_usage(input_tokens=200, output_tokens=80)
    model = PostgresTokenUsageRepository._to_model(usage)

    assert model.id == usage.id
    assert model.tenant_id == usage.tenant_id
    assert model.input_tokens == 200
    assert model.output_tokens == 80
    assert model.provider == "openai"
    assert model.model == "gpt-4o-mini"
