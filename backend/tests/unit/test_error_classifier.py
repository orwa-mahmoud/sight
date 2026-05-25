"""Unit tests for the LLM error classifier."""

from __future__ import annotations

from src.infrastructure.llm.error_classifier import LLMErrorCategory, classify_llm_error


def test_rate_limit_by_message() -> None:
    assert classify_llm_error(Exception("Rate limit exceeded")) == LLMErrorCategory.RATE_LIMIT


def test_timeout_by_message() -> None:
    assert classify_llm_error(Exception("Request timed out")) == LLMErrorCategory.TIMEOUT


def test_auth_error_by_message() -> None:
    assert classify_llm_error(Exception("Invalid API key")) == LLMErrorCategory.AUTH_ERROR


def test_quota_by_message() -> None:
    assert classify_llm_error(Exception("Insufficient quota")) == LLMErrorCategory.QUOTA_EXCEEDED


def test_content_filter_by_message() -> None:
    assert classify_llm_error(Exception("Content policy violation")) == LLMErrorCategory.CONTENT_FILTER


def test_invalid_model_by_message() -> None:
    assert classify_llm_error(Exception("Model does not exist")) == LLMErrorCategory.INVALID_MODEL


def test_provider_outage_by_message() -> None:
    assert classify_llm_error(Exception("503 Service Unavailable")) == LLMErrorCategory.PROVIDER_OUTAGE


def test_unknown_error() -> None:
    assert classify_llm_error(Exception("Something weird")) == LLMErrorCategory.UNKNOWN


def test_transient_categories() -> None:
    assert LLMErrorCategory.RATE_LIMIT.is_transient
    assert LLMErrorCategory.TIMEOUT.is_transient
    assert LLMErrorCategory.PROVIDER_OUTAGE.is_transient
    assert not LLMErrorCategory.AUTH_ERROR.is_transient
    assert not LLMErrorCategory.UNKNOWN.is_transient


class FakeRateLimitError(Exception):
    pass


def test_rate_limit_by_type_name() -> None:
    assert classify_llm_error(FakeRateLimitError("")) == LLMErrorCategory.RATE_LIMIT
