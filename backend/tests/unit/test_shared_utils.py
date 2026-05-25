"""Unit tests for shared domain utilities."""

from __future__ import annotations

from src.domain.shared.utils import is_valid_slug, normalize_email, truncate


def test_valid_slug():
    assert is_valid_slug("my-slug")
    assert is_valid_slug("ab")
    assert is_valid_slug("a1-b2-c3")


def test_invalid_slug():
    assert not is_valid_slug("a")
    assert not is_valid_slug("My Slug")
    assert not is_valid_slug("UPPER")
    assert not is_valid_slug("")


def test_normalize_email():
    assert normalize_email("  Test@Example.COM  ") == "test@example.com"


def test_truncate():
    assert truncate("abc", 5) == "abc"
    assert truncate("abcdef", 3) == "abc"
    assert len(truncate("x" * 2000, 1024)) == 1024
