"""Webhook message de-duplication via Redis SET NX.

WhatsApp and Telegram deliver webhooks **at least once** — the same inbound
message can arrive more than once (provider retries / duplicates). Without a
guard each delivery would be saved, answered by the agent, and billed again.

We record each processed ``(tenant, channel, message_id)`` in Redis with a TTL
and treat a repeat as a duplicate. If Redis is unavailable the check degrades to
"not a duplicate" — we'd rather risk a rare double-reply than drop messages.
"""

from __future__ import annotations

from uuid import UUID

import redis.asyncio as aioredis
import structlog

from src.config.settings import get_settings

logger = structlog.get_logger()

_TTL_SECONDS = 86_400  # 24h — comfortably longer than any provider retry window
_PREFIX = "sight:msg_seen:"


class _RedisSingleton:
    client: object | None = None


def _get_client() -> object | None:
    if _RedisSingleton.client is not None:
        return _RedisSingleton.client
    try:
        _RedisSingleton.client = aioredis.from_url(get_settings().redis_url)
        return _RedisSingleton.client
    except Exception:
        return None


async def is_duplicate_message(*, tenant_id: UUID, channel: str, message_id: str) -> bool:
    """Return True if this (tenant, channel, message_id) was already processed.

    The first call for a given key records it and returns False; subsequent calls
    within the TTL return True. No message_id (or no Redis) → never a duplicate.
    """
    if not message_id:
        return False
    client = _get_client()
    if client is None:
        return False
    key = f"{_PREFIX}{tenant_id}:{channel}:{message_id}"
    try:
        # SET key 1 NX EX ttl → truthy when newly set, None when it already existed.
        was_set = await client.set(key, "1", nx=True, ex=_TTL_SECONDS)  # type: ignore[attr-defined]
        return not was_set
    except Exception:
        logger.warning("idempotency.check_failed", key=key, exc_info=True)
        return False
