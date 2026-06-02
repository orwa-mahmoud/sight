"""Unit tests for Fernet encryption/decryption utility."""

from __future__ import annotations

from unittest.mock import patch

from src.infrastructure.auth.crypto import _ENC_PREFIX, decrypt_value, encrypt_value


def _reset_fernet() -> None:
    import src.infrastructure.auth.crypto as mod

    mod._CryptoState.fernet = None


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
