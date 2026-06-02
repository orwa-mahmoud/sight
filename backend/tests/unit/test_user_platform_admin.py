"""Unit tests for User platform-admin behavior + deactivation guard."""

from __future__ import annotations

import pytest

from src.domain.shared.exceptions import InvalidOperationError
from src.domain.users.entities import User
from src.domain.users.events import PlatformAdminGranted, PlatformAdminRevoked


def _user() -> User:
    return User.create(email="A@Example.com", hashed_password="hash", full_name="A")


def test_new_user_is_not_platform_admin() -> None:
    user = _user()
    assert user.is_platform_admin is False
    assert user.email == "a@example.com"  # normalized


def test_grant_platform_admin_sets_flag_and_emits_event() -> None:
    user = _user()
    user.clear_events()
    user.grant_platform_admin()
    assert user.is_platform_admin is True
    assert any(isinstance(e, PlatformAdminGranted) for e in user.pending_events)


def test_grant_platform_admin_is_idempotent() -> None:
    user = _user()
    user.grant_platform_admin()
    user.clear_events()
    user.grant_platform_admin()  # second call: no-op, no new event
    assert user.is_platform_admin is True
    assert not any(isinstance(e, PlatformAdminGranted) for e in user.pending_events)


def test_revoke_platform_admin_clears_flag_and_emits_event() -> None:
    user = _user()
    user.grant_platform_admin()
    user.clear_events()
    user.revoke_platform_admin()
    assert user.is_platform_admin is False
    assert any(isinstance(e, PlatformAdminRevoked) for e in user.pending_events)


def test_revoke_platform_admin_is_idempotent() -> None:
    user = _user()
    user.clear_events()
    user.revoke_platform_admin()  # never an admin: no-op
    assert user.is_platform_admin is False
    assert not any(isinstance(e, PlatformAdminRevoked) for e in user.pending_events)


def test_deactivate_normal_user_works() -> None:
    user = _user()
    user.deactivate()
    assert user.is_active is False


def test_cannot_deactivate_platform_admin() -> None:
    user = _user()
    user.grant_platform_admin()
    with pytest.raises(InvalidOperationError):
        user.deactivate()
    assert user.is_active is True
