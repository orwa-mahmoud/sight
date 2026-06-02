"""Unit tests for the rate-limiter key function (per-user, proxy-aware)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.drivers.api.middleware.rate_limit import _identity_key


def _request(
    *,
    cookies: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    client_host: str = "10.0.0.9",
) -> MagicMock:
    req = MagicMock()
    req.cookies = cookies or {}
    req.headers = headers or {}
    req.client = MagicMock(host=client_host)
    return req


def test_keys_by_jwt_subject_when_cookie_present() -> None:
    fake_jwt = MagicMock()
    fake_jwt.decode.return_value = {"sub": "user-123"}
    with patch("src.drivers.api.middleware.rate_limit.get_jwt_service", return_value=fake_jwt):
        key = _identity_key(_request(cookies={"frontdesk_token": "tok"}))
    assert key == "user:user-123"


def test_keys_by_bearer_token_subject() -> None:
    fake_jwt = MagicMock()
    fake_jwt.decode.return_value = {"sub": "owner-9"}
    with patch("src.drivers.api.middleware.rate_limit.get_jwt_service", return_value=fake_jwt):
        key = _identity_key(_request(headers={"Authorization": "Bearer abc"}))
    assert key == "user:owner-9"


def test_falls_back_to_forwarded_ip_when_unauthenticated() -> None:
    key = _identity_key(_request(headers={"X-Forwarded-For": "203.0.113.7, 10.0.0.1"}))
    assert key == "203.0.113.7"


def test_falls_back_to_peer_ip_when_no_token_or_forwarded() -> None:
    key = _identity_key(_request(client_host="198.51.100.4"))
    assert key == "198.51.100.4"


def test_falls_back_to_ip_when_token_is_invalid() -> None:
    fake_jwt = MagicMock()
    fake_jwt.decode.side_effect = ValueError("bad token")
    with patch("src.drivers.api.middleware.rate_limit.get_jwt_service", return_value=fake_jwt):
        key = _identity_key(_request(cookies={"frontdesk_token": "bad"}, headers={"X-Forwarded-For": "203.0.113.9"}))
    assert key == "203.0.113.9"
