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
from collections.abc import Iterator
from typing import Any

import redis.asyncio as aioredis
import structlog

from src.ai.concurrency import ThreadLock
from src.ai.context.checkpoint import maybe_create_checkpoint
from src.ai.context.history import load_history
from src.ai.context.memory import load_key_facts_context
from src.ai.context.prompts import build_asker_system_prompt
from src.ai.tools.escalate_question import ESCALATE_QUESTION_DEF
from src.ai.tools.remove_key_fact import REMOVE_KEY_FACT_DEF
from src.ai.tools.save_key_fact import SAVE_KEY_FACT_DEF
from src.ai.tools.search_documents import SEARCH_DOCUMENTS_DEF
from src.ai.types import AgentLoopResult, ChatInput, ChatResult, ChatSource
from src.ai.utils.sender import resolve_sender
from src.application.conversations.commands import SaveThreadMessage
from src.application.conversations.use_cases.save_thread_message import SaveThreadMessageUseCase
from src.application.llm_usage.commands import RecordTokenUsage
from src.application.llm_usage.use_cases.record_token_usage import RecordTokenUsageUseCase
from src.application.shared.unit_of_work import UnitOfWork
from src.config.settings import get_settings
from src.domain.conversations.value_objects import ConversationRole
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole
from src.domain.shared.exceptions import InvalidOperationError
from src.infrastructure.ai.graph import build_agent_graph, run_graph
from src.infrastructure.llm.tenant_factory import TenantLLMClientFactory
from src.infrastructure.metrics import AGENT_INVOCATIONS_TOTAL, AGENT_TOOL_CALLS_TOTAL
from src.infrastructure.rag.embedder import OpenAIEmbedder
from src.infrastructure.rag.retriever import HybridRetriever

logger = structlog.get_logger()

_TOOLS = [SEARCH_DOCUMENTS_DEF, ESCALATE_QUESTION_DEF, SAVE_KEY_FACT_DEF, REMOVE_KEY_FACT_DEF]


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

    # ── 0b. Resolve sender to a Contact ──────────────────────────
    contact_id = inp.contact_id
    if contact_id is None:
        contact_id = await resolve_sender(
            tenant_id=inp.tenant_id,
            channel=inp.channel,
            sender_identifier=inp.sender_identifier,
            sender_name=inp.sender_name,
            uow=uow,
        )
        await uow.flush()

    # ── 1. Save inbound message ───────────────────────────────────
    save_uc = SaveThreadMessageUseCase(uow=uow)
    save_result = await save_uc.execute(
        SaveThreadMessage(
            tenant_id=inp.tenant_id,
            thread_id=thread_id,
            channel=inp.channel,
            role=ConversationRole.USER,
            content=inp.message,
            participant_id=contact_id,
            request_id=request_id,
        )
    )
    conversation_id = save_result.conversation_id
    await uow.flush()

    # ── 2. Load history ───────────────────────────────────────────
    history = await load_history(thread_id=thread_id, uow=uow)

    # ── 3. Build prompt (with key facts if available) ───────────
    system_msg = build_asker_system_prompt(
        bot_name=tenant_config.bot_name,
        bot_language=tenant_config.bot_language,
        welcome_message=tenant_config.bot_welcome_message,
    )
    facts_context = ""
    if contact_id is not None:
        facts_context = await load_key_facts_context(
            tenant_id=inp.tenant_id,
            contact_id=contact_id,
            uow=uow,
        )
    messages: list[LLMMessage] = [system_msg]
    if facts_context:
        messages.append(LLMMessage(role=LLMMessageRole.SYSTEM, content=facts_context))
    messages.extend(history)
    if not any(m.role == LLMMessageRole.USER for m in messages):
        messages.append(LLMMessage(role=LLMMessageRole.USER, content=inp.message))

    # ── 4. Build LLM client + retriever from tenant config ────────

    llm = _get_llm_factory().get_or_build(inp.tenant_id, tenant_config)
    embedding_key = tenant_config.embedding_api_key or tenant_config.llm_api_key
    embedder = OpenAIEmbedder(
        api_key=embedding_key,
        model=tenant_config.embedding_model,
        dimensions=1536,
    )
    retriever = HybridRetriever(session=uow._session, embedder=embedder)

    # ── 5. Acquire thread lock + run LangGraph agent ───────────────
    lock = await _acquire_thread_lock(thread_id)

    try:
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
            temperature=tenant_config.llm_temperature,
        )
        result = await run_graph(
            graph,
            messages=messages,
            tenant_id=inp.tenant_id,
            channel=inp.channel,
            conversation_id=conversation_id,
            contact_id=contact_id,
        )
        _record_agent_metrics(inp.channel.value, result)
        logger.info(
            "gateway.agent_done",
            thread_id=thread_id,
            request_id=request_id,
            tools_used=len(result.tool_calls),
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )
    finally:
        if lock:
            await lock.release()

    # ── 6. Save tool exchanges + assistant reply ──────────────────
    await _save_agent_messages(save_uc, inp, thread_id, result, request_id)

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
        sources=_extract_sources(result),
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
    )


