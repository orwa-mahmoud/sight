"""Tenant invitation routes.

Owner-only: create / list / revoke (guarded by `require_owner`).
Authenticated: accept / reject (caller's email must match the invite).
Public (by token): preview / register-through-invite.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Response, status

from src.application.invitations.dtos import InvitationDTO
from src.bootstrap.container import (
    accept_invitation_use_case,
    create_invitation_use_case,
    list_invitations_use_case,
    preview_invitation_use_case,
    register_via_invitation_use_case,
    reject_invitation_use_case,
    revoke_invitation_use_case,
)
from src.config.settings import get_settings
from src.drivers.api.auth_cookie import set_auth_cookie
from src.drivers.api.dependencies import CurrentUser, TenantOwner, UnitOfWorkDep, resolve_tenant_id
from src.drivers.api.v1.auth.schemas import TokenResponse
from src.drivers.api.v1.invitations.schemas import (
    CreateInvitationRequest,
    InvitationPreviewResponse,
    InvitationResponse,
    RegisterViaInvitationRequest,
)

router = APIRouter(prefix="/invitations", tags=["invitations"])


def _invite_url(token: str) -> str:
    base = get_settings().frontend_base_url.rstrip("/")
    return f"{base}/invite/{token}"


def _to_response(dto: InvitationDTO) -> InvitationResponse:
    return InvitationResponse(
        id=dto.id,
        email=dto.email,
        role=dto.role,
        status=dto.status,
        token=dto.token,
        invite_url=_invite_url(dto.token),
        expires_at=dto.expires_at,
        created_at=dto.created_at,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_invitation(req: CreateInvitationRequest, owner: TenantOwner, uow: UnitOfWorkDep) -> InvitationResponse:
    tenant_id = await resolve_tenant_id(owner, uow)
    dto = await create_invitation_use_case(uow).execute(
        tenant_id=tenant_id, email=req.email, invited_by_user_id=owner.id
    )
    return _to_response(dto)


@router.get("")
async def list_invitations(owner: TenantOwner, uow: UnitOfWorkDep) -> list[InvitationResponse]:
    tenant_id = await resolve_tenant_id(owner, uow)
    rows = await list_invitations_use_case(uow).execute(tenant_id=tenant_id)
    return [_to_response(dto) for dto in rows]


@router.post("/{invitation_id}/revoke", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(invitation_id: UUID, owner: TenantOwner, uow: UnitOfWorkDep) -> None:
    tenant_id = await resolve_tenant_id(owner, uow)
    await revoke_invitation_use_case(uow).execute(tenant_id=tenant_id, invitation_id=invitation_id)


@router.get("/token/{token}")
async def preview_invitation(token: str, uow: UnitOfWorkDep) -> InvitationPreviewResponse:
    dto = await preview_invitation_use_case(uow).execute(token=token)
    return InvitationPreviewResponse(
        tenant_name=dto.tenant_name,
        email=dto.email,
        role=dto.role,
        status=dto.status,
        valid=dto.valid,
    )


@router.post("/token/{token}/accept", status_code=status.HTTP_204_NO_CONTENT)
async def accept_invitation(token: str, current_user: CurrentUser, uow: UnitOfWorkDep) -> None:
    await accept_invitation_use_case(uow).execute(token=token, accepting_user_id=current_user.id)


@router.post("/token/{token}/reject", status_code=status.HTTP_204_NO_CONTENT)
async def reject_invitation(token: str, current_user: CurrentUser, uow: UnitOfWorkDep) -> None:
    await reject_invitation_use_case(uow).execute(token=token, rejecting_user_id=current_user.id)


@router.post("/token/{token}/register", status_code=status.HTTP_201_CREATED)
async def register_via_invitation(
    token: str, req: RegisterViaInvitationRequest, uow: UnitOfWorkDep, response: Response
) -> TokenResponse:
    result = await register_via_invitation_use_case(uow).execute(
        token=token, password=req.password, full_name=req.full_name
    )
    set_auth_cookie(response, result.access_token)
    return TokenResponse(access_token=result.access_token, user_id=result.user_id, tenant_id=result.tenant_id)
