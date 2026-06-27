"""Unit tests for the JWT service."""

from __future__ import annotations

from uuid import uuid4

import pytest

from src.domain.shared.exceptions import AuthenticationError
from src.infrastructure.auth.jwt_service import JwtService


def _make_service() -> JwtService:
    return JwtService(secret_key="test-secret", access_token_expire_minutes=60)


def test_issue_and_decode() -> None:
    svc = _make_service()
    user_id = uuid4()
    tenant_id = uuid4()
    token = svc.issue_access_token(user_id=user_id, tenant_id=tenant_id)
    payload = svc.decode(token)
    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["iss"] == "sight"


def test_decode_invalid_token_raises() -> None:
    svc = _make_service()
    with pytest.raises(AuthenticationError):
        svc.decode("not.a.valid.jwt")


def test_decode_wrong_secret_raises() -> None:
    svc1 = JwtService(secret_key="secret-1")
    svc2 = JwtService(secret_key="secret-2")
    token = svc1.issue_access_token(user_id=uuid4())
    with pytest.raises(AuthenticationError):
        svc2.decode(token)


def test_token_without_tenant_id() -> None:
    svc = _make_service()
    token = svc.issue_access_token(user_id=uuid4(), tenant_id=None)
    payload = svc.decode(token)
    assert payload["tenant_id"] is None