def _iter_search_rows(result: AgentLoopResult) -> Iterator[dict[str, Any]]:
    """Yield each result row from every search_documents tool call."""
    for tc in result.tool_calls:
        if tc.tool_name == "search_documents" and isinstance(tc.result, list):
            yield from (row for row in tc.result if isinstance(row, dict))


def _extract_sources(result: AgentLoopResult, *, limit: int = 5, snippet_len: int = 240) -> list[ChatSource]:
    """Collect the best retrieved chunk per document from search_documents calls.

    Lets the dashboard chat show which uploaded documents grounded the answer.
    """
    best: dict[str, ChatSource] = {}
    for row in _iter_search_rows(result):
        document_id = str(row.get("document_id") or "")
        if not document_id:
            continue
        score = float(row.get("score") or 0.0)
        existing = best.get(document_id)
        if existing is None or score > existing.score:
            best[document_id] = ChatSource(
                document_id=document_id,
                snippet=str(row.get("content") or "")[:snippet_len],
                score=score,
            )
    return sorted(best.values(), key=lambda s: s.score, reverse=True)[:limit]


async def _save_agent_messages(
    save_uc: SaveThreadMessageUseCase,
    inp: ChatInput,
    thread_id: str,
    result: AgentLoopResult,
    request_id: str,
) -> None:
    """Persist tool exchanges and the final assistant reply."""
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


def _record_agent_metrics(channel: str, result: AgentLoopResult) -> None:
    AGENT_INVOCATIONS_TOTAL.labels(channel=channel).inc()
    for tc in result.tool_calls:
        AGENT_TOOL_CALLS_TOTAL.labels(tool_name=tc.tool_name).inc()


class _Singletons:
    llm_factory: TenantLLMClientFactory | None = None
    redis_client: object | None = None


def _get_llm_factory() -> TenantLLMClientFactory:
    if _Singletons.llm_factory is None:
        _Singletons.llm_factory = TenantLLMClientFactory()
    return _Singletons.llm_factory


def invalidate_tenant_llm_client(tenant_id: uuid.UUID) -> None:
    """Drop a tenant's cached LLM client so the next chat picks up new LLM config.

    Called from the settings route after an LLM-config update; without this the
    cached client (provider/model/api_key) would keep serving for up to the
    factory TTL (1h) and the owner's change wouldn't take effect.
    """
    _get_llm_factory().invalidate(tenant_id)


def _get_redis_client() -> object | None:
    if _Singletons.redis_client is not None:
        return _Singletons.redis_client
    try:
        _Singletons.redis_client = aioredis.from_url(get_settings().redis_url)
        return _Singletons.redis_client
    except Exception:
        return None


async def _acquire_thread_lock(thread_id: str) -> ThreadLock | None:
    """Acquire a Redis-based thread lock. Returns the lock or None if unavailable."""
    client = _get_redis_client()
    if client is None:
        return None

    try:
        lock = ThreadLock(client, thread_id)
        acquired = await lock.acquire()
        if not acquired:
            logger.warning("gateway.thread_lock.contention", thread_id=thread_id)
        return lock
    except Exception:
        logger.warning("gateway.thread_lock.unavailable", thread_id=thread_id)
        return None
