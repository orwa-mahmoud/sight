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
from src.infrastructure.metrics import CRYPTO_DECRYPT_FAILURES_TOTAL

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
        # No key in the cipher could decrypt this — almost always a key rotated away
        # without keeping the old one in ENCRYPTION_KEY_FALLBACKS. Returning "" here is
        # what causes silent webhook 403s, so make it loud + alertable via the metric.
        CRYPTO_DECRYPT_FAILURES_TOTAL.inc()
        logger.error("crypto.decrypt_failed", hint="ENCRYPTION_KEY rotated without a matching fallback?")
        return ""


def verify_encryption_keys() -> None:
    """Startup self-check: build the cipher from ENCRYPTION_KEY (+ fallbacks) and
    round-trip a sentinel, so a malformed/unparseable key fails loudly at boot
    instead of silently returning "" on a request months later.

    Limitation: this proves the *configured* keys parse and round-trip. It cannot
    prove that a fallback some *existing* ciphertext still depends on is present —
    that case surfaces at runtime via the crypto_decrypt_failures metric.
    """
    try:
        cipher = _get_cipher()
    except (ValueError, TypeError) as exc:
        raise RuntimeError(
            "ENCRYPTION_KEY / ENCRYPTION_KEY_FALLBACKS contains an invalid Fernet key "
            "(each must be a 32-byte url-safe base64 key). Generate one with: "
            'python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
        ) from exc
    if cipher is None:
        return  # no key configured (dev mode) — nothing to verify
    sentinel = b"sight-encryption-self-check"
    if cipher.decrypt(cipher.encrypt(sentinel)) != sentinel:  # pragma: no cover - belt-and-suspenders
        raise RuntimeError("ENCRYPTION_KEY self-check failed: the configured key did not round-trip.")
    logger.info("crypto.self_check_ok")
