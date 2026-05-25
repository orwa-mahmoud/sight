"""Health + readiness endpoints."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from src.config.settings import get_settings
from src.infrastructure.persistence.postgres.database import async_session_factory

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
    settings = get_settings()
    return HealthResponse(status="ok", service=settings.app_name, version="0.1.0")


@router.get("/ready")
async def readiness() -> ReadinessResponse:
    """Check database connectivity."""
    db_status = "ok"
    redis_status = "unknown"
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    return ReadinessResponse(database=db_status, redis=redis_status)
