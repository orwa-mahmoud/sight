"""Full gateway tests with mocked LLM + graph — covers the entire chat flow."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.ai.gateway import chat_with_agent
from src.ai.types import AgentLoopResult, ChatInput
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.tenant_config.entities import TenantConfig
from src.domain.tenant_config.value_objects import LLMProvider
from src.infrastructure.persistence.postgres.database import async_session_factory


def _make_config(tenant_id: object) -> TenantConfig:
    c = TenantConfig.create_default(tenant_id=tenant_id)  # type: ignore[arg-type]
    c.llm_api_key = "sk-test-key-1234567890"
    return c


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_full_flow_with_mocked_graph(client: None) -> None:
    """End-to-end gateway: saves inbound msg, calls graph, saves reply, records tokens."""
    from src.domain.tenants.entities import Tenant

    # Seed tenant + config
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="GW Test", slug=f"gw-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.flush()
        config = _make_config(tenant.id)
        config._is_new = True
        await uow.tenant_configs.save(config)
        await uow.commit()

    mock_result = AgentLoopResult(
        text="Hello! I'm your front desk assistant.",
        tool_calls=[],
        input_tokens=50,
        output_tokens=20,
    )

    with (
        patch("src.ai.gateway.build_agent_graph") as mock_build,
        patch("src.ai.gateway.run_graph", new_callable=AsyncMock, return_value=mock_result),
        patch("src.ai.gateway.maybe_create_checkpoint", new_callable=AsyncMock),
    ):
        mock_build.return_value = MagicMock()

        async with async_session_factory() as session:
            uow = UnitOfWork(session)
            result = await chat_with_agent(
                ChatInput(
                    message="Hi there!",
                    tenant_id=tenant.id,
                    channel=ConversationChannel.WEB,
                    sender_identifier="test@user.com",
                    sender_name="Test User",
                ),
                uow=uow,
            )
            await uow.commit()

    assert result.response == "Hello! I'm your front desk assistant."
    assert result.thread_id
    assert not result.escalated
    assert result.request_id

    # Verify messages were saved
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        conv = await uow.conversations.get_by_thread_id(result.thread_id)
        assert conv is not None
        messages = await uow.messages.list_for_conversation(conv.id, include_hidden=True)
        assert len(messages) >= 2  # user + assistant

    # Verify token usage was recorded
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        stats = await uow.token_usages.aggregate_for_tenant(tenant.id)
        assert stats.total_calls >= 1
        assert stats.total_input_tokens >= 50


@pytest.mark.integration
@pytest.mark.asyncio
async def test_gateway_with_tool_calls(client: None) -> None:
    """Gateway with escalation tool call — verifies tool exchanges are saved."""
    from src.ai.types import ToolCallResult
    from src.domain.tenants.entities import Tenant

    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        tenant = Tenant.create(name="GW Tool", slug=f"gwt-{uuid4().hex[:8]}")
        await uow.tenants.save(tenant)
        await uow.flush()
        config = _make_config(tenant.id)
        config._is_new = True
        await uow.tenant_configs.save(config)
        await uow.commit()

    mock_result = AgentLoopResult(
        text="Let me check with the team and get back to you.",
        tool_calls=[
            ToolCallResult(
                tool_name="escalate_question",
                arguments={"question_text": "What's your return policy?"},
                result={"status": "escalated", "question_id": str(uuid4())},
                summary='{"status": "escalated"}',
            )
        ],
        input_tokens=80,
        output_tokens=30,
    )

    with (
        patch("src.ai.gateway.build_agent_graph") as mock_build,
        patch("src.ai.gateway.run_graph", new_callable=AsyncMock, return_value=mock_result),
        patch("src.ai.gateway.maybe_create_checkpoint", new_callable=AsyncMock),
    ):
        mock_build.return_value = MagicMock()

        async with async_session_factory() as session:
            uow = UnitOfWork(session)
            result = await chat_with_agent(
                ChatInput(
                    message="What's your return policy?",
                    tenant_id=tenant.id,
                    channel=ConversationChannel.WHATSAPP,
                    sender_identifier="+971500000000",
                ),
                uow=uow,
            )
            await uow.commit()

    assert result.escalated is True

    # Verify tool exchange messages saved (hidden)
    async with async_session_factory() as session:
        uow = UnitOfWork(session)
        conv = await uow.conversations.get_by_thread_id(result.thread_id)
        assert conv is not None
        all_msgs = await uow.messages.list_for_conversation(conv.id, include_hidden=True)
        hidden = [m for m in all_msgs if m.hidden]
        assert len(hidden) >= 2  # tool_call + tool_result


@pytest.mark.asyncio
async def test_gateway_no_token_usage_when_zero_tokens() -> None:
    """If the agent uses 0 tokens, no usage row is recorded."""
    mock_config = MagicMock()
    mock_config.llm_api_key = "sk-test"
    mock_config.llm_provider = LLMProvider.OPENAI
    mock_config.llm_model = "gpt-4o-mini"
    mock_config.llm_max_tokens = 1024
    mock_config.embedding_api_key = ""
    mock_config.embedding_model = "text-embedding-3-large"

    mock_result = AgentLoopResult(text="cached", input_tokens=0, output_tokens=0)

    uow = MagicMock()
    uow.tenant_configs = MagicMock()
    uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=mock_config)
    uow.flush = AsyncMock()

    mock_save_uc = MagicMock()
    mock_save_uc.execute = AsyncMock(return_value=MagicMock(conversation_id=uuid4()))

    with (
        patch("src.ai.gateway.SaveThreadMessageUseCase", return_value=mock_save_uc),
        patch("src.ai.gateway.load_history", new_callable=AsyncMock, return_value=[]),
        patch("src.ai.gateway.load_key_facts_context", new_callable=AsyncMock, return_value=""),
        patch("src.ai.gateway.build_agent_graph") as mock_build,
        patch("src.ai.gateway.run_graph", new_callable=AsyncMock, return_value=mock_result),
        patch("src.ai.gateway.maybe_create_checkpoint", new_callable=AsyncMock),
        patch("src.ai.gateway.RecordTokenUsageUseCase") as mock_record,
    ):
        mock_build.return_value = MagicMock()

        await chat_with_agent(
            ChatInput(
                message="hi",
                tenant_id=uuid4(),
                channel=ConversationChannel.API,
                sender_identifier="x@y.com",
            ),
            uow=uow,
        )

    # RecordTokenUsageUseCase should NOT have been instantiated
    mock_record.assert_not_called()


@pytest.mark.asyncio
async def test_gateway_applies_temperature_and_bot_personality() -> None:
    """The tenant's temperature + bot personality must reach the graph build and prompt."""
    mock_config = MagicMock()
    mock_config.llm_api_key = "sk-test"
    mock_config.llm_provider = LLMProvider.OPENAI
    mock_config.llm_model = "gpt-4o-mini"
    mock_config.llm_max_tokens = 1024
    mock_config.llm_temperature = 0.7
    mock_config.embedding_api_key = ""
    mock_config.embedding_model = "text-embedding-3-large"
    mock_config.bot_name = "Aria"
    mock_config.bot_language = "Arabic"
    mock_config.bot_welcome_message = ""

    mock_result = AgentLoopResult(text="hi", input_tokens=1, output_tokens=1)

    uow = MagicMock()
    uow.tenant_configs = MagicMock()
    uow.tenant_configs.get_by_tenant_id = AsyncMock(return_value=mock_config)
    uow.flush = AsyncMock()

    mock_save_uc = MagicMock()
    mock_save_uc.execute = AsyncMock(return_value=MagicMock(conversation_id=uuid4()))

    mock_record_uc = MagicMock()
    mock_record_uc.execute = AsyncMock()

    with (
        patch("src.ai.gateway.SaveThreadMessageUseCase", return_value=mock_save_uc),
        patch("src.ai.gateway.load_history", new_callable=AsyncMock, return_value=[]),
        patch("src.ai.gateway.load_key_facts_context", new_callable=AsyncMock, return_value=""),
        patch("src.ai.gateway.build_agent_graph") as mock_build,
        patch("src.ai.gateway.run_graph", new_callable=AsyncMock, return_value=mock_result) as mock_run,
        patch("src.ai.gateway.maybe_create_checkpoint", new_callable=AsyncMock),
        patch("src.ai.gateway.RecordTokenUsageUseCase", return_value=mock_record_uc),
    ):
        mock_build.return_value = MagicMock()
        await chat_with_agent(
            ChatInput(
                message="hi",
                tenant_id=uuid4(),
                channel=ConversationChannel.API,
                sender_identifier="x@y.com",
            ),
            uow=uow,
        )

    # Bug #5: temperature (and max_tokens) threaded into the graph build.
    assert mock_build.call_args.kwargs["temperature"] == pytest.approx(0.7)
    assert mock_build.call_args.kwargs["max_tokens"] == 1024
    # Bug #6: bot personality reached the system prompt.
    system_text = mock_run.call_args.kwargs["messages"][0].content
    assert "Aria" in system_text
    assert "Arabic" in system_text
