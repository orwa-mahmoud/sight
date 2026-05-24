"""Question queries."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from src.domain.questions.value_objects import QuestionStatus


@dataclass(frozen=True, kw_only=True)
class ListQuestions:
    tenant_id: UUID
    status: QuestionStatus | None = None
    limit: int = 100


@dataclass(frozen=True, kw_only=True)
class GetQuestion:
    tenant_id: UUID
    question_id: UUID
