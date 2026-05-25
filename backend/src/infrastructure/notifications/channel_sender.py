"""Channel delivery for notifications -- routes messages to WhatsApp or Telegram.

Ported from PropertyBot. Uses the cached adapter pool for connection reuse.
"""

from __future__ import annotations

import structlog

from src.infrastructure.channels.cache import get_telegram_adapter, get_whatsapp_adapter
from src.infrastructure.notifications.context_loader import RecipientInfo

logger = structlog.get_logger()


async def send_to_recipient(
    recipient: RecipientInfo,
    message: str,
    channel: str,
    tenant_config: object,
) -> bool:
    """Send a message to a recipient (contact or user) on the specified channel.

    Returns True if delivered successfully, False otherwise.
    """
    tid = str(getattr(tenant_config, "tenant_id", ""))
    try:
        if channel == "whatsapp" and recipient.phone:
            wa = await get_whatsapp_adapter(
                tid,
                phone_number_id=getattr(tenant_config, "whatsapp_phone_number_id", "") or "",
                access_token=getattr(tenant_config, "whatsapp_access_token", "") or "",
            )
            await wa.send_text(recipient.phone, message)
            return True

        if channel == "telegram":
            tg_recipient = recipient.telegram_user_id or recipient.phone
            if tg_recipient:
                tg = await get_telegram_adapter(tid, tenant_config=tenant_config)
                await tg.send_text(tg_recipient, message)
                return True

        logger.info("notify.api_only", recipient_id=recipient.id)
        return True
    except Exception:
        logger.error(
            "notify.delivery_failed",
            channel=channel,
            recipient_id=recipient.id,
            exc_info=True,
        )
        return False
