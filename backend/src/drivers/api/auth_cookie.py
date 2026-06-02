"""Shared auth-cookie helpers.

The session JWT lives in an httpOnly cookie so the SPA never reads/stores it.
Centralized here so login, register, and register-via-invite all set it the
same way (and `dependencies.py` reads the same name).
"""

from __future__ import annotations

from fastapi import Response

from src.config.settings import get_settings

COOKIE_NAME = "frontdesk_token"


def set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.app_env == "production",
        samesite="lax",
        max_age=settings.jwt_access_token_expire_minutes * 60,
        path="/",
    )
