"""Channel send retry -- configurable constants and reusable decorator."""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

# -- Configurable constants --------------------------------------------------

CHANNEL_SEND_MAX_RETRIES: int = 3
CHANNEL_SEND_RETRY_DELAY_SECONDS: float = 2.0

WHATSAPP_MAX_IMAGES_PER_ALBUM: int = 5
WHATSAPP_IMAGE_SEND_DELAY_SECONDS: float = 1.0


# -- Retry decorator ---------------------------------------------------------

_F = TypeVar("_F", bound=Callable[..., object])


def channel_send_retry() -> Callable[[_F], _F]:
    """Tenacity retry decorator for channel send operations.

    Retries on transient transport errors, timeouts, and 5xx HTTP errors.
    Does NOT retry on 4xx (client errors like bad request / rate limit).
    """
    return retry(
        retry=retry_if_exception_type((httpx.TransportError, httpx.TimeoutException)),
        stop=stop_after_attempt(CHANNEL_SEND_MAX_RETRIES),
        wait=wait_fixed(CHANNEL_SEND_RETRY_DELAY_SECONDS),
        reraise=True,
    )
