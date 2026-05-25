"""Unit tests for rate limiter setup."""

from __future__ import annotations

from src.drivers.api.middleware.rate_limit import limiter


def test_limiter_exists():
    assert limiter is not None
    assert limiter._default_limits is not None
