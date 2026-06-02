"""Entity → DTO mapping for invitations."""

from __future__ import annotations

from src.application.invitations.dtos import InvitationDTO
from src.domain.invitations.entities import Invitation


def to_invitation_dto(inv: Invitation) -> InvitationDTO:
    return InvitationDTO(
        id=inv.id,
        tenant_id=inv.tenant_id,
        email=inv.email,
        role=inv.role.value,
        status=inv.status.value,
        token=inv.token,
        expires_at=inv.expires_at,
        created_at=inv.created_at,
    )
