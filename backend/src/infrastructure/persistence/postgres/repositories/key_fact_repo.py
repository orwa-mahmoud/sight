"""PostgreSQL KeyFact repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.key_facts.entities import KeyFact
from src.infrastructure.persistence.postgres.models.key_fact import KeyFactModel


class PostgresKeyFactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, fact: KeyFact) -> None:
        if fact.is_new:
            self._session.add(self._to_model(fact))
            fact.mark_persisted()
            return
        model = await self._session.get(KeyFactModel, fact.id)
        if model is None:
            self._session.add(self._to_model(fact))
            return
        model.value = fact.value
        model.updated_at = fact.updated_at

    async def get(self, tenant_id: UUID, participant_identifier: str, key: str) -> KeyFact | None:
        stmt = select(KeyFactModel).where(
            KeyFactModel.tenant_id == tenant_id,
            KeyFactModel.participant_identifier == participant_identifier,
            KeyFactModel.key == key,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_for_participant(self, tenant_id: UUID, participant_identifier: str) -> list[KeyFact]:
        stmt = (
            select(KeyFactModel)
            .where(KeyFactModel.tenant_id == tenant_id, KeyFactModel.participant_identifier == participant_identifier)
            .order_by(KeyFactModel.key)
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def delete(self, fact_id: UUID) -> None:
        await self._session.execute(delete(KeyFactModel).where(KeyFactModel.id == fact_id))

    @staticmethod
    def _to_model(f: KeyFact) -> KeyFactModel:
        return KeyFactModel(
            id=f.id,
            tenant_id=f.tenant_id,
            participant_identifier=f.participant_identifier,
            key=f.key,
            value=f.value,
            created_at=f.created_at,
            updated_at=f.updated_at,
        )

    @staticmethod
    def _to_entity(m: KeyFactModel) -> KeyFact:
        return KeyFact(
            id=m.id,
            tenant_id=m.tenant_id,
            participant_identifier=m.participant_identifier,
            key=m.key,
            value=m.value,
            created_at=m.created_at,
            updated_at=m.updated_at,
        )
