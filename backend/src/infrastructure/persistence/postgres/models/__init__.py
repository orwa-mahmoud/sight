"""ORM model registry.

Every model is imported here so that `Base.metadata` is fully populated
before Alembic's autogenerate runs.
"""

from __future__ import annotations

from src.infrastructure.persistence.postgres.models.base import Base
from src.infrastructure.persistence.postgres.models.chunk import ChunkModel
from src.infrastructure.persistence.postgres.models.contact import ContactModel
from src.infrastructure.persistence.postgres.models.conversation import ConversationModel
from src.infrastructure.persistence.postgres.models.document import DocumentModel
from src.infrastructure.persistence.postgres.models.key_fact import KeyFactModel
from src.infrastructure.persistence.postgres.models.message import MessageModel
from src.infrastructure.persistence.postgres.models.outbox import OutboxEventModel
from src.infrastructure.persistence.postgres.models.question import QuestionModel
from src.infrastructure.persistence.postgres.models.telegram_phone import TelegramPhoneModel
from src.infrastructure.persistence.postgres.models.tenant import TenantModel
from src.infrastructure.persistence.postgres.models.tenant_config import TenantConfigModel
from src.infrastructure.persistence.postgres.models.token_usage import TokenUsageModel
from src.infrastructure.persistence.postgres.models.user import UserModel
from src.infrastructure.persistence.postgres.models.user_tenant import UserTenantModel

__all__ = [
    "Base",
    "ChunkModel",
    "ContactModel",
    "ConversationModel",
    "DocumentModel",
    "KeyFactModel",
    "MessageModel",
    "OutboxEventModel",
    "QuestionModel",
    "TelegramPhoneModel",
    "TenantConfigModel",
    "TenantModel",
    "TokenUsageModel",
    "UserModel",
    "UserTenantModel",
]
