"""Thread-level concurrency control via Redis.

Prevents two inbound messages on the same conversation thread from
racing through the agent loop simultaneously. Uses Redis SET NX with
a TTL as a distributed lock, and a Lua compare-and-delete script for
safe release (only the lock holder can release).

If Redis is unavailable, the lock degrades gracefully (allows through
with a warning) — better to risk a race than to block all messages.
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

logger = structlog.get_logger()

_LOCK_TTL_SECONDS = 300  # 5 minutes — safety cap
_LOCK_PREFIX = "sight:thread_lock:"

_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


class ThreadLock:
    """Redis-backed per-thread lock. Use as an async context manager."""

    def __init__(self, redis_client: Any, thread_id: str) -> None:
        self._redis = redis_client
        self._key = f"{_LOCK_PREFIX}{thread_id}"
        self._token = uuid.uuid4().hex
        self._acquired = False

    async def acquire(self) -> bool:
        try:
            result = await self._redis.set(
                self._key,
                self._token,
                nx=True,
                ex=_LOCK_TTL_SECONDS,
            )
            self._acquired = result is not None and result is not False
            return self._acquired
        except Exception:
            logger.warning("thread_lock.acquire_failed", key=self._key, exc_info=True)
            self._acquired = True  # degrade: allow through
            return True

    async def release(self) -> None:
        if not self._acquired:
            return
        try:
            await self._redis.eval(
                _RELEASE_LUA,
                1,
                self._key,
                self._token,
            )
        except Exception:
            logger.warning("thread_lock.release_failed", key=self._key, exc_info=True)

    async def __aenter__(self) -> ThreadLock:
        await self.acquire()
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.release()
