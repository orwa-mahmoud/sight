"""Unit tests for src/infrastructure/channels/retry.py -- channel_send_retry decorator and constants."""

from __future__ import annotations

import httpx
import pytest

from src.infrastructure.channels.retry import (
    CHANNEL_SEND_MAX_RETRIES,
    CHANNEL_SEND_RETRY_DELAY_SECONDS,
    WHATSAPP_IMAGE_SEND_DELAY_SECONDS,
    WHATSAPP_MAX_IMAGES_PER_ALBUM,
    channel_send_retry,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_max_retries(self) -> None:
        assert CHANNEL_SEND_MAX_RETRIES == 3

    def test_retry_delay(self) -> None:
        assert CHANNEL_SEND_RETRY_DELAY_SECONDS == 2.0

    def test_max_images(self) -> None:
        assert WHATSAPP_MAX_IMAGES_PER_ALBUM == 5

    def test_image_delay(self) -> None:
        assert WHATSAPP_IMAGE_SEND_DELAY_SECONDS == 1.0


# ---------------------------------------------------------------------------
# channel_send_retry decorator
# ---------------------------------------------------------------------------


class TestChannelSendRetry:
    @pytest.mark.asyncio
    async def test_success_no_retry(self) -> None:
        @channel_send_retry()
        async def send() -> str:
            return "ok"

        result = await send()
        assert result == "ok"

    @pytest.mark.asyncio
    async def test_retries_on_transport_error(self) -> None:
        call_count = 0

        @channel_send_retry()
        async def send() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TransportError("connection reset")
            return "ok"

        result = await send()
        assert result == "ok"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retries_on_timeout(self) -> None:
        call_count = 0

        @channel_send_retry()
        async def send() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise httpx.TimeoutException("timeout")
            return "ok"

        result = await send()
        assert result == "ok"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_does_not_retry_on_value_error(self) -> None:
        call_count = 0

        @channel_send_retry()
        async def send() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("bad input")

        with pytest.raises(ValueError):
            await send()
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_max_retries_exhausted(self) -> None:
        call_count = 0

        @channel_send_retry()
        async def send() -> str:
            nonlocal call_count
            call_count += 1
            raise httpx.TransportError("fail")

        with pytest.raises(httpx.TransportError):
            await send()
        assert call_count == CHANNEL_SEND_MAX_RETRIES
