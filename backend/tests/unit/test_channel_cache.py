"""Unit tests for src/infrastructure/channels/cache.py -- _AdapterCache, get_whatsapp_adapter, get_telegram_adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.infrastructure.channels.cache import (
    _AdapterCache,
    _cred_hash,
    _safe_close,
    get_telegram_adapter,
    get_whatsapp_adapter,
)

# ---------------------------------------------------------------------------
# _cred_hash
# ---------------------------------------------------------------------------


class TestCredHash:
    def test_deterministic(self) -> None:
        h1 = _cred_hash("a", "b")
        h2 = _cred_hash("a", "b")
        assert h1 == h2

    def test_different_inputs_differ(self) -> None:
        assert _cred_hash("a", "b") != _cred_hash("c", "d")

    def test_length_12(self) -> None:
        assert len(_cred_hash("x", "y")) == 12


# ---------------------------------------------------------------------------
# _safe_close
# ---------------------------------------------------------------------------


class TestSafeClose:
    @pytest.mark.asyncio
    async def test_calls_close(self) -> None:
        adapter = AsyncMock()
        adapter.close = AsyncMock()
        await _safe_close(adapter)
        adapter.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_close_method(self) -> None:
        adapter = MagicMock(spec=[])  # no close attribute
        # Should not raise
        await _safe_close(adapter)

    @pytest.mark.asyncio
    async def test_close_error_ignored(self) -> None:
        adapter = AsyncMock()
        adapter.close = AsyncMock(side_effect=RuntimeError("fail"))
        # Should not raise
        await _safe_close(adapter)


# ---------------------------------------------------------------------------
# _AdapterCache
# ---------------------------------------------------------------------------


class TestAdapterCache:
    @pytest.mark.asyncio
    async def test_put_and_get(self) -> None:
        cache = _AdapterCache(ttl=60, max_size=10)
        adapter = MagicMock()
        await cache.put("k1", adapter)
        result = await cache.get("k1")
        assert result is adapter

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self) -> None:
        cache = _AdapterCache(ttl=60, max_size=10)
        assert await cache.get("missing") is None

    @pytest.mark.asyncio
    async def test_ttl_expiry(self) -> None:
        cache = _AdapterCache(ttl=0, max_size=10)  # immediate expiry
        adapter = AsyncMock()
        adapter.close = AsyncMock()
        await cache.put("k1", adapter)
        # Even though we just put it, TTL=0 means it's expired
        result = await cache.get("k1")
        assert result is None
        adapter.close.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_lru_eviction(self) -> None:
        cache = _AdapterCache(ttl=300, max_size=2)
        a1 = AsyncMock()
        a1.close = AsyncMock()
        a2 = AsyncMock()
        a2.close = AsyncMock()
        a3 = AsyncMock()
        a3.close = AsyncMock()

        await cache.put("k1", a1)
        await cache.put("k2", a2)
        await cache.put("k3", a3)  # should evict k1 (LRU)

        a1.close.assert_awaited_once()
        assert await cache.get("k1") is None
        assert await cache.get("k2") is a2
        assert await cache.get("k3") is a3

    @pytest.mark.asyncio
    async def test_replace_closes_old(self) -> None:
        cache = _AdapterCache(ttl=300, max_size=10)
        old = AsyncMock()
        old.close = AsyncMock()
        new = MagicMock()
        await cache.put("k1", old)
        await cache.put("k1", new)
        old.close.assert_awaited_once()
        assert await cache.get("k1") is new

    @pytest.mark.asyncio
    async def test_get_moves_to_end(self) -> None:
        cache = _AdapterCache(ttl=300, max_size=2)
        a1 = AsyncMock()
        a1.close = AsyncMock()
        a2 = AsyncMock()
        a2.close = AsyncMock()
        a3 = AsyncMock()
        a3.close = AsyncMock()

        await cache.put("k1", a1)
        await cache.put("k2", a2)
        # Access k1 to move it to end (most recently used)
        await cache.get("k1")
        # Now k2 is LRU -- adding k3 should evict k2
        await cache.put("k3", a3)
        a2.close.assert_awaited_once()
        assert await cache.get("k1") is a1


# ---------------------------------------------------------------------------
# get_whatsapp_adapter
# ---------------------------------------------------------------------------


class TestGetWhatsappAdapter:
    @pytest.mark.asyncio
    async def test_creates_new(self) -> None:
        # Use a fresh cache so we don't leak state
        fresh_cache = _AdapterCache(ttl=300, max_size=10)
        with patch("src.infrastructure.channels.cache._cache", fresh_cache):
            adapter = await get_whatsapp_adapter("t1", phone_number_id="pn1", access_token="tok1")
            assert adapter._phone_number_id == "pn1"

    @pytest.mark.asyncio
    async def test_returns_cached(self) -> None:
        fresh_cache = _AdapterCache(ttl=300, max_size=10)
        with patch("src.infrastructure.channels.cache._cache", fresh_cache):
            a1 = await get_whatsapp_adapter("t1", phone_number_id="pn1", access_token="tok1")
            a2 = await get_whatsapp_adapter("t1", phone_number_id="pn1", access_token="tok1")
            assert a1 is a2

    @pytest.mark.asyncio
    async def test_different_creds_different_adapter(self) -> None:
        fresh_cache = _AdapterCache(ttl=300, max_size=10)
        with patch("src.infrastructure.channels.cache._cache", fresh_cache):
            a1 = await get_whatsapp_adapter("t1", phone_number_id="pn1", access_token="tok1")
            a2 = await get_whatsapp_adapter("t1", phone_number_id="pn1", access_token="tok2")
            assert a1 is not a2


# ---------------------------------------------------------------------------
# get_telegram_adapter
# ---------------------------------------------------------------------------


class TestGetTelegramAdapter:
    @pytest.mark.asyncio
    async def test_creates_new(self) -> None:
        fresh_cache = _AdapterCache(ttl=300, max_size=10)
        cfg = MagicMock()
        cfg.telegram_bot_token = "bot-tok"
        with patch("src.infrastructure.channels.cache._cache", fresh_cache):
            adapter = await get_telegram_adapter("t1", tenant_config=cfg)
            assert adapter._token == "bot-tok"

    @pytest.mark.asyncio
    async def test_returns_cached(self) -> None:
        fresh_cache = _AdapterCache(ttl=300, max_size=10)
        cfg = MagicMock()
        cfg.telegram_bot_token = "bot-tok"
        with patch("src.infrastructure.channels.cache._cache", fresh_cache):
            a1 = await get_telegram_adapter("t1", tenant_config=cfg)
            a2 = await get_telegram_adapter("t1", tenant_config=cfg)
            assert a1 is a2

    @pytest.mark.asyncio
    async def test_empty_token(self) -> None:
        fresh_cache = _AdapterCache(ttl=300, max_size=10)
        cfg = MagicMock()
        cfg.telegram_bot_token = ""
        with patch("src.infrastructure.channels.cache._cache", fresh_cache):
            adapter = await get_telegram_adapter("t1", tenant_config=cfg)
            assert adapter._token == ""
