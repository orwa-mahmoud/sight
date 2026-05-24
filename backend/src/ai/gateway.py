"""Chat gateway — the single public entry point for all inbound messages.

Every channel (WhatsApp webhook, Telegram webhook, API) calls
`chat_with_agent()`. The gateway:

1. Resolves or creates the conversation thread
2. Saves the inbound message
3. Loads history from the DB (source of truth)
4. Builds the system prompt + tool definitions
5. Runs the agent loop (LLM → tool → LLM cycle)
6. Saves the assistant reply + tool exchanges
7. Records token usage
8. Returns the response text for the channel to send back
"""

from __future__ import annotations

import uuid

import structlog

from src.ai.agents.agent import run_agent_loop
from src.ai.context.history import load_history
from src.ai.context.prompts import build_asker_system_prompt
from src.ai.tools.escalate_question import ESCALATE_QUESTION_DEF
from src.ai.tools.search_documents import SEARCH_DOCUMENTS_DEF
from src.ai.types import ChatInput, ChatResult
from src.application.conversations.commands import SaveThreadMessage
from src.application.conversations.use_cases.save_thread_message import SaveThreadMessageUseCase
from src.application.llm_usage.commands import RecordTokenUsage
from src.application.llm_usage.use_cases.record_token_usage import RecordTokenUsageUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationRole
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole
from src.infrastructure.llm.client import LangChainLLMClient
from src.infrastructure.rag.embedder import OpenAIEmbedder
from src.infrastructure.rag.retriever import HybridRetriever

logger = structlog.get_logger()

_TOOLS = [SEARCH_DOCUMENTS_DEF, ESCALATE_QUESTION_DEF]


async def chat_with_agent(inp: ChatInput, *, uow: UnitOfWork) -> ChatResult:
    """Process one inbound message end-to-end. Returns the AI's reply."""
    request_id = uuid.uuid4().hex

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

    # ── 3. Build prompt ───────────────────────────────────────────
    system_msg = build_asker_system_prompt()
    messages: list[LLMMessage] = [system_msg, *history]
    if not any(m.role == LLMMessageRole.USER for m in messages):
        messages.append(LLMMessage(role=LLMMessageRole.USER, content=inp.message))

    # ── 4. Build LLM client + retriever ───────────────────────────
    llm = LangChainLLMClient(provider="openai", model="gpt-4o-mini")
    embedder = OpenAIEmbedder()
    retriever = HybridRetriever(session=uow._session, embedder=embedder)

    # ── 5. Run agent loop ─────────────────────────────────────────
    logger.info("gateway.agent_start", thread_id=thread_id, request_id=request_id)
    result = await run_agent_loop(
        messages=messages,
        tools=_TOOLS,
        llm=llm,
        tenant_id=inp.tenant_id,
        channel=inp.channel,
        conversation_id=conversation_id,
        asker_name=inp.sender_name,
        asker_contact=inp.sender_identifier,
        retriever=retriever,
        uow=uow,
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
                provider="openai",
                model="gpt-4o-mini",
                input_tokens=result.input_tokens,
                output_tokens=result.output_tokens,
                cache_read_tokens=result.cache_read_tokens,
                thread_id=thread_id,
                request_id=request_id,
                source="asker",
                channel=inp.channel.value,
            )
        )

    escalated = any(tc.tool_name == "escalate_question" for tc in result.tool_calls)

    return ChatResult(
        response=result.text,
        thread_id=thread_id,
        escalated=escalated,
        request_id=request_id,
    )
