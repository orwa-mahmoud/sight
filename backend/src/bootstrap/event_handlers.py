"""Event handlers — wired at app startup via register_event_handlers().

Each handler subscribes to a specific domain event type and executes
a side effect. Handlers are fire-and-forget with error isolation
(failures are logged, not propagated).
"""

from __future__ import annotations

import structlog

from src.bootstrap.events import subscribe
from src.domain.llm_usage.events import TokenUsageRecorded
from src.domain.questions.events import QuestionResolved, QuestionSubmitted
from src.domain.shared.events import DomainEvent
from src.domain.tenants.events import TenantCreated

logger = structlog.get_logger()


def _on_question_submitted(event: DomainEvent) -> None:
    assert isinstance(event, QuestionSubmitted)
    logger.info(
        "event.question_submitted",
        question_id=str(event.question_id),
        tenant_id=str(event.tenant_id),
        channel=event.channel,
    )


def _on_question_resolved(event: DomainEvent) -> None:
    assert isinstance(event, QuestionResolved)
    logger.info(
        "event.question_resolved",
        question_id=str(event.question_id),
        tenant_id=str(event.tenant_id),
        replied_by=str(event.replied_by_user_id),
    )


def _on_tenant_created(event: DomainEvent) -> None:
    assert isinstance(event, TenantCreated)
    logger.info(
        "event.tenant_created",
        tenant_id=str(event.tenant_id),
        name=event.name,
        slug=event.slug,
    )


def _on_token_usage_recorded(event: DomainEvent) -> None:
    assert isinstance(event, TokenUsageRecorded)
    from src.infrastructure.metrics import LLM_CALLS_TOTAL, LLM_TOKENS_TOTAL  # noqa: PLC0415

    LLM_CALLS_TOTAL.labels(
        provider=event.provider,
        model=event.model,
        status="success",
    ).inc()
    LLM_TOKENS_TOTAL.labels(
        provider=event.provider,
        model=event.model,
        direction="input",
    ).inc(event.input_tokens)
    LLM_TOKENS_TOTAL.labels(
        provider=event.provider,
        model=event.model,
        direction="output",
    ).inc(event.output_tokens)


def register_event_handlers() -> None:
    """Call once at app startup to subscribe all handlers."""
    subscribe(QuestionSubmitted, _on_question_submitted)
    subscribe(QuestionResolved, _on_question_resolved)
    subscribe(TenantCreated, _on_tenant_created)
    subscribe(TokenUsageRecorded, _on_token_usage_recorded)
    logger.info("event_handlers.registered", count=4)
