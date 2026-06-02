"""PostgreSQL Invitation repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.invitations.entities import Invitation
from src.domain.invitations.value_objects import InvitationStatus
from src.domain.users.value_objects import UserTenantRole
from src.infrastructure.persistence.postgres.models.invitation import InvitationModel


class PostgresInvitationRepository:
    """Concrete invitation repository — implements the `InvitationRepository` port."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, invitation: Invitation) -> None:
        if invitation.is_new:
            self._session.add(self._to_model(invitation))
            invitation.mark_persisted()
            return
        model = await self._session.get(InvitationModel, invitation.id)
        if model is None:
            self._session.add(self._to_model(invitation))
            return
        model.status = invitation.status.value
        model.updated_at = invitation.updated_at

    async def get_by_id(self, invitation_id: UUID) -> Invitation | None:
        model = await self._session.get(InvitationModel, invitation_id)
        return self._to_entity(model) if model else None

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(InvitationModel).where(InvitationModel.token == token)
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list_for_tenant(self, tenant_id: UUID) -> list[Invitation]:
        stmt = (
            select(InvitationModel)
            .where(InvitationModel.tenant_id == tenant_id)
            .order_by(InvitationModel.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def get_pending_for_email(self, tenant_id: UUID, email: str) -> Invitation | None:
        stmt = select(InvitationModel).where(
            InvitationModel.tenant_id == tenant_id,
            InvitationModel.email == email.strip().lower(),
            InvitationModel.status == InvitationStatus.PENDING.value,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    # ── Mapping helpers ────────────────────────────────────────────
    @staticmethod
    def _to_model(inv: Invitation) -> InvitationModel:
        return InvitationModel(
            id=inv.id,
            tenant_id=inv.tenant_id,
            email=inv.email,
            role=inv.role.value,
            token=inv.token,
            status=inv.status.value,
            invited_by_user_id=inv.invited_by_user_id,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
            updated_at=inv.updated_at,
        )

    @staticmethod
    def _to_entity(model: InvitationModel) -> Invitation:
        return Invitation(
            id=model.id,
            tenant_id=model.tenant_id,
            email=model.email,
            role=UserTenantRole(model.role),
            token=model.token,
            status=InvitationStatus(model.status),
            invited_by_user_id=model.invited_by_user_id,
            expires_at=model.expires_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
