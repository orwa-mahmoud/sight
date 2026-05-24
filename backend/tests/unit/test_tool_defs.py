"""Unit tests for tool definitions."""

from __future__ import annotations

from src.ai.tools.escalate_question import ESCALATE_QUESTION_DEF
from src.ai.tools.search_documents import SEARCH_DOCUMENTS_DEF


def test_search_documents_def_shape() -> None:
    assert SEARCH_DOCUMENTS_DEF.name == "search_documents"
    assert "query" in SEARCH_DOCUMENTS_DEF.parameters_schema["properties"]
    assert "query" in SEARCH_DOCUMENTS_DEF.parameters_schema["required"]


def test_escalate_question_def_shape() -> None:
    assert ESCALATE_QUESTION_DEF.name == "escalate_question"
    assert "question_text" in ESCALATE_QUESTION_DEF.parameters_schema["properties"]
    assert "question_text" in ESCALATE_QUESTION_DEF.parameters_schema["required"]
