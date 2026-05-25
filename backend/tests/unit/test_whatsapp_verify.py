"""Unit tests for WhatsApp webhook signature verification."""

from __future__ import annotations

from src.drivers.api.webhooks.whatsapp import _verify_signature


def test_valid_signature() -> None:
    body = b'{"test": "data"}'
    import hashlib
    import hmac as hmac_mod

    secret = "test-secret"
    sig = "sha256=" + hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert _verify_signature(body, sig, secret)


def test_invalid_signature() -> None:
    assert not _verify_signature(b"data", "sha256=wrong", "secret")


def test_missing_signature_header() -> None:
    assert not _verify_signature(b"data", None, "secret")
