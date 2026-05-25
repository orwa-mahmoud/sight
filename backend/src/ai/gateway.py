"""Chat gateway — the single public entry point for all inbound messages.

Every channel (WhatsApp webhook, Telegram webhook, API) calls
`chat_with_agent()`. The gateway:

1. Loads the tenant's LLM config from the DB (per-tenant, not .env)
2. Resolves or creates the conversation thread
3. Saves the inbound message
4. Loads history from the DB (source of truth)
5. Builds the system prompt + tool definitions
6. Runs the agent loop (LLM → tool → LLM cycle)
7. Saves the assistant reply + tool exchanges
8. Records token usage
9. Returns the response text for the channel to send back
"""

from __future__ import annotations

import uuid

import structlog

from src.ai.context.history import load_history
from src.ai.context.prompts import build_asker_system_prompt
from src.ai.tools.escalate_question import ESCALATE_QUESTION_DEF
from src.ai.tools.save_key_fact import SAVE_KEY_FACT_DEF
from src.ai.tools.search_documents import SEARCH_DOCUMENTS_DEF
from src.ai.types import ChatInput, ChatResult
from src.application.conversations.commands import SaveThreadMessage
from src.application.conversations.use_cases.save_thread_message import SaveThreadMessageUseCase
from src.application.llm_usage.commands import RecordTokenUsage
from src.application.llm_usage.use_cases.record_token_usage import RecordTokenUsageUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationRole
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole
from src.domain.shared.exceptions import InvalidOperationError
from src.infrastructure.llm.client import LangChainLLMClient
from src.infrastructure.rag.embedder import OpenAIEmbedder
from src.infrastructure.rag.retriever import HybridRetriever

logger = structlog.get_logger()

_TOOLS = [SEARCH_DOCUMENTS_DEF, ESCALATE_QUESTION_DEF, SAVE_KEY_FACT_DEF]


