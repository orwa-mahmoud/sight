"""ORM Base + model registry.

Every model is imported here so that `Base.metadata` is fully populated
before Alembic's autogenerate runs.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


# ── Model imports (must come after Base to avoid circulars) ───────
from src.infrastructure.persistence.postgres.models.chunk import ChunkModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.conversation import ConversationModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.document import DocumentModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.message import MessageModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.question import QuestionModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.tenant import TenantModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.tenant_config import TenantConfigModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.token_usage import TokenUsageModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.user import UserModel  # noqa: E402
from src.infrastructure.persistence.postgres.models.user_tenant import UserTenantModel  # noqa: E402

__all__ = [
    "Base",
    "ChunkModel",
    "ConversationModel",
    "DocumentModel",
    "MessageModel",
    "QuestionModel",
    "TenantConfigModel",
    "TenantModel",
    "TokenUsageModel",
    "UserModel",
    "UserTenantModel",
]
