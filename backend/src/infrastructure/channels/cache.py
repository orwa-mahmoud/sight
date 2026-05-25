"""Tenant-keyed adapter cache -- reuse httpx connection pools across requests.

Each tenant gets one WhatsAppAdapter and one TelegramAdapter. The adapters
(and their underlying httpx.AsyncClient) are reused for all requests to the
same tenant, avoiding repeated TCP+TLS handshakes to Meta/Telegram APIs.

Entries expire after TTL so credential rotations are picked up.
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from collections import OrderedDict
from typing import TYPE_CHECKING

import structlog

from src.infrastructure.channels.telegram import TelegramAdapter
from src.infrastructure.channels.whatsapp import WhatsAppAdapter

if TYPE_CHECKING:
    from src.infrastructure.channels.base import ChannelAdapter

logger = structlog.get_logger()

_TTL_SECONDS = 1800  # 30 min -- pick up credential changes
_MAX_SIZE = 200  # max cached adapters (across all tenants + channels)


class _AdapterCache:
    """LRU + TTL cache for channel adapters, keyed by (tenant_id, channel).

    Protected by asyncio.Lock for safe concurrent access.
    Properly closes evicted/expired adapters to prevent connection leaks.
    """

    def __init__(self, ttl: int = _TTL_SECONDS, max_size: int = _MAX_SIZE) -> None:
        self._cache: OrderedDict[str, tuple[ChannelAdapter, float]] = OrderedDict()
        self._ttl = ttl
        self._max_size = max_size
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> ChannelAdapter | None:
        async with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            adapter, created_at = entry
            if (time.monotonic() - created_at) > self._ttl:
                self._cache.pop(key, None)
                # Close expired adapter outside lock is ideal but we keep it simple
                await _safe_close(adapter)
                return None
            self._cache.move_to_end(key)
            return adapter

    async def put(self, key: str, adapter: ChannelAdapter) -> None:
        async with self._lock:
            # If replacing existing entry, close the old adapter
            old_entry = self._cache.pop(key, None)
            if old_entry is not None:
                await _safe_close(old_entry[0])
            self._cache[key] = (adapter, time.monotonic())
            self._cache.move_to_end(key)
            while len(self._cache) > self._max_size:
                evicted_key, (evicted_adapter, _) = self._cache.popitem(last=False)
                logger.debug("adapter_cache.evicted", key=evicted_key)
                await _safe_close(evicted_adapter)


async def _safe_close(adapter: ChannelAdapter) -> None:
    """Close an adapter's HTTP client, ignoring errors."""
    try:
        if hasattr(adapter, "close"):
            await adapter.close()
    except Exception:
        logger.debug("adapter_cache.close_failed", exc_info=True)


_cache = _AdapterCache()


def _cred_hash(*parts: str) -> str:
    """Short hash of credential parts -- cache key rotates when creds change."""
    return hashlib.sha256("|".join(parts).encode()).hexdigest()[:12]


async def get_whatsapp_adapter(
    tenant_id: str,
    *,
    phone_number_id: str = "",
    access_token: str = "",
) -> WhatsAppAdapter:
    """Get or create a cached WhatsAppAdapter for this tenant."""
    key = f"wa:{tenant_id}:{_cred_hash(phone_number_id, access_token)}"
    existing = await _cache.get(key)
    if existing is not None:
        return existing  # type: ignore[return-value]

    adapter = WhatsAppAdapter(phone_number_id=phone_number_id, access_token=access_token)
    await _cache.put(key, adapter)
    return adapter


async def get_telegram_adapter(tenant_id: str, *, tenant_config: object) -> TelegramAdapter:
    """Get or create a cached TelegramAdapter for this tenant."""
    token = getattr(tenant_config, "telegram_bot_token", "") or ""
    key = f"tg:{tenant_id}:{_cred_hash(token)}"
    existing = await _cache.get(key)
    if existing is not None:
        return existing  # type: ignore[return-value]

    adapter = TelegramAdapter(tenant_config=tenant_config)  # type: ignore[arg-type]
    await _cache.put(key, adapter)
    return adapter