async def chat_with_agent(inp: ChatInput, *, uow: UnitOfWork) -> ChatResult:
    """Process one inbound message end-to-end. Returns the AI's reply."""
    request_id = uuid.uuid4().hex

    # ── 0. Load tenant config (per-tenant LLM + embedding creds) ──
    tenant_config = await uow.tenant_configs.get_by_tenant_id(inp.tenant_id)
    if tenant_config is None:
        raise InvalidOperationError("Tenant configuration not found. Please set up your LLM credentials in Settings.")
    if not tenant_config.llm_api_key:
        raise InvalidOperationError(
            "LLM API key not configured. Go to Settings → LLM Configuration and add your API key."
        )

    thread_id = inp.thread_id or f"{inp.channel.value}:{inp.sender_identifier}:{inp.tenant_id}"

    # ── 1. Save inbound message ───────────────────────────────────
    save_uc = SaveThreadMessageUseCase(uow=uow)
    save_result = await save_uc.execute(
        SaveThreadMessage(
            tenant_id=inp.tenant_id,
            thread_id=thread_id,
            channel=inp.channel,
            role=ConversationRole.USER,
            content=inp.message,
            request_id=request_id,
        )
    )
    conversation_id = save_result.conversation_id
    await uow.flush()

    # ── 2. Load history ───────────────────────────────────────────
    history = await load_history(thread_id=thread_id, uow=uow)

    # ── 3. Build prompt (with key facts if available) ───────────
    from src.ai.context.memory import load_key_facts_context  # noqa: PLC0415

    system_msg = build_asker_system_prompt()
    facts_context = await load_key_facts_context(
        tenant_id=inp.tenant_id,
        participant_identifier=inp.sender_identifier,
        uow=uow,
    )
    messages: list[LLMMessage] = [system_msg]
    if facts_context:
        messages.append(LLMMessage(role=LLMMessageRole.SYSTEM, content=facts_context))
    messages.extend(history)
    if not any(m.role == LLMMessageRole.USER for m in messages):
        messages.append(LLMMessage(role=LLMMessageRole.USER, content=inp.message))

    # ── 4. Build LLM client + retriever from tenant config ────────
    llm = LangChainLLMClient(
        provider=tenant_config.llm_provider.value,
        model=tenant_config.llm_model,
        api_key=tenant_config.llm_api_key,
    )
    embedding_key = tenant_config.embedding_api_key or tenant_config.llm_api_key
    embedder = OpenAIEmbedder(
        api_key=embedding_key,
        model=tenant_config.embedding_model,
        dimensions=tenant_config.embedding_dimensions,
    )
    retriever = HybridRetriever(session=uow._session, embedder=embedder)

    # ── 5. Run LangGraph agent ────────────────────────────────────
    from src.infrastructure.ai.graph import build_agent_graph, run_graph  # noqa: PLC0415

    logger.info(
        "gateway.agent_start",
        thread_id=thread_id,
        request_id=request_id,
        provider=tenant_config.llm_provider.value,
        model=tenant_config.llm_model,
    )
    graph = build_agent_graph(
        llm=llm,
        tools=_TOOLS,
        retriever=retriever,
        uow=uow,
        max_tokens=tenant_config.llm_max_tokens,
    )
    result = await run_graph(
        graph,
        messages=messages,
        tenant_id=inp.tenant_id,
        channel=inp.channel,
        conversation_id=conversation_id,
        asker_name=inp.sender_name,
        asker_contact=inp.sender_identifier,
    )
    logger.info(
        "gateway.agent_done",
        thread_id=thread_id,
        request_id=request_id,
        tools_used=len(result.tool_calls),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )

    # ── 6. Save tool exchanges + assistant reply ──────────────────
    for tc in result.tool_calls:
        await save_uc.execute(
            SaveThreadMessage(
                tenant_id=inp.tenant_id,
                thread_id=thread_id,
                channel=inp.channel,
                role=ConversationRole.ASSISTANT,
                content="",
                hidden=True,
                tool_call_id=tc.tool_name,
                tool_args=tc.arguments,
                request_id=request_id,
            )
        )
        await save_uc.execute(
            SaveThreadMessage(
                tenant_id=inp.tenant_id,
                thread_id=thread_id,
                channel=inp.channel,
                role=ConversationRole.TOOL,
                content=tc.summary,
                hidden=True,
                tool_result=tc.result if isinstance(tc.result, dict) else {"data": tc.result},
                tool_call_id=tc.tool_name,
                request_id=request_id,
            )
        )

    await save_uc.execute(
        SaveThreadMessage(
            tenant_id=inp.tenant_id,
            thread_id=thread_id,
            channel=inp.channel,
            role=ConversationRole.ASSISTANT,
            content=result.text,
            request_id=request_id,
        )
    )

    # ── 7. Record token usage ─────────────────────────────────────
    if result.input_tokens > 0 or result.output_tokens > 0:
        await RecordTokenUsageUseCase(uow=uow).execute(
            RecordTokenUsage(
                tenant_id=inp.tenant_id,
                provider=tenant_config.llm_provider.value,
                model=tenant_config.llm_model,
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cache_read_tokens=result.cache_read_tokens,
                thread_id=thread_id,
                request_id=request_id,
                source="asker",
                channel=inp.channel.value,
            )
        )

    # ── 8. Maybe create checkpoint (structured summary) ─────────
    from src.ai.context.checkpoint import maybe_create_checkpoint  # noqa: PLC0415

    await maybe_create_checkpoint(
        thread_id=thread_id,
        tenant_id=inp.tenant_id,
        channel=inp.channel,
        llm=llm,
        uow=uow,
        request_id=request_id,
    )

    escalated = any(tc.tool_name == "escalate_question" for tc in result.tool_calls)

    return ChatResult(
        response=result.text,
        thread_id=thread_id,
        escalated=escalated,
        request_id=request_id,
    )
