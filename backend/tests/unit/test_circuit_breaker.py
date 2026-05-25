"""Unit tests for the Redis circuit breaker."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.llm.circuit_breaker import (
    CircuitBreakerError,
    CircuitState,
    RedisCircuitBreaker,
)


def _make_redis(state: str | None = None, opened_at: float | None = None) -> AsyncMock:
    redis = AsyncMock()

    async def mock_get(key: str) -> bytes | None:
        if "state" in key and state:
            return state.encode()
        if "opened_at" in key and opened_at is not None:
            return str(opened_at).encode()
        return None

    redis.get = AsyncMock(side_effect=mock_get)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    return redis


@pytest.mark.asyncio
async def test_closed_circuit_allows_through() -> None:
    redis = _make_redis()
    cb = RedisCircuitBreaker(redis)
    await cb.check("tenant-1")  # no error


@pytest.mark.asyncio
async def test_open_circuit_raises() -> None:
    redis = _make_redis(state="open", opened_at=time.time())
    cb = RedisCircuitBreaker(redis)
    with pytest.raises(CircuitBreakerError):
        await cb.check("tenant-1")


@pytest.mark.asyncio
async def test_open_circuit_transitions_to_half_open_after_cooldown() -> None:
    redis = _make_redis(state="open", opened_at=time.time() - 60)
    cb = RedisCircuitBreaker(redis)
    await cb.check("tenant-1")  # transitions to half-open, no error
    redis.set.assert_called()


@pytest.mark.asyncio
async def test_record_success_in_half_open_closes_circuit() -> None:
    redis = _make_redis(state="half_open")
    redis.incr = AsyncMock(return_value=2)  # meets threshold
    cb = RedisCircuitBreaker(redis)
    await cb.record_success("tenant-1")
    # Should have transitioned to closed
    redis.set.assert_called()


@pytest.mark.asyncio
async def test_record_failure_opens_circuit_at_threshold() -> None:
    redis = _make_redis()
    redis.incr = AsyncMock(return_value=5)  # meets threshold
    cb = RedisCircuitBreaker(redis)
    await cb.record_failure("tenant-1")
    redis.set.assert_called()


@pytest.mark.asyncio
async def test_permanent_failure_opens_immediately() -> None:
    redis = _make_redis()
    cb = RedisCircuitBreaker(redis)
    await cb.record_failure("tenant-1", is_transient=False)
    redis.set.assert_called()


@pytest.mark.asyncio
async def test_redis_error_degrades_gracefully() -> None:
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=ConnectionError("down"))
    cb = RedisCircuitBreaker(redis)
    await cb.check("tenant-1")  # doesn't raise — degrades to allow


def test_circuit_state_values() -> None:
    assert CircuitState.CLOSED == "closed"
    assert CircuitState.OPEN == "open"
    assert CircuitState.HALF_OPEN == "half_open"
