"""Notification adapter — routes outbound messages to the right channel.

Implements NotificationPort. Dispatches to WhatsApp or Telegram based
on the channel parameter. Best-effort — errors logged, never raised.
"""

from __future__ import annotations

import httpx
import structlog

from src.domain.tenant_config.entities import TenantConfig

logger = structlog.get_logger()


class ChannelNotificationAdapter:
    def __init__(self, tenant_config: TenantConfig) -> None:
        self._config = tenant_config

    async def send_text(self, *, recipient: str, channel: str, message: str) -> bool:
        match channel:
            case "whatsapp":
                return await self._send_whatsapp(recipient, message)
            case "telegram":
                return await self._send_telegram(recipient, message)
            case _:
                logger.warning("notification.unsupported_channel", channel=channel)
                return False

    async def _send_whatsapp(self, to: str, text: str) -> bool:
        token = self._config.whatsapp_access_token
        phone_id = self._config.whatsapp_phone_number_id
        if not token or not phone_id:
            logger.warning("notification.whatsapp_not_configured")
            return False
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://graph.facebook.com/v21.0/{phone_id}/messages",
                    headers={"Authorization": f"Bearer {token}"},
                    json={"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": text}},
                    timeout=10,
                )
            return True
        except Exception:
            logger.error("notification.whatsapp_failed", exc_info=True)
            return False

    async def _send_telegram(self, chat_id: str, text: str) -> bool:
        bot_token = self._config.telegram_bot_token
        if not bot_token:
            logger.warning("notification.telegram_not_configured")
            return False
        try:
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"https://api.telegram.org/bot{bot_token}/sendMessage",
                    json={"chat_id": chat_id, "text": text},
                    timeout=10,
                )
            return True
        except Exception:
            logger.error("notification.telegram_failed", exc_info=True)
            return False
