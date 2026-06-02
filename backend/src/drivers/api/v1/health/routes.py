"""Health + readiness endpoints."""

from __future__ import annotations

import redis.asyncio as aioredis
import structlog
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from sqlalchemy import text

from src.config.settings import get_settings
from src.infrastructure.persistence.postgres.database import async_session_factory

logger = structlog.get_logger()

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    database: str
    redis: str


@router.get("/health")
async def health() -> HealthResponse:
    """Liveness — the process is up. Intentionally does not touch dependencies."""
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, version="0.1.0")


async def _check_database() -> bool:
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return True
    except Exception:
        logger.warning("readiness.database_unavailable", exc_info=True)
        return False


async def _check_redis() -> bool:
    try:
        client = aioredis.from_url(get_settings().redis_url)
        try:
            await client.ping()
        finally:
            await client.aclose()
        return True
    except Exception:
        logger.warning("readiness.redis_unavailable", exc_info=True)
        return False


@router.get("/ready")
async def readiness(response: Response) -> ReadinessResponse:
    """Readiness — verify dependencies.

    The database is required, so a DB failure returns 503 to take the instance out
    of rotation. Redis is reported truthfully but degrades gracefully (locks +
    idempotency), so it does not by itself fail readiness.
    """
    db_ok = await _check_database()
    redis_ok = await _check_redis()
    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        database="ok" if db_ok else "error",
        redis="ok" if redis_ok else "error",
    )
