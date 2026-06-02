"""Invitation repository port — implementation lives in infrastructure."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.invitations.entities import Invitation


class InvitationRepository(Protocol):
    async def save(self, invitation: Invitation) -> None: ...

    async def get_by_id(self, invitation_id: UUID) -> Invitation | None: ...

    async def get_by_token(self, token: str) -> Invitation | None: ...

    async def list_for_tenant(self, tenant_id: UUID) -> list[Invitation]: ...

    async def get_pending_for_email(self, tenant_id: UUID, email: str) -> Invitation | None: ...
