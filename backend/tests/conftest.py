"""Shared pytest fixtures."""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _set_env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Provide a minimum viable env for any module importing settings during tests."""
    defaults = {
        "DATABASE_URL": os.getenv(
            "DATABASE_URL_TEST",
            "postgresql+asyncpg://postgres:postgres@localhost:5432/frontdesk_test",
        ),
        "DATABASE_URL_SYNC": os.getenv(
            "DATABASE_URL_SYNC",
            "postgresql://postgres:postgres@localhost:5432/frontdesk_test",
        ),
        "JWT_SECRET_KEY": "test-secret-not-for-production",
    }
    for key, value in defaults.items():
        monkeypatch.setenv(key, value)
    yield
