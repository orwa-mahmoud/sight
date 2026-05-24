"""Question repository port."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from src.domain.questions.entities import Question
from src.domain.questions.value_objects import QuestionStatus


class QuestionRepository(Protocol):
    async def save(self, question: Question) -> None: ...

    async def get_by_id(self, question_id: UUID) -> Question | None: ...

    async def list_for_tenant(
        self,
        tenant_id: UUID,
        *,
        status: QuestionStatus | None = None,
        limit: int = 100,
    ) -> list[Question]: ...

    async def count_for_tenant(
        self,
        tenant_id: UUID,
        *,
        status: QuestionStatus | None = None,
    ) -> int: ...
