"""SQLAlchemy async engine + session factory.

Connection pooling is configured per app environment: production uses a real
pool, tests use `NullPool` to avoid asyncpg connections being held across
event loops (a known pytest-asyncio interaction). The factory functions
return module-level singletons so DI / FastAPI dependencies reuse the engine.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from src.config.settings import get_settings


def _build_engine() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    settings = get_settings()
    is_test = settings.app_env.lower() in {"test", "testing"}
    if is_test:
        eng = create_async_engine(settings.database_url, echo=False, poolclass=NullPool)
    else:
        eng = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
        )
    factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
        eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    return eng, factory


engine, async_session_factory = _build_engine()


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Open a session, commit on success, rollback on error, always close."""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
