"""RevokeInvitation — owner cancels a pending invite."""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError


class RevokeInvitation:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, tenant_id: UUID, invitation_id: UUID) -> None:
        invitation = await self._uow.invitations.get_by_id(invitation_id)
        if invitation is None:
            raise EntityNotFoundError("Invitation not found")
        # Defense in depth: an owner may only revoke invites for their own tenant.
        if invitation.tenant_id != tenant_id:
            raise AuthorizationError("Invitation does not belong to this tenant")
        invitation.revoke()
        await self._uow.invitations.save(invitation)
        self._uow.track(invitation)
