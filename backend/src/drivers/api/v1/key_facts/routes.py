"""Key facts routes — owner can see what the AI remembers about contacts."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query
from pydantic import BaseModel

from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep, resolve_tenant_id

router = APIRouter(prefix="/key-facts", tags=["key-facts"])


class KeyFactResponse(BaseModel):
    id: UUID
    contact_id: UUID
    key: str
    value: str


@router.get("")
async def list_key_facts(
    current_user: CurrentUser,
    uow: UnitOfWorkDep,
    contact_id: Annotated[UUID | None, Query()] = None,
) -> list[KeyFactResponse]:
    tenant_id = await resolve_tenant_id(current_user, uow)
    if contact_id:
        facts = await uow.key_facts.list_for_contact(tenant_id, contact_id)
    else:
        facts = await uow.key_facts.list_for_tenant(tenant_id)
    return [KeyFactResponse(id=f.id, contact_id=f.contact_id, key=f.key, value=f.value) for f in facts]
