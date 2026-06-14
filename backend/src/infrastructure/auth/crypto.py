"""Fernet encryption for tenant secrets stored at rest.

When ENCRYPTION_KEY is set, API keys and tokens are encrypted before persisting
and decrypted on read. When unset, values pass through as plaintext (dev mode).

Key rotation: set ENCRYPTION_KEY to the new key and list the previous key(s) in
ENCRYPTION_KEY_FALLBACKS (comma-separated). New writes use the new key; existing
ciphertext still decrypts via a fallback (MultiFernet). Re-encrypt at leisure by
re-saving the affected records, then drop the fallback once nothing depends on it.

Generate a key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import structlog
from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from src.config.settings import get_settings

logger = structlog.get_logger()

_ENC_PREFIX = "enc:"


class _CryptoState:
    cipher: MultiFernet | None = None


def _get_cipher() -> MultiFernet | None:
    if _CryptoState.cipher is not None:
        return _CryptoState.cipher
    settings = get_settings()
    key = settings.encryption_key
    if not key:
        return None
    keys = [Fernet(key.encode())]
    # Previous keys (comma-separated) still decrypt old ciphertext during a rotation.
    fallbacks = getattr(settings, "encryption_key_fallbacks", None)
    if isinstance(fallbacks, str):
        keys.extend(Fernet(part.strip().encode()) for part in fallbacks.split(",") if part.strip())
    _CryptoState.cipher = MultiFernet(keys)
    return _CryptoState.cipher


def encrypt_value(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    cipher = _get_cipher()
    if cipher is None:
        return plaintext
    return _ENC_PREFIX + cipher.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    if not ciphertext or not ciphertext.startswith(_ENC_PREFIX):
        return ciphertext
    cipher = _get_cipher()
    if cipher is None:
        return ciphertext
    try:
        return cipher.decrypt(ciphertext[len(_ENC_PREFIX) :].encode()).decode()
    except InvalidToken:
        logger.error("crypto.decrypt_failed", hint="ENCRYPTION_KEY rotated without a matching fallback?")
        return ""
