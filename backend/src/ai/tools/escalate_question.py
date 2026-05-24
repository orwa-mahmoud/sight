"""escalate_question tool — forwards the asker's question to the owner.

Called by the agent when it doesn't have enough information to answer
confidently, or when the asker explicitly asks to talk to a human.
Creates a Question row in SUBMITTED status; the owner sees it in their
inbox and can reply.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from src.ai.types import ToolDef
from src.application.questions.commands import SubmitQuestion
from src.application.questions.use_cases.submit_question import SubmitQuestionUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel

ESCALATE_QUESTION_DEF = ToolDef(
    name="escalate_question",
    description=(
        "Forward this question to the owner for a human answer. Use this when: "
        "(1) the search_documents tool returned no relevant results, "
        "(2) you're not confident in the answer, or "
        "(3) the asker explicitly asks to speak with someone. "
        "Include your best-effort answer attempt so the owner has context."
    ),
    parameters_schema={
        "type": "object",
        "properties": {
            "question_text": {
                "type": "string",
                "description": "The asker's original question, verbatim or lightly cleaned.",
            },
            "ai_answer_attempt": {
                "type": "string",
                "description": "Your best-effort answer (even if incomplete) so the owner sees what you tried.",
            },
        },
        "required": ["question_text"],
    },
)


async def run_escalate_question(
    *,
    arguments: dict[str, Any],
    tenant_id: UUID,
    channel: ConversationChannel,
    conversation_id: UUID | None,
    asker_name: str | None,
    asker_contact: str | None,
    uow: UnitOfWork,
) -> dict[str, str]:
    question_text = arguments.get("question_text", "")
    ai_attempt = arguments.get("ai_answer_attempt")

    dto = await SubmitQuestionUseCase(uow=uow).execute(
        SubmitQuestion(
            tenant_id=tenant_id,
            channel=channel,
            question_text=question_text,
            conversation_id=conversation_id,
            asker_name=asker_name,
            asker_contact=asker_contact,
            ai_answer_attempt=ai_attempt,
        )
    )
    return {"status": "escalated", "question_id": str(dto.id)}
