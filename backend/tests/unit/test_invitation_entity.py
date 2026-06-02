"""Unit tests for the Invitation aggregate lifecycle."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from src.domain.invitations.entities import Invitation
from src.domain.invitations.events import (
    InvitationAccepted,
    InvitationCreated,
    InvitationRejected,
    InvitationRevoked,
)
from src.domain.invitations.value_objects import InvitationStatus
from src.domain.shared.exceptions import InvalidOperationError
from src.domain.users.value_objects import UserTenantRole


def _invite() -> Invitation:
    return Invitation.create(tenant_id=uuid4(), email="New@Example.com", invited_by_user_id=uuid4())


def test_create_defaults() -> None:
    inv = _invite()
    assert inv.status == InvitationStatus.PENDING
    assert inv.role == UserTenantRole.STAFF
    assert inv.email == "new@example.com"  # normalized
    assert len(inv.token) > 20
    assert inv.expires_at > datetime.now(UTC)
    assert any(isinstance(e, InvitationCreated) for e in inv.pending_events)


def test_accept_sets_status_and_emits() -> None:
    inv = _invite()
    inv.clear_events()
    inv.accept()
    assert inv.status == InvitationStatus.ACCEPTED
    assert any(isinstance(e, InvitationAccepted) for e in inv.pending_events)


def test_reject_sets_status_and_emits() -> None:
    inv = _invite()
    inv.clear_events()
    inv.reject()
    assert inv.status == InvitationStatus.REJECTED
    assert any(isinstance(e, InvitationRejected) for e in inv.pending_events)


def test_revoke_sets_status_and_emits() -> None:
    inv = _invite()
    inv.clear_events()
    inv.revoke()
    assert inv.status == InvitationStatus.REVOKED
    assert any(isinstance(e, InvitationRevoked) for e in inv.pending_events)


def test_cannot_accept_twice() -> None:
    inv = _invite()
    inv.accept()
    with pytest.raises(InvalidOperationError):
        inv.accept()


def test_cannot_accept_rejected() -> None:
    inv = _invite()
    inv.reject()
    with pytest.raises(InvalidOperationError):
        inv.accept()


def test_cannot_accept_expired() -> None:
    inv = Invitation.create(tenant_id=uuid4(), email="x@example.com", invited_by_user_id=uuid4(), ttl_days=0)
    # ttl_days=0 → expires_at == created time, so it's already expired.
    assert inv.is_expired()
    with pytest.raises(InvalidOperationError, match="expired"):
        inv.accept()


def test_is_expired_with_explicit_now() -> None:
    inv = _invite()
    assert inv.is_expired(now=inv.expires_at + timedelta(seconds=1)) is True
    assert inv.is_expired(now=inv.expires_at - timedelta(seconds=1)) is False
