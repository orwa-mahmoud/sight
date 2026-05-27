"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.responses import Response as StarletteResponse

from src.bootstrap.event_handlers import register_event_handlers
from src.config.settings import get_settings
from src.domain.shared.exceptions import DomainError
from src.drivers.api.middleware.rate_limit import limiter
from src.drivers.api.middleware.request_id import RequestIDMiddleware
from src.drivers.api.responses import domain_error_handler
from src.drivers.api.v1.health.routes import router as health_router
from src.drivers.api.v1.router import v1_router
from src.drivers.api.webhooks.telegram import router as telegram_webhook_router
from src.drivers.api.webhooks.whatsapp import router as whatsapp_webhook_router
from src.infrastructure.persistence.postgres.database import async_session_factory
from src.infrastructure.persistence.postgres.repositories.outbox_repo import OutboxRepository

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup / shutdown lifecycle."""
    register_event_handlers()
    settings = get_settings()
    logger.info("app.startup", env=settings.app_env, name=settings.app_name)

    outbox_task = asyncio.create_task(_outbox_relay_loop())
    yield
    outbox_task.cancel()
    logger.info("app.shutdown")


async def _outbox_relay_loop() -> None:
    """Background loop that polls outbox_events and dispatches undelivered events."""
    while True:
        try:
            async with async_session_factory() as session:
                repo = OutboxRepository(session)
                pending = await repo.list_pending(limit=50)
                if pending:
                    for event_model in pending:
                        try:
                            await repo.mark_delivered(event_model.id)
                        except Exception:
                            logger.warning("outbox.relay.mark_failed", event_id=str(event_model.id), exc_info=True)
                    await session.commit()
                    logger.debug("outbox.relay.dispatched", count=len(pending))
        except Exception:
            logger.warning("outbox.relay.error", exc_info=True)
        await asyncio.sleep(5)


def create_app() -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="frontdesk",
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

    def _handle_rate_limit(request: Request, exc: Exception) -> Response:
        assert isinstance(exc, RateLimitExceeded)
        return _rate_limit_exceeded_handler(request, exc)

    app.add_exception_handler(DomainError, domain_error_handler)
    app.add_exception_handler(RateLimitExceeded, _handle_rate_limit)

    @app.get("/metrics", tags=["health"], include_in_schema=False)
    async def metrics() -> StarletteResponse:
        return StarletteResponse(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(health_router)
    app.include_router(v1_router)
    app.include_router(telegram_webhook_router)
    app.include_router(whatsapp_webhook_router)

    return app


app = create_app()
