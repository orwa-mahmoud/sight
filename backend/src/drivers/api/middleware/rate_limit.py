"""Rate limiting (slowapi).

Key function: per authenticated user (JWT subject) when possible, else per real
client IP. The app runs behind a reverse proxy (nginx / Vite dev proxy), so the
peer IP is the *proxy's* for every request — keying on it alone would pool all
users into one bucket and throttle everyone together. Authenticated endpoints
(e.g. /chat) key by the token subject instead; unauthenticated traffic falls
back to the X-Forwarded-For client IP, then the peer IP.
"""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from src.bootstrap.container import get_jwt_service

_COOKIE_NAME = "sight_token"


def _bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip() or None
    return None


def _ip_key(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Leftmost entry is the original client (the proxy appends its own hops).
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


def _identity_key(request: Request) -> str:
    token = request.cookies.get(_COOKIE_NAME) or _bearer_token(request)
    if not token:
        return _ip_key(request)
    try:
        sub = get_jwt_service().decode(token).get("sub")
    except Exception:
        return _ip_key(request)
    return f"user:{sub}" if sub else _ip_key(request)


limiter = Limiter(key_func=_identity_key, default_limits=["100/minute"])
