"""Unit tests for WhatsApp webhook signature verification via WhatsAppAdapter."""

from __future__ import annotations

from src.infrastructure.channels.whatsapp import WhatsAppAdapter


def test_valid_signature() -> None:
    import hashlib
    import hmac as hmac_mod

    body = b'{"test": "data"}'
    secret = "test-secret"
    sig = "sha256=" + hmac_mod.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert WhatsAppAdapter.verify_signature(body, sig, secret)


def test_invalid_signature() -> None:
    assert not WhatsAppAdapter.verify_signature(b"data", "sha256=wrong", "secret")


def test_missing_signature_header() -> None:
    assert not WhatsAppAdapter.verify_signature(b"data", "", "secret")
