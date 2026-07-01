"""Webhook message de-duplication via Redis.

WhatsApp and Telegram deliver webhooks **at least once** — the same inbound
message can arrive more than once (provider retries / duplicates). Without a
guard each delivery would be saved, answered by the agent, and billed again.

The marker is written **only after a message is fully processed and its reply
dispatched** (`mark_message_processed`), and read at the start of the next
delivery (`was_message_processed`). Marking on success — not on receipt — is
deliberate: a transient failure leaves the message un-marked, so the provider's
re-delivery reprocesses it instead of being silently dropped for the whole TTL.
This matches the contract we want: rather risk a rare double-reply than drop a
message. Double-billing is separately prevented by the durable DB de-dup on
``provider_message_id`` (see SaveThreadMessageUseCase.insert_if_new).

If Redis is unavailable both calls degrade safely: the check reports "not seen"
and the mark is a no-op — again favouring a possible re-process over a drop.
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
    client: aioredis.Redis | None = None


def _get_client() -> aioredis.Redis | None:
    if _RedisSingleton.client is not None:
        return _RedisSingleton.client
    try:
        _RedisSingleton.client = aioredis.from_url(get_settings().redis_url)
        return _RedisSingleton.client
    except Exception:
        return None


def _key(tenant_id: UUID, channel: str, message_id: str) -> str:
    return f"{_PREFIX}{tenant_id}:{channel}:{message_id}"


async def was_message_processed(*, tenant_id: UUID, channel: str, message_id: str) -> bool:
    """True if this ``(tenant, channel, message_id)`` was already fully processed.

    No message_id (or no Redis) → treated as not seen, so the caller processes it.
    """
    if not message_id:
        return False
    client = _get_client()
    if client is None:
        return False
    key = _key(tenant_id, channel, message_id)
    try:
        return await client.get(key) is not None
    except Exception:
        logger.warning("idempotency.check_failed", key=key, exc_info=True)
        return False


async def mark_message_processed(*, tenant_id: UUID, channel: str, message_id: str) -> None:
    """Record that a message was fully processed so re-deliveries are skipped for
    the TTL. Call this only after the reply was dispatched. Best-effort: a Redis
    outage just risks a re-process (double-reply), never a drop.
    """
    if not message_id:
        return
    client = _get_client()
    if client is None:
        return
    key = _key(tenant_id, channel, message_id)
    try:
        await client.set(key, "1", ex=_TTL_SECONDS)
    except Exception:
        logger.warning("idempotency.mark_failed", key=key, exc_info=True)
