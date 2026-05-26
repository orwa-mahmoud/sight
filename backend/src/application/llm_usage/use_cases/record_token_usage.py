"""RecordTokenUsage — append a usage row for one LLM call."""

from __future__ import annotations

from src.application.llm_usage.commands import RecordTokenUsage
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.llm_usage.entities import TokenUsage


class RecordTokenUsageUseCase:
    def __init__(self, *, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, cmd: RecordTokenUsage) -> None:
        usage = TokenUsage.record(
            tenant_id=cmd.tenant_id,
            provider=cmd.provider,
            model=cmd.model,
            input_tokens=cmd.input_tokens,
            output_tokens=cmd.output_tokens,
            cache_read_tokens=cmd.cache_read_tokens,
            thread_id=cmd.thread_id,
            request_id=cmd.request_id,
            source=cmd.source,
            channel=cmd.channel,
        )
        await self._uow.token_usages.save(usage)
        self._uow.track(usage)
