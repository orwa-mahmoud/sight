"""Request ID + HTTP metrics middleware."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from src.infrastructure.metrics import HTTP_REQUEST_DURATION, HTTP_REQUESTS_TOTAL


def _metric_path(request: Request) -> str:
    """Templated route path (e.g. /api/v1/documents/{document_id}) for metric labels.

    Using the raw URL would make every id its own Prometheus series — an unbounded
    cardinality explosion. Fall back to "unmatched" for unrouted requests (404s,
    scanners) so they don't create per-URL series either.
    """
    route = request.scope.get("route")
    return getattr(route, "path", None) or "unmatched"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID", uuid.uuid4().hex)
        request.state.request_id = request_id
        start = time.monotonic()
        response = await call_next(request)
        duration = time.monotonic() - start

        path = _metric_path(request)
        method = request.method
        HTTP_REQUESTS_TOTAL.labels(method=method, path=path, status=str(response.status_code)).inc()
        HTTP_REQUEST_DURATION.labels(method=method, path=path).observe(duration)

        response.headers["X-Request-ID"] = request_id
        return response
