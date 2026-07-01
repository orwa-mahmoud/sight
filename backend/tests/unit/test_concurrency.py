"""Unit tests for the thread lock — mock Redis, test lock semantics."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

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


@pytest.mark.asyncio
async def test_acquire_blocking_succeeds_immediately_when_free() -> None:
    redis = AsyncMock()
    redis.set.return_value = True
    lock = ThreadLock(redis, "thread-5")
    with patch("src.ai.concurrency.asyncio.sleep", new_callable=AsyncMock) as sleep:
        assert await lock.acquire_blocking(attempts=5, interval_seconds=0.01) is True
    sleep.assert_not_called()  # no wait needed


@pytest.mark.asyncio
async def test_acquire_blocking_waits_then_acquires() -> None:
    redis = AsyncMock()
    # Held by another turn for the first two polls, then released.
    redis.set.side_effect = [None, None, True]
    lock = ThreadLock(redis, "thread-6")
    with patch("src.ai.concurrency.asyncio.sleep", new_callable=AsyncMock) as sleep:
        assert await lock.acquire_blocking(attempts=5, interval_seconds=0.01) is True
    assert lock._acquired
    assert sleep.await_count == 2  # slept between the two failed attempts


@pytest.mark.asyncio
async def test_acquire_blocking_times_out_when_never_free() -> None:
    redis = AsyncMock()
    redis.set.return_value = None  # perpetually contended
    lock = ThreadLock(redis, "thread-7")
    with patch("src.ai.concurrency.asyncio.sleep", new_callable=AsyncMock) as sleep:
        assert await lock.acquire_blocking(attempts=3, interval_seconds=0.01) is False
    assert not lock._acquired
    assert redis.set.await_count == 3  # tried exactly `attempts` times
    assert sleep.await_count == 2  # no sleep after the final attempt
