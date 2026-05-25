"""Tenant management routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from src.domain.shared.exceptions import AuthenticationError
from src.drivers.api.dependencies import CurrentUser, UnitOfWorkDep

router = APIRouter(prefix="/tenants", tags=["tenants"])


class TenantResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    status: str


@router.get("/me")
async def get_my_tenant(current_user: CurrentUser, uow: UnitOfWorkDep) -> TenantResponse:
    links = await uow.user_tenants.list_for_user(current_user.id)
    if not links:
        raise AuthenticationError("No tenant")
    tenant = await uow.tenants.get_by_id(links[0].tenant_id)
    if not tenant:
        raise AuthenticationError("Tenant not found")
    return TenantResponse(id=tenant.id, name=tenant.name, slug=tenant.slug, status=tenant.status.value)
