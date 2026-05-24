"""Questions domain — escalated questions the AI couldn't answer.

Lifecycle: SUBMITTED -> RESOLVED (owner replied) or CLOSED (without reply).
A question is created when the AI agent's confidence threshold isn't met
or when the asker explicitly requests human follow-up. The owner answers
via the dashboard or their preferred channel, and the AI relays the reply
back to the asker through the original channel.
"""

from src.domain.questions.entities import Question
from src.domain.questions.events import QuestionResolved, QuestionSubmitted
from src.domain.questions.repositories import QuestionRepository
from src.domain.questions.value_objects import QuestionStatus

__all__ = [
    "Question",
    "QuestionRepository",
    "QuestionResolved",
    "QuestionStatus",
    "QuestionSubmitted",
]
