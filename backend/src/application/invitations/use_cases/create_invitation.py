"""CreateInvitation — a tenant owner invites a collaborator by email."""

from __future__ import annotations

from uuid import UUID

from src.application.invitations.dtos import InvitationDTO
from src.application.invitations.mappers import to_invitation_dto
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.invitations.entities import Invitation
from src.domain.shared.exceptions import AlreadyExistsError, InvalidOperationError


class CreateInvitation:
    """Create a PENDING invitation for an email to join the tenant as STAFF.

    Guards: the email must not already be a member of the tenant, and there must
    be no existing pending invite (also enforced by a partial unique index).
    """

    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, tenant_id: UUID, email: str, invited_by_user_id: UUID) -> InvitationDTO:
        clean_email = email.strip().lower()
        if not clean_email:
            raise InvalidOperationError("Email is required")

        existing_user = await self._uow.users.get_by_email(clean_email)
        if existing_user is not None:
            membership = await self._uow.user_tenants.get(existing_user.id, tenant_id)
            if membership is not None:
                raise AlreadyExistsError("This user is already a member of the tenant")

        if await self._uow.invitations.get_pending_for_email(tenant_id, clean_email):
            raise AlreadyExistsError("A pending invitation already exists for this email")

        invitation = Invitation.create(
            tenant_id=tenant_id,
            email=clean_email,
            invited_by_user_id=invited_by_user_id,
        )
        await self._uow.invitations.save(invitation)
        self._uow.track(invitation)
        return to_invitation_dto(invitation)
