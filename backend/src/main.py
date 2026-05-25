"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config.settings import get_settings
from src.domain.shared.exceptions import DomainError
from src.drivers.api.responses import domain_error_handler
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_exception_handler(DomainError, domain_error_handler)  # type: ignore[arg-type]

    app.include_router(v1_router)
    app.include_router(telegram_webhook_router)
    app.include_router(whatsapp_webhook_router)

    @app.get("/health", tags=["health"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
