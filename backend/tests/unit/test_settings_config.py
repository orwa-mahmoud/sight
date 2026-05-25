"""Unit tests for pydantic settings construction."""

from __future__ import annotations

import os


def test_settings_loads_from_env(monkeypatch: object) -> None:
    import pytest

    mp = pytest.MonkeyPatch()
    mp.setenv("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    mp.setenv("DATABASE_URL_SYNC", "postgresql://localhost/test")
    mp.setenv("JWT_SECRET_KEY", "test-key")
    mp.setenv("CORS_ORIGINS", "http://a.com,http://b.com")

    # Clear the cache so we get a fresh Settings instance.
    from src.config.settings import Settings

    s = Settings()  # type: ignore[call-arg]
    assert s.jwt_secret_key == "test-key"
    assert s.cors_origins_list == ["http://a.com", "http://b.com"]
    mp.undo()


def test_cors_origins_split() -> None:
    from src.config.settings import Settings

    os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://localhost/test")
    os.environ.setdefault("DATABASE_URL_SYNC", "postgresql://localhost/test")
    os.environ.setdefault("JWT_SECRET_KEY", "k")
    s = Settings(cors_origins="http://x.com , http://y.com ")  # type: ignore[call-arg]
    assert s.cors_origins_list == ["http://x.com", "http://y.com"]
