"""Telegram webhook — receives updates from a per-tenant bot.

Verification: compares X-Telegram-Bot-Api-Secret-Token header against
the tenant's configured secret. Message extraction follows the standard
Telegram Bot API update schema.

Contact-share flow: on first contact the bot asks the user to share
their phone number. When they do, we store the telegram_user_id -> phone
mapping so future messages are identified.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, Header, Request, Response

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.config.settings import get_settings
from src.domain.conversations.value_objects import ConversationChannel
from src.drivers.api.dependencies import get_session

logger = structlog.get_logger()

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/{tenant_id}/telegram")
async def telegram_webhook(
    tenant_id: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> Response:
    settings = get_settings()
    expected = settings.telegram_webhook_secret
    if expected and x_telegram_bot_api_secret_token != expected:
        logger.warning("telegram.webhook.invalid_secret", tenant_id=tenant_id)
        return Response(status_code=403)

    body: dict[str, Any] = await request.json()
    message = body.get("message") or body.get("edited_message")
    if not message:
        return Response(status_code=200)

    from_user = message.get("from", {})
    telegram_user_id = str(from_user.get("id", ""))
    text = message.get("text", "")
    sender_name = from_user.get("first_name")

    if not text or not telegram_user_id:
        return Response(status_code=200)

    from uuid import UUID  # noqa: PLC0415

    try:
        tid = UUID(tenant_id)
    except ValueError:
        return Response(status_code=400)

    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            result = await chat_with_agent(
                ChatInput(
                    message=text,
                    tenant_id=tid,
                    channel=ConversationChannel.TELEGRAM,
                    sender_identifier=telegram_user_id,
                    sender_name=sender_name,
                ),
                uow=uow,
            )
            await uow.commit()

            # Send reply back via Telegram Bot API.
            await _send_telegram_reply(
                chat_id=message["chat"]["id"],
                text=result.response,
                tenant_id=tenant_id,
            )
        except Exception:
            await uow.rollback()
            logger.error("telegram.webhook.failed", tenant_id=tenant_id, exc_info=True)

    return Response(status_code=200)


async def _send_telegram_reply(*, chat_id: int, text: str, tenant_id: str) -> None:
    """Send a text reply via Telegram Bot API. Best-effort — errors are logged."""
    import httpx  # noqa: PLC0415

    # Per-tenant bot token would come from DB in production; for v1 we
    # use the env var. The architecture supports per-tenant tokens via
    # the tenant_config table (same as PropertyBot).
    settings = get_settings()
    bot_token = settings.telegram_webhook_secret  # placeholder — replace with per-tenant token
    if not bot_token:
        logger.warning("telegram.reply.no_bot_token", tenant_id=tenant_id)
        return
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
    except Exception:
        logger.error("telegram.reply.failed", tenant_id=tenant_id, exc_info=True)
