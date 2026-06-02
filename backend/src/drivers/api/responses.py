"""Domain exception -> HTTP response mapping.

Registered on the FastAPI app so use cases can raise `DomainError` (and its
subclasses) without ever knowing about HTTP. Each subclass declares its
`http_status` so the mapping is open for extension without touching this file.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse

from src.domain.shared.exceptions import DomainError
from src.drivers.api.i18n import resolve_locale, translate


def domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    locale = resolve_locale(request.headers.get("accept-language"))
    message = str(exc) or "An error occurred"
    code = exc.code or ("error.generic" if not str(exc) else None)
    detail = translate(code, locale, default=message)
    return JSONResponse(
        status_code=exc.http_status,
        content={"detail": detail},
    )
