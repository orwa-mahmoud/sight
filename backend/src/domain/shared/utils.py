"""Shared domain utilities."""

from __future__ import annotations

import re

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_slug(value: str) -> bool:
    return bool(_SLUG_RE.match(value)) and len(value) >= 2


def normalize_email(email: str) -> str:
    return email.strip().lower()


def truncate(text: str, max_length: int = 1024) -> str:
    return text[:max_length] if len(text) > max_length else text
