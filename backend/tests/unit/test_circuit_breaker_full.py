"""Additional unit tests for circuit breaker — covers record_success and record_failure error paths."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.infrastructure.llm.circuit_breaker import RedisCircuitBreaker


def _make_redis(state: str | None = None) -> AsyncMock:
    redis = AsyncMock()

    async def mock_get(key: str) -> bytes | None:
        if "state" in key and state:
            return state.encode()
        return None

    redis.get = AsyncMock(side_effect=mock_get)
    redis.set = AsyncMock()
    redis.delete = AsyncMock()
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock()
    return redis


@pytest.mark.asyncio
async def test_record_success_redis_error_degrades_gracefully() -> None:
    """If Redis fails during record_success, the error is swallowed."""
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
    cb = RedisCircuitBreaker(redis)
    # Should NOT raise
    await cb.record_success("tenant-1")


@pytest.mark.asyncio
async def test_record_failure_redis_error_degrades_gracefully() -> None:
    """If Redis fails during record_failure, the error is swallowed."""
    redis = AsyncMock()
    redis.get = AsyncMock(side_effect=ConnectionError("redis down"))
    cb = RedisCircuitBreaker(redis)
    # Should NOT raise
    await cb.record_failure("tenant-1")


@pytest.mark.asyncio
async def test_record_failure_below_threshold_does_not_open() -> None:
    """When failures < threshold, circuit stays closed."""
    redis = _make_redis()
    redis.incr = AsyncMock(return_value=3)  # below threshold of 5
    cb = RedisCircuitBreaker(redis)
    await cb.record_failure("tenant-1")
    # set should NOT have been called (no transition)
    redis.set.assert_not_called()


@pytest.mark.asyncio
async def test_record_success_in_closed_state_does_nothing() -> None:
    """Recording success when circuit is CLOSED should be a no-op."""
    redis = _make_redis()  # defaults to CLOSED
    cb = RedisCircuitBreaker(redis)
    await cb.record_success("tenant-1")
    redis.set.assert_not_called()
    redis.incr.assert_not_called()
