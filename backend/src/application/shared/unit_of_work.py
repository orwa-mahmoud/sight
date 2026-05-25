"""Unit of Work — single transactional scope across repositories.

A UoW owns one async session, exposes the typed repositories needed for a
flow, and is committed/rolled back by the caller (typically the route handler).
Use cases interact ONLY with the UoW; they never see the session directly.

Repo attributes are annotated with domain Protocol types so use cases
depend on the abstract contract, not on concrete Postgres implementations.
The concrete wiring happens here (composition-root pattern).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.repositories.chunk_repo import PostgresChunkRepository
from src.infrastructure.persistence.postgres.repositories.contact_repo import PostgresContactRepository
from src.infrastructure.persistence.postgres.repositories.conversation_repo import (
    PostgresConversationRepository,
)
from src.infrastructure.persistence.postgres.repositories.document_repo import PostgresDocumentRepository
from src.infrastructure.persistence.postgres.repositories.key_fact_repo import PostgresKeyFactRepository
from src.infrastructure.persistence.postgres.repositories.message_repo import PostgresMessageRepository
from src.infrastructure.persistence.postgres.repositories.question_repo import PostgresQuestionRepository
from src.infrastructure.persistence.postgres.repositories.telegram_phone_repo import (
    PostgresTelegramPhoneRepository,
)
from src.infrastructure.persistence.postgres.repositories.tenant_config_repo import (
    PostgresTenantConfigRepository,
)
from src.infrastructure.persistence.postgres.repositories.tenant_repo import PostgresTenantRepository
from src.infrastructure.persistence.postgres.repositories.token_usage_repo import (
    PostgresTokenUsageRepository,
)
from src.infrastructure.persistence.postgres.repositories.user_repo import PostgresUserRepository
from src.infrastructure.persistence.postgres.repositories.user_tenant_repo import (
    PostgresUserTenantRepository,
)

if TYPE_CHECKING:
    from src.domain.contacts.repositories import ContactRepository
    from src.domain.conversations.repositories import ConversationRepository, MessageRepository
    from src.domain.documents.repositories import ChunkRepository, DocumentRepository
    from src.domain.key_facts.repositories import KeyFactRepository
    from src.domain.llm_usage.repositories import TokenUsageRepository
    from src.domain.questions.repositories import QuestionRepository
    from src.domain.telegram.repositories import TelegramPhoneRepository
    from src.domain.tenant_config.repositories import TenantConfigRepository
    from src.domain.tenants.repositories import TenantRepository
    from src.domain.users.repositories import UserRepository, UserTenantRepository


class UnitOfWork:
    tenants: TenantRepository
    users: UserRepository
    user_tenants: UserTenantRepository
    token_usages: TokenUsageRepository
    conversations: ConversationRepository
    messages: MessageRepository
    documents: DocumentRepository
    chunks: ChunkRepository
    questions: QuestionRepository
    tenant_configs: TenantConfigRepository
    key_facts: KeyFactRepository
    contacts: ContactRepository
    telegram_phones: TelegramPhoneRepository

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self.tenants = PostgresTenantRepository(session)
        self.users = PostgresUserRepository(session)
        self.user_tenants = PostgresUserTenantRepository(session)
        self.token_usages = PostgresTokenUsageRepository(session)
        self.conversations = PostgresConversationRepository(session)
        self.messages = PostgresMessageRepository(session)
        self.documents = PostgresDocumentRepository(session)
        self.chunks = PostgresChunkRepository(session)
        self.questions = PostgresQuestionRepository(session)
        self.tenant_configs = PostgresTenantConfigRepository(session)
        self.key_facts = PostgresKeyFactRepository(session)
        self.contacts = PostgresContactRepository(session)
        self.telegram_phones = PostgresTelegramPhoneRepository(session)

    async def flush(self) -> None:
        """Push pending inserts/updates to the DB without committing — useful
        before referencing newly created entities in FK rows within the same txn."""
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
