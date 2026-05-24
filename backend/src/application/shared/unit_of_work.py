"""Unit of Work — single transactional scope across repositories.

A UoW owns one async session, exposes the typed repositories needed for a
flow, and is committed/rolled back by the caller (typically the route handler).
Use cases interact ONLY with the UoW; they never see the session directly.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.persistence.postgres.repositories.chunk_repo import PostgresChunkRepository
from src.infrastructure.persistence.postgres.repositories.conversation_repo import (
    PostgresConversationRepository,
)
from src.infrastructure.persistence.postgres.repositories.document_repo import PostgresDocumentRepository
from src.infrastructure.persistence.postgres.repositories.message_repo import PostgresMessageRepository
from src.infrastructure.persistence.postgres.repositories.tenant_repo import PostgresTenantRepository
from src.infrastructure.persistence.postgres.repositories.token_usage_repo import (
    PostgresTokenUsageRepository,
)
from src.infrastructure.persistence.postgres.repositories.user_repo import PostgresUserRepository
from src.infrastructure.persistence.postgres.repositories.user_tenant_repo import (
    PostgresUserTenantRepository,
)


class UnitOfWork:
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

    async def flush(self) -> None:
        """Push pending inserts/updates to the DB without committing — useful
        before referencing newly created entities in FK rows within the same txn."""
        await self._session.flush()

    async def commit(self) -> None:
        await self._session.commit()

    async def rollback(self) -> None:
        await self._session.rollback()
