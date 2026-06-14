"""Unit tests for Fernet encryption/decryption utility."""

from __future__ import annotations

from unittest.mock import patch

from cryptography.fernet import Fernet

from src.infrastructure.auth.crypto import _ENC_PREFIX, decrypt_value, encrypt_value


def _reset_fernet() -> None:
    import src.infrastructure.auth.crypto as mod

    mod._CryptoState.cipher = None


def test_encrypt_empty_string() -> None:
    assert encrypt_value("") == ""


def test_decrypt_empty_string() -> None:
    assert decrypt_value("") == ""


def test_encrypt_without_key_returns_plaintext() -> None:
    _reset_fernet()
    with patch("src.infrastructure.auth.crypto.get_settings") as mock:
        mock.return_value.encryption_key = None
        result = encrypt_value("sk-secret-key")
    assert result == "sk-secret-key"
    _reset_fernet()


def test_decrypt_plaintext_returns_as_is() -> None:
    assert decrypt_value("sk-secret-key") == "sk-secret-key"


def test_encrypt_and_decrypt_roundtrip() -> None:
    _reset_fernet()
    with patch("src.infrastructure.auth.crypto.get_settings") as mock:
        mock.return_value.encryption_key = "mhINJi_JIPU2XO7ZD2idAhJM-0qLbPk2T2Js3ZuwSVQ="
        encrypted = encrypt_value("my-api-key")
        assert encrypted.startswith(_ENC_PREFIX)
        assert encrypted != "my-api-key"
        decrypted = decrypt_value(encrypted)
        assert decrypted == "my-api-key"
    _reset_fernet()


def test_decrypt_invalid_ciphertext_returns_empty() -> None:
    _reset_fernet()
    with patch("src.infrastructure.auth.crypto.get_settings") as mock:
        mock.return_value.encryption_key = "mhINJi_JIPU2XO7ZD2idAhJM-0qLbPk2T2Js3ZuwSVQ="
        result = decrypt_value(f"{_ENC_PREFIX}corrupted-data")
        assert result == ""
    _reset_fernet()


def test_key_rotation_decrypts_old_ciphertext_via_fallback() -> None:
    """After rotating ENCRYPTION_KEY, old ciphertext still reads via the fallback,
    and new writes use the new key."""
    old_key = "mhINJi_JIPU2XO7ZD2idAhJM-0qLbPk2T2Js3ZuwSVQ="
    new_key = Fernet.generate_key().decode()

    # Encrypt with the old key only.
    _reset_fernet()
    with patch("src.infrastructure.auth.crypto.get_settings") as mock:
        mock.return_value.encryption_key = old_key
        mock.return_value.encryption_key_fallbacks = None
        old_token = encrypt_value("rotate-me")

    # Rotate: new key primary, old key as fallback — old ciphertext still decrypts.
    _reset_fernet()
    with patch("src.infrastructure.auth.crypto.get_settings") as mock:
        mock.return_value.encryption_key = new_key
        mock.return_value.encryption_key_fallbacks = old_key
        assert decrypt_value(old_token) == "rotate-me"
        new_token = encrypt_value("after-rotation")

    # Drop the fallback: only new-key ciphertext is required to read now.
    _reset_fernet()
    with patch("src.infrastructure.auth.crypto.get_settings") as mock:
        mock.return_value.encryption_key = new_key
        mock.return_value.encryption_key_fallbacks = None
        assert decrypt_value(new_token) == "after-rotation"
    _reset_fernet()
