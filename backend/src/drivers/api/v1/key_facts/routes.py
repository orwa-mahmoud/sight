"""Key facts routes — owner can see what the AI remembers about contacts."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.domain.shared.exceptions import AuthenticationError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep

router = APIRouter(prefix="/key-facts", tags=["key-facts"])


class KeyFactResponse(BaseModel):
    id: UUID
    contact_id: UUID
    key: str
    value: str


async def _resolve_tenant_id(current_user: CurrentUser, uow: UnitOfWorkDep) -> UUID:
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthenticationError("User is not associated with any tenant")
    return links[0].tenant_id


@router.get("")
async def list_key_facts(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    contact_id: Annotated[UUID | None, Query()] = None,
) -> list[KeyFactResponse]:
    tenant_id = await _resolve_tenant_id(current_user, uow)
    if contact_id:
        facts = await uow.key_facts.list_for_contact(tenant_id, contact_id)
    else:
        from sqlalchemy import select  # noqa: PLC0415

        from src.infrastructure.persistence.postgres.models.key_fact import KeyFactModel  # noqa: PLC0415

        stmt = (
            select(KeyFactModel)
            .where(KeyFactModel.tenant_id == tenant_id)
            .order_by(KeyFactModel.contact_id, KeyFactModel.key)
            .limit(500)
        )
        result = await uow._session.execute(stmt)
        from src.domain.key_facts.entities import KeyFact  # noqa: PLC0415

        facts = [
            KeyFact(
                id=m.id,
                tenant_id=m.tenant_id,
                contact_id=m.contact_id,
                key=m.key,
                value=m.value,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
            for m in result.scalars().all()
        ]
    return [KeyFactResponse(id=f.id, contact_id=f.contact_id, key=f.key, value=f.value) for f in facts]
