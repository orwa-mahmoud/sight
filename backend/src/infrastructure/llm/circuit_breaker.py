"""Per-tenant LLM circuit breaker — Redis-backed state machine.

State transitions: CLOSED → OPEN → HALF_OPEN → CLOSED.

When a tenant's LLM fails N times in a window, the circuit opens and
fast-fails subsequent calls (returning a clear error message instead of
hammering the provider). After a cooldown, a single test request is
allowed (HALF_OPEN); if it succeeds, the circuit closes again.

If Redis is unavailable, the circuit degrades to always-closed (allow
through) — better to risk an LLM call than block all tenants.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

import structlog

logger = structlog.get_logger()

_KEY_PREFIX = "frontdesk:circuit:"
_FAILURE_THRESHOLD = 5  # failures within the window to open
_FAILURE_WINDOW_SECONDS = 60  # rolling window
_OPEN_DURATION_SECONDS = 30  # how long the circuit stays open
_HALF_OPEN_SUCCESS_THRESHOLD = 2  # successes in half-open to close


class CircuitState(StrEnum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreakerError(Exception):
    """Raised when the circuit is open — fast-fail the request."""

    def __init__(self, tenant_id: str) -> None:
        super().__init__(
            f"LLM circuit breaker is OPEN for tenant {tenant_id}. "
            "The provider may be experiencing issues. Try again shortly."
        )
        self.tenant_id = tenant_id


class RedisCircuitBreaker:
    """Per-tenant circuit breaker backed by Redis. Thread-safe via atomic ops."""

    def __init__(self, redis_client: Any) -> None:
        self._redis = redis_client

    async def check(self, tenant_id: str) -> None:
        """Raise CircuitBreakerError if the circuit is open."""
        try:
            state = await self._get_state(tenant_id)
            if state == CircuitState.OPEN:
                opened_at = await self._get_opened_at(tenant_id)
                if time.time() - opened_at > _OPEN_DURATION_SECONDS:
                    await self._transition(tenant_id, CircuitState.HALF_OPEN)
                    return
                raise CircuitBreakerError(tenant_id)
        except CircuitBreakerError:
            raise
        except Exception:
            logger.warning("circuit_breaker.check_failed", tenant_id=tenant_id, exc_info=True)

    async def record_success(self, tenant_id: str) -> None:
        """Record a successful call. In HALF_OPEN, may close the circuit."""
        try:
            state = await self._get_state(tenant_id)
            if state == CircuitState.HALF_OPEN:
                successes = await self._incr_counter(tenant_id, "successes")
                if successes >= _HALF_OPEN_SUCCESS_THRESHOLD:
                    await self._transition(tenant_id, CircuitState.CLOSED)
                    logger.info("circuit_breaker.closed", tenant_id=tenant_id)
        except Exception:
            logger.warning("circuit_breaker.record_success_failed", tenant_id=tenant_id, exc_info=True)

    async def record_failure(self, tenant_id: str, *, is_transient: bool = True) -> None:
        """Record a failed call. May open the circuit."""
        try:
            if not is_transient:
                await self._transition(tenant_id, CircuitState.OPEN)
                logger.warning("circuit_breaker.opened_permanent", tenant_id=tenant_id)
                return

            failures = await self._incr_counter(tenant_id, "failures")
            if failures >= _FAILURE_THRESHOLD:
                await self._transition(tenant_id, CircuitState.OPEN)
                logger.warning("circuit_breaker.opened_transient", tenant_id=tenant_id, failures=failures)
        except Exception:
            logger.warning("circuit_breaker.record_failure_failed", tenant_id=tenant_id, exc_info=True)

    async def _get_state(self, tenant_id: str) -> CircuitState:
        raw = await self._redis.get(f"{_KEY_PREFIX}{tenant_id}:state")
        if raw is None:
            return CircuitState.CLOSED
        return CircuitState(raw.decode() if isinstance(raw, bytes) else raw)

    async def _get_opened_at(self, tenant_id: str) -> float:
        raw = await self._redis.get(f"{_KEY_PREFIX}{tenant_id}:opened_at")
        return float(raw) if raw else 0.0

    async def _transition(self, tenant_id: str, new_state: CircuitState) -> None:
        key = f"{_KEY_PREFIX}{tenant_id}"
        await self._redis.set(f"{key}:state", new_state.value, ex=_OPEN_DURATION_SECONDS * 3)
        if new_state == CircuitState.OPEN:
            await self._redis.set(f"{key}:opened_at", str(time.time()), ex=_OPEN_DURATION_SECONDS * 3)
            await self._redis.delete(f"{key}:failures", f"{key}:successes")
        elif new_state == CircuitState.CLOSED:
            await self._redis.delete(f"{key}:failures", f"{key}:successes", f"{key}:opened_at")
        elif new_state == CircuitState.HALF_OPEN:
            await self._redis.delete(f"{key}:successes")

    async def _incr_counter(self, tenant_id: str, counter: str) -> int:
        key = f"{_KEY_PREFIX}{tenant_id}:{counter}"
        val = await self._redis.incr(key)
        await self._redis.expire(key, _FAILURE_WINDOW_SECONDS)
        return int(val)
