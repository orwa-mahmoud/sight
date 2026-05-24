"""Unit tests for checkpoint summarization helpers."""

from __future__ import annotations

from src.ai.context.checkpoint import _parse_summary


def test_parse_valid_json_summary() -> None:
    raw = '{"summary": "User asked about hours.", "current_state": {"name": null}}'
    display, tool_data = _parse_summary(raw)
    assert display == "User asked about hours."
    assert tool_data is not None
    assert "checkpoint" in tool_data


def test_parse_json_with_markdown_fences() -> None:
    raw = '```json\n{"summary": "Wrapped in fences."}\n```'
    display, tool_data = _parse_summary(raw)
    assert display == "Wrapped in fences."
    assert tool_data is not None


def test_parse_invalid_json_returns_raw() -> None:
    raw = "This is not JSON at all."
    display, tool_data = _parse_summary(raw)
    assert display == raw
    assert tool_data is None


def test_parse_empty_string() -> None:
    display, tool_data = _parse_summary("")
    assert display == ""
    assert tool_data is None
