"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response as StarletteResponse

from src.bootstrap.event_handlers import register_event_handlers
from src.bootstrap.startup import bootstrap_platform_admin, validate_production_settings
from src.config.settings import get_settings
from src.domain.shared.exceptions import DomainError
from src.drivers.api.middleware.rate_limit import limiter
from src.drivers.api.middleware.request_id import RequestIDMiddleware
from src.drivers.api.responses import domain_error_handler, integrity_error_handler
from src.drivers.api.v1.health.routes import router as health_router
from src.drivers.api.v1.router import v1_router
from src.drivers.api.webhooks.telegram import router as telegram_webhook_router
from src.drivers.api.webhooks.whatsapp import router as whatsapp_webhook_router
from src.drivers.jobs.queue import create_job_pool
from src.infrastructure.auth.crypto import verify_encryption_keys

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup / shutdown lifecycle.

    Domain-event side effects are dispatched synchronously in-process by the
    Unit of Work after each successful commit (see `bootstrap/events.py`). The
    durable `outbox_events` table + `OutboxRepository` are available for a
    future relay-based dispatcher but are not yet wired into the commit path,
    so there is no background relay task to start here.
    """
    register_event_handlers()
    settings = get_settings()
    validate_production_settings(settings)
    # Fail loudly at boot if ENCRYPTION_KEY / its fallbacks are malformed, rather than
    # silently decrypting tenant secrets to "" (and 403-ing webhooks) on a later request.
    verify_encryption_keys()
    logger.info("app.startup", env=settings.app_env, name=settings.app_name)
    await bootstrap_platform_admin(settings)
    # Connect the Arq job queue (ingestion runs on the worker). Skipped under the test
    # env, which drives the app via ASGITransport with no Redis/worker.
    app.state.job_pool = None
    if settings.app_env != "test":
        app.state.job_pool = await create_job_pool()
    yield
    if app.state.job_pool is not None:
        await app.state.job_pool.close()
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Sight",
        description="Multi-tenant AI front desk with RAG-grounded answers and human-in-the-loop escalation.",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(RequestIDMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    app.state.limiter = limiter
    # Set by the lifespan in non-test envs; None under tests (the dep is overridden).
    app.state.job_pool = None
    # Disable rate limiting under the test env so the suite's many login/register
    # calls from one client aren't throttled; enforced in dev and production.
    limiter.enabled = get_settings().app_env != "test"

    def _handle_rate_limit(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, RateLimitExceeded)
        return _rate_limit_exceeded_handler(request, exc)

    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)
    app.add_exception_handler(IntegrityError, integrity_error_handler)

    @app.get("/metrics", tags=["health"], include_in_schema=False)
    async def metrics() -> StarletteResponse:
        return StarletteResponse(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(health_router)
    app.include_router(v1_router)
    app.include_router(telegram_webhook_router)
    app.include_router(whatsapp_webhook_router)

    return app


app = create_app()
