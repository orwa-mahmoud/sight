"""Unit tests for event handlers."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

from src.bootstrap.event_handlers import (
    _on_question_resolved,
    _on_question_submitted,
    _on_tenant_created,
    _on_token_usage_recorded,
)
from src.domain.llm_usage.events import TokenUsageRecorded
from src.domain.questions.events import QuestionResolved, QuestionSubmitted
from src.domain.tenants.events import TenantCreated


def test_on_question_submitted() -> None:
    event = QuestionSubmitted(
        question_id=uuid4(),
        tenant_id=uuid4(),
        channel="whatsapp",
        asker_contact="+971500000000",
    )
    _on_question_submitted(event)  # no crash


def test_on_question_resolved() -> None:
    event = QuestionResolved(
        question_id=uuid4(),
        tenant_id=uuid4(),
        replied_by_user_id=uuid4(),
    )
    _on_question_resolved(event)


def test_on_tenant_created() -> None:
    event = TenantCreated(tenant_id=uuid4(), name="Test", slug="test")
    _on_tenant_created(event)


def test_on_token_usage_recorded() -> None:
    event = TokenUsageRecorded(
        usage_id=uuid4(),
        tenant_id=uuid4(),
        request_id=None,
        provider="openai",
        model="gpt-4o-mini",
        input_tokens=100,
        output_tokens=50,
        total_cost=Decimal("0.01"),
    )
    _on_token_usage_recorded(event)
