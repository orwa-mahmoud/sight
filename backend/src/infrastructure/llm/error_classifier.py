"""LLM error classifier — maps provider exceptions to business categories.

Used by the circuit breaker to distinguish transient failures (rate limit,
timeout) from permanent ones (auth error, invalid model). Transient errors
increment the failure count; permanent errors open the circuit immediately.
"""

from __future__ import annotations

from enum import StrEnum

import structlog

logger = structlog.get_logger()


class LLMErrorCategory(StrEnum):
    RATE_LIMIT = "rate_limit"
    AUTH_ERROR = "auth_error"
    TIMEOUT = "timeout"
    CONTENT_FILTER = "content_filter"
    QUOTA_EXCEEDED = "quota_exceeded"
    INVALID_MODEL = "invalid_model"
    PROVIDER_OUTAGE = "provider_outage"
    UNKNOWN = "unknown"

    @property
    def is_transient(self) -> bool:
        return self in {
            LLMErrorCategory.RATE_LIMIT,
            LLMErrorCategory.TIMEOUT,
            LLMErrorCategory.PROVIDER_OUTAGE,
        }


# Message substring → category mapping, checked in order.
_MESSAGE_PATTERNS: list[tuple[tuple[str, ...], LLMErrorCategory]] = [
    (("rate", "limit"), LLMErrorCategory.RATE_LIMIT),
    (("timeout",), LLMErrorCategory.TIMEOUT),
    (("timed out",), LLMErrorCategory.TIMEOUT),
    (("auth",), LLMErrorCategory.AUTH_ERROR),
    (("api key",), LLMErrorCategory.AUTH_ERROR),
    (("401",), LLMErrorCategory.AUTH_ERROR),
    (("quota",), LLMErrorCategory.QUOTA_EXCEEDED),
    (("insufficient",), LLMErrorCategory.QUOTA_EXCEEDED),
    (("billing",), LLMErrorCategory.QUOTA_EXCEEDED),
    (("content", "filter"), LLMErrorCategory.CONTENT_FILTER),
    (("content", "policy"), LLMErrorCategory.CONTENT_FILTER),
    (("content", "safety"), LLMErrorCategory.CONTENT_FILTER),
    (("model", "not found"), LLMErrorCategory.INVALID_MODEL),
    (("model", "does not exist"), LLMErrorCategory.INVALID_MODEL),
    (("model", "invalid"), LLMErrorCategory.INVALID_MODEL),
    (("503",), LLMErrorCategory.PROVIDER_OUTAGE),
    (("502",), LLMErrorCategory.PROVIDER_OUTAGE),
]

# Exception type name → category, checked as fallback.
_TYPE_PATTERNS: list[tuple[str, LLMErrorCategory]] = [
    ("RateLimitError", LLMErrorCategory.RATE_LIMIT),
    ("AuthenticationError", LLMErrorCategory.AUTH_ERROR),
    ("PermissionDenied", LLMErrorCategory.AUTH_ERROR),
    ("Timeout", LLMErrorCategory.TIMEOUT),
    ("NotFoundError", LLMErrorCategory.INVALID_MODEL),
    ("InternalServerError", LLMErrorCategory.PROVIDER_OUTAGE),
    ("ServiceUnavailable", LLMErrorCategory.PROVIDER_OUTAGE),
]


def classify_llm_error(exc: Exception) -> LLMErrorCategory:
    """Map an exception from any LLM provider to a business category."""
    msg = str(exc).lower()
    result = _match_message(msg) or _match_type(type(exc).__name__)
    if result is None:
        logger.warning("llm_error.unclassified", exc_type=type(exc).__name__, message=msg[:200])
        return LLMErrorCategory.UNKNOWN
    return result


def _match_message(msg: str) -> LLMErrorCategory | None:
    for keywords, category in _MESSAGE_PATTERNS:
        if all(kw in msg for kw in keywords):
            return category
    return None


def _match_type(exc_type: str) -> LLMErrorCategory | None:
    for pattern, category in _TYPE_PATTERNS:
        if pattern in exc_type:
            return category
    return None
