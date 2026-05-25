"""Unit tests for the tool registry."""

from __future__ import annotations

from src.ai.tools.types import ALL_TOOLS, ASKER_TOOLS, OWNER_TOOLS


def test_all_tools_has_four() -> None:
    assert len(ALL_TOOLS) == 4
    assert "search_documents" in ALL_TOOLS
    assert "escalate_question" in ALL_TOOLS
    assert "save_key_fact" in ALL_TOOLS
    assert "remove_key_fact" in ALL_TOOLS


def test_asker_tools() -> None:
    assert len(ASKER_TOOLS) == 4


def test_owner_tools() -> None:
    assert len(OWNER_TOOLS) == 1
    assert OWNER_TOOLS[0].name == "search_documents"
