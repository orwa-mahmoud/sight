"""Unit tests for the admin CLI argument parsing + routing."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from src.cli.__main__ import build_parser, main


def test_parser_requires_a_group() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_parser_parses_grant() -> None:
    args = build_parser().parse_args(["admin", "grant", "a@b.com"])
    assert args.group == "admin"
    assert args.action == "grant"
    assert args.email == "a@b.com"


def test_main_grant_routes_to_set_admin() -> None:
    with patch("src.cli.__main__._set_admin", new_callable=AsyncMock, return_value=0) as mock:
        assert main(["admin", "grant", "a@b.com"]) == 0
    mock.assert_awaited_once_with("a@b.com", granted=True)


def test_main_revoke_routes_to_set_admin() -> None:
    with patch("src.cli.__main__._set_admin", new_callable=AsyncMock, return_value=0) as mock:
        assert main(["admin", "revoke", "a@b.com"]) == 0
    mock.assert_awaited_once_with("a@b.com", granted=False)
