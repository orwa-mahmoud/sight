"""Unit tests for rate limiter setup."""

from __future__ import annotations

from src.drivers.api.middleware.rate_limit import limiter


def test_limiter_exists() -> None:
    assert limiter is not None
    assert limiter._default_limits is not None


def test_limiter_disabled_under_test_env() -> None:
    # create_app() runs on import with APP_ENV=test and must disable throttling so
    # the suite's many login/register calls from one client aren't rate-limited.
    import src.main  # noqa: F401  (import triggers create_app side effect)

    assert limiter.enabled is False
