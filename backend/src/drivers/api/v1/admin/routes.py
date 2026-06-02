"""Platform super-admin routes — cross-tenant operations.

Every route is guarded by `require_platform_admin` (via the `PlatformAdmin`
dependency), which raises 403 for non-admin callers.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from src.bootstrap.container import (
    list_tenants_for_admin_use_case,
    list_users_for_admin_use_case,
    set_tenant_active_use_case,
    set_user_active_use_case,
)
from src.drivers.api.dependencies import PlatformAdmin, UnitOfWorkDep
from src.drivers.api.v1.admin.schemas import (
    AdminTenantResponse,
    AdminUserResponse,
    TenantStatusResponse,
    UserActiveResponse,
)

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/tenants")
async def list_tenants(_admin: PlatformAdmin, uow: UnitOfWorkDep) -> list[AdminTenantResponse]:
    rows = await list_tenants_for_admin_use_case(uow).execute()
    return [
        AdminTenantResponse(
            id=r.id,
            name=r.name,
            slug=r.slug,
            status=r.status,
            owner_email=r.owner_email,
            user_count=r.user_count,
            document_count=r.document_count,
        )
        for r in rows
    ]


@router.get("/users")
async def list_users(_admin: PlatformAdmin, uow: UnitOfWorkDep) -> list[AdminUserResponse]:
    rows = await list_users_for_admin_use_case(uow).execute()
    return [
        AdminUserResponse(
            id=r.id,
            email=r.email,
            full_name=r.full_name,
            is_active=r.is_active,
            is_platform_admin=r.is_platform_admin,
            tenant_id=r.tenant_id,
            tenant_name=r.tenant_name,
            role=r.role,
        )
        for r in rows
    ]


@router.post("/tenants/{tenant_id}/deactivate")
async def deactivate_tenant(tenant_id: UUID, _admin: PlatformAdmin, uow: UnitOfWorkDep) -> TenantStatusResponse:
    status = await set_tenant_active_use_case(uow).execute(tenant_id=tenant_id, active=False)
    return TenantStatusResponse(id=tenant_id, status=status)


@router.post("/tenants/{tenant_id}/activate")
async def activate_tenant(tenant_id: UUID, _admin: PlatformAdmin, uow: UnitOfWorkDep) -> TenantStatusResponse:
    status = await set_tenant_active_use_case(uow).execute(tenant_id=tenant_id, active=True)
    return TenantStatusResponse(id=tenant_id, status=status)


@router.post("/users/{user_id}/deactivate")
async def deactivate_user(user_id: UUID, admin: PlatformAdmin, uow: UnitOfWorkDep) -> UserActiveResponse:
    is_active = await set_user_active_use_case(uow).execute(user_id=user_id, active=False, acting_user_id=admin.id)
    return UserActiveResponse(id=user_id, is_active=is_active)


@router.post("/users/{user_id}/activate")
async def activate_user(user_id: UUID, admin: PlatformAdmin, uow: UnitOfWorkDep) -> UserActiveResponse:
    is_active = await set_user_active_use_case(uow).execute(user_id=user_id, active=True, acting_user_id=admin.id)
    return UserActiveResponse(id=user_id, is_active=is_active)
