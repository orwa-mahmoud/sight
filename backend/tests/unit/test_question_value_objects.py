"""Unit tests for question value objects."""

from __future__ import annotations

from src.domain.questions.value_objects import QuestionStatus


def test_question_status_values() -> None:
    assert QuestionStatus.SUBMITTED == "submitted"
    assert QuestionStatus.RESOLVED == "resolved"
    assert QuestionStatus.CLOSED == "closed"
