"""PreviewInvitation — public, by-token view used by the invite landing page."""

from __future__ import annotations

from src.application.invitations.dtos import InvitationPreviewDTO
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.invitations.value_objects import InvitationStatus
from src.domain.shared.exceptions import EntityNotFoundError


class PreviewInvitation:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, token: str) -> InvitationPreviewDTO:
        invitation = await self._uow.invitations.get_by_token(token)
        if invitation is None:
            raise EntityNotFoundError("Invitation not found")
        tenant = await self._uow.tenants.get_by_id(invitation.tenant_id)
        valid = invitation.status == InvitationStatus.PENDING and not invitation.is_expired()
        return InvitationPreviewDTO(
            tenant_name=tenant.name if tenant else "",
            email=invitation.email,
            role=invitation.role.value,
            status=invitation.status.value,
            valid=valid,
        )
