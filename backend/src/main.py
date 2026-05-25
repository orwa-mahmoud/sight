"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.config.settings import get_settings
from src.domain.shared.exceptions import DomainError
from src.drivers.api.middleware.rate_limit import limiter
from src.drivers.api.middleware.request_id import RequestIDMiddleware
from src.drivers.api.responses import domain_error_handler
from src.drivers.api.v1.health.routes import router as health_router
from src.drivers.api.v1.router import v1_router
from src.drivers.api.webhooks.telegram import router as telegram_webhook_router
from src.drivers.api.webhooks.whatsapp import router as whatsapp_webhook_router

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application startup / shutdown lifecycle."""
    from src.bootstrap.event_handlers import register_event_handlers  # noqa: PLC0415

    register_event_handlers()
    settings = get_settings()
    logger.info("app.startup", env=settings.app_env, name=settings.app_name)
    yield
    logger.info("app.shutdown")


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
    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest  # noqa: PLC0415
    from starlette.responses import Response  # noqa: PLC0415

    @app.get("/metrics", tags=["health"], include_in_schema=False)
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    app.include_router(health_router)
    app.include_router(v1_router)
    app.include_router(telegram_webhook_router)
    app.include_router(whatsapp_webhook_router)

    return app


app = create_app()
