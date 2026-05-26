"""Fernet encryption for tenant secrets stored at rest.

When ENCRYPTION_KEY is set, API keys and tokens are encrypted before
persisting and decrypted on read. When not set, values pass through
as plaintext (development mode).

Generate a key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""

from __future__ import annotations

import structlog
from cryptography.fernet import Fernet, InvalidToken

from src.config.settings import get_settings

logger = structlog.get_logger()

_fernet: Fernet | None = None
_ENC_PREFIX = "enc:"


def _get_fernet() -> Fernet | None:
    global _fernet  # noqa: PLW0603
    if _fernet is not None:
        return _fernet
    key = get_settings().encryption_key
    if not key:
        return None
    _fernet = Fernet(key.encode())
    return _fernet


def encrypt_value(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    f = _get_fernet()
    if f is None:
        return plaintext
    return _ENC_PREFIX + f.encrypt(plaintext.encode()).decode()


def decrypt_value(ciphertext: str) -> str:
    if not ciphertext or not ciphertext.startswith(_ENC_PREFIX):
        return ciphertext
    f = _get_fernet()
    if f is None:
        return ciphertext
    try:
        return f.decrypt(ciphertext[len(_ENC_PREFIX) :].encode()).decode()
    except InvalidToken:
        logger.error("crypto.decrypt_failed", hint="ENCRYPTION_KEY may have changed")
        return ""
