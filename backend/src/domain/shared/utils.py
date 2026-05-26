"""Shared domain utilities."""

from __future__ import annotations

import re

_SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def is_valid_slug(value: str) -> bool:
    return bool(_SLUG_RE.match(value)) and len(value) >= 2
