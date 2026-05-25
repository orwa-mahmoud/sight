"""Telegram webhook — receives updates from a per-tenant bot.

Verification: compares X-Telegram-Bot-Api-Secret-Token header against
the tenant's configured secret from the DB.
"""

from __future__ import annotations

from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Header, Request, Response

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.drivers.api.dependencies import get_session

logger = structlog.get_logger()

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/{tenant_id}/telegram")
async def telegram_webhook(
    tenant_id: str,
    request: Request,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> Response:
    from uuid import UUID  # noqa: PLC0415

    try:
        tid = UUID(tenant_id)
    except ValueError:
        return Response(status_code=400)

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

    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            # Load tenant config for verification + reply.
            config = await uow.tenant_configs.get_by_tenant_id(tid)
            if config is None:
                logger.warning("telegram.webhook.no_config", tenant_id=tenant_id)
                return Response(status_code=404)

            # Verify webhook secret from the tenant's stored config.
            if config.telegram_webhook_secret and x_telegram_bot_api_secret_token != config.telegram_webhook_secret:
                logger.warning("telegram.webhook.invalid_secret", tenant_id=tenant_id)
                return Response(status_code=403)

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

            # Reply using the tenant's own bot token from DB.
            if config.telegram_bot_token:
                await _send_telegram_reply(
                    chat_id=message["chat"]["id"],
                    text=result.response,
                    bot_token=config.telegram_bot_token,
                )
        except Exception:
            await uow.rollback()
            logger.error("telegram.webhook.failed", tenant_id=tenant_id, exc_info=True)

    return Response(status_code=200)


async def _send_telegram_reply(*, chat_id: int, text: str, bot_token: str) -> None:
    """Send a text reply via Telegram Bot API using the tenant's bot token."""
    import httpx  # noqa: PLC0415

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://api.telegram.org/bot{bot_token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=10,
            )
    except Exception:
        logger.error("telegram.reply.failed", exc_info=True)
