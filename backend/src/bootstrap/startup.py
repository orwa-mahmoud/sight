"""Startup tasks: production-config validation + platform-admin bootstrap.

Called from the FastAPI lifespan. Kept separate from `main.py` so it can be
unit-tested and reused by the CLI without importing the web app.
"""

from __future__ import annotations

import structlog

from src.application.shared.unit_of_work import UnitOfWork
from src.bootstrap.container import set_platform_admin_use_case
from src.config.settings import Settings
from src.domain.shared.exceptions import EntityNotFoundError
from src.infrastructure.persistence.postgres.database import async_session_factory

logger = structlog.get_logger()


def validate_production_settings(settings: Settings) -> None:
    """Fail fast on unsafe production configuration.

    In production, tenant secrets (LLM API keys, channel tokens) MUST be
    encrypted at rest — refuse to boot without an ENCRYPTION_KEY.
    """
    if settings.app_env != "production":
        return
    if not settings.encryption_key:
        raise RuntimeError(
            "ENCRYPTION_KEY must be set in production so tenant secrets are "
            "encrypted at rest. Generate one with: "
            'python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )


async def bootstrap_platform_admin(settings: Settings) -> None:
    """Grant platform-admin to PLATFORM_ADMIN_EMAIL if that user exists.

    Idempotent and best-effort: a missing user (e.g. before first registration)
    is logged, not fatal — re-running after the user registers will grant it.
    """
    email = settings.platform_admin_email
    if not email:
        return
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        try:
            await set_platform_admin_use_case(uow).execute(email=email, granted=True)
            await session.commit()
            logger.info("startup.platform_admin_bootstrapped", email=email)
        except EntityNotFoundError:
            await session.rollback()
            logger.warning("startup.platform_admin_user_missing", email=email)
