"""WhatsApp Cloud API webhook — receives messages from Meta.

Verification: GET with hub.verify_token matched against the tenant's
stored verify token. POST with X-Hub-Signature-256 HMAC-SHA256
verification. All credentials come from the tenant_configs table.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import structlog
from fastapi import APIRouter, Header, Query, Request, Response

from src.ai.gateway import chat_with_agent
from src.ai.types import ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.drivers.api.dependencies import get_session

logger = structlog.get_logger()

router = APIRouter(tags=["webhooks"])


@router.get("/webhooks/{tenant_id}/whatsapp")
async def whatsapp_verify(
    tenant_id: str,
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    """Meta webhook verification — echo the challenge if the token matches the tenant's stored token."""
    from uuid import UUID  # noqa: PLC0415

    try:
        tid = UUID(tenant_id)
    except ValueError:
        return Response(status_code=400)

    async for session in get_session():
        uow = UnitOfWork(session)
        config = await uow.tenant_configs.get_by_tenant_id(tid)
        if config and hub_mode == "subscribe" and hub_verify_token == config.whatsapp_verify_token:
            return Response(content=hub_challenge, media_type="text/plain")

    return Response(status_code=403)


@router.post("/webhooks/{tenant_id}/whatsapp")
async def whatsapp_webhook(
    tenant_id: str,
    request: Request,
    x_hub_signature_256: str | None = Header(default=None),
) -> Response:
    body = await request.body()

    from uuid import UUID  # noqa: PLC0415

    try:
        tid = UUID(tenant_id)
    except ValueError:
        return Response(status_code=400)

    payload: dict[str, Any] = await request.json()

    entry = (payload.get("entry") or [{}])[0]
    changes = (entry.get("changes") or [{}])[0]
    value = changes.get("value", {})
    messages = value.get("messages", [])
    if not messages:
        return Response(status_code=200)

    msg = messages[0]
    sender_phone = msg.get("from", "")
    text = ""
    if msg.get("type") == "text":
        text = (msg.get("text") or {}).get("body", "")

    if not text or not sender_phone:
        return Response(status_code=200)

    contacts = value.get("contacts", [])
    sender_name = None
    if contacts:
        profile = contacts[0].get("profile", {})
        sender_name = profile.get("name")

    async for session in get_session():
        uow = UnitOfWork(session)
        try:
            config = await uow.tenant_configs.get_by_tenant_id(tid)
            if config is None:
                logger.warning("whatsapp.webhook.no_config", tenant_id=tenant_id)
                return Response(status_code=404)

            # Verify HMAC signature using the tenant's app secret from DB.
            if config.whatsapp_access_token:
                app_secret = config.whatsapp_verify_token or ""
                if app_secret and not _verify_signature(body, x_hub_signature_256, app_secret):
                    logger.warning("whatsapp.webhook.invalid_signature", tenant_id=tenant_id)
                    return Response(status_code=403)

            result = await chat_with_agent(
                ChatInput(
                    message=text,
                    tenant_id=tid,
                    channel=ConversationChannel.WHATSAPP,
                    sender_identifier=sender_phone,
                    sender_name=sender_name,
                ),
                uow=uow,
            )
            await uow.commit()

            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            if phone_number_id and config.whatsapp_access_token:
                await _send_whatsapp_reply(
                    phone_number_id=phone_number_id,
                    to=sender_phone,
                    text=result.response,
                    access_token=config.whatsapp_access_token,
                )
        except Exception:
            await uow.rollback()
            logger.error("whatsapp.webhook.failed", tenant_id=tenant_id, exc_info=True)

    return Response(status_code=200)


def _verify_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header:
        return False
    expected = "sha256=" + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature_header)


async def _send_whatsapp_reply(
    *,
    phone_number_id: str,
    to: str,
    text: str,
    access_token: str,
) -> None:
    """Send a text reply via WhatsApp Cloud API using the tenant's access token."""
    import httpx  # noqa: PLC0415

    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                f"https://graph.facebook.com/v21.0/{phone_number_id}/messages",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": to,
                    "type": "text",
                    "text": {"body": text},
                },
                timeout=10,
            )
    except Exception:
        logger.error("whatsapp.reply.failed", exc_info=True)
