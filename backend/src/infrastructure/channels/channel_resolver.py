"""Channel resolver — determines which channel to reply on for a question."""

from __future__ import annotations

import structlog

from src.domain.conversations.value_objects import ConversationChannel
from src.domain.tenant_config.entities import TenantConfig
from src.infrastructure.channels.notification_adapter import ChannelNotificationAdapter

logger = structlog.get_logger()


async def relay_question_reply(
    *,
    channel: ConversationChannel,
    asker_contact: str | None,
    reply_text: str,
    tenant_config: TenantConfig,
) -> bool:
    """Send the owner's reply back to the asker via their original channel."""
    if not asker_contact:
        logger.warning("relay.no_asker_contact")
        return False
    adapter = ChannelNotificationAdapter(tenant_config)
    return await adapter.send_text(
        recipient=asker_contact,
        channel=channel.value,
        message=reply_text,
    )
