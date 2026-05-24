"""Unit tests for the thread lock — mock Redis, test lock semantics."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from src.ai.concurrency import ThreadLock


@pytest.mark.asyncio
async def test_acquire_and_release() -> None:
    redis = AsyncMock()
    redis.set.return_value = True

    lock = ThreadLock(redis, "thread-1")
    assert await lock.acquire()
    assert lock._acquired

    await lock.release()
    redis.eval.assert_called_once()


@pytest.mark.asyncio
async def test_acquire_fails_gracefully_on_redis_error() -> None:
    redis = AsyncMock()
    redis.set.side_effect = ConnectionError("Redis down")

    lock = ThreadLock(redis, "thread-2")
    result = await lock.acquire()
    assert result is True  # degrades: allows through


@pytest.mark.asyncio
async def test_release_without_acquire_is_noop() -> None:
    redis = AsyncMock()
    lock = ThreadLock(redis, "thread-3")
    await lock.release()
    redis.eval.assert_not_called()


@pytest.mark.asyncio
async def test_context_manager() -> None:
    redis = AsyncMock()
    redis.set.return_value = True

    async with ThreadLock(redis, "thread-4") as lock:
        assert lock._acquired

    redis.eval.assert_called_once()
