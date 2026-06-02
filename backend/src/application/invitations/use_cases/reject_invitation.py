"""RejectInvitation — a logged-in user declines an invite sent to their email."""

from __future__ import annotations

from uuid import UUID

from src.application.shared.unit_of_work import UnitOfWork
from src.domain.shared.exceptions import AuthorizationError, EntityNotFoundError


class RejectInvitation:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, *, token: str, rejecting_user_id: UUID) -> None:
        invitation = await self._uow.invitations.get_by_token(token)
        if invitation is None:
            raise EntityNotFoundError("Invitation not found")

        user = await self._uow.users.get_by_id(rejecting_user_id)
        if user is None:
            raise EntityNotFoundError("User not found")
        if user.email != invitation.email:
            raise AuthorizationError("This invitation was sent to a different email address")

        invitation.reject()
        await self._uow.invitations.save(invitation)
        self._uow.track(invitation)
