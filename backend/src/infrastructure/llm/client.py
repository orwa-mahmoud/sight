"""Concrete `LLMClientPort` implementation backed by LangChain's `init_chat_model`.

LangChain is intentionally confined to this single module. Callers see only
domain value objects (`LLMMessage`, `LLMCallResult`). Provider / model are
configured at construction time; multi-tenant per-tenant config is composed
above this client by a factory.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from src.domain.llm.ports import LLMClientPort
from src.domain.llm.value_objects import (
    LLMCallResult,
    LLMMessage,
    LLMMessageRole,
    LLMToolCall,
    TokenUsage,
)
from src.infrastructure.llm.error_classifier import classify_llm_error

_LLM_RETRY_ATTEMPTS = 3
_ANTHROPIC = "anthropic"


def _is_transient_llm_error(exc: BaseException) -> bool:
    """Retry only transient provider errors (rate limit / timeout / outage)."""
    return isinstance(exc, Exception) and classify_llm_error(exc).is_transient


class LangChainLLMClient(LLMClientPort):
    """One client = one (provider, model) pair. Build a new instance per tenant."""

    def __init__(self, *, provider: str, model: str, api_key: str | None = None) -> None:
        self._provider = provider
        self._model = model
        kwargs: dict[str, Any] = {"model_provider": provider}
        if api_key:
            kwargs["api_key"] = api_key
        self._chat = init_chat_model(model, **kwargs)

    @retry(
        retry=retry_if_exception(_is_transient_llm_error),
        stop=stop_after_attempt(_LLM_RETRY_ATTEMPTS),
        wait=wait_exponential(multiplier=0.5, max=4),
        reraise=True,
    )
    async def chat_with_tools(
        self,
        messages: Sequence[LLMMessage],
        *,
        tools: Sequence[dict[str, Any]] | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> LLMCallResult:
        chat = self._chat
        bind_kwargs: dict[str, Any] = {}
        if max_tokens is not None:
            bind_kwargs["max_tokens"] = max_tokens
        if temperature is not None:
            bind_kwargs["temperature"] = temperature
        if bind_kwargs:
            chat = chat.bind(**bind_kwargs)
        if tools:
            chat = chat.bind_tools(list(tools))

        lc_messages = [_to_lc_message(m, self._provider) for m in messages]
        response = await chat.ainvoke(lc_messages)
        return _to_call_result(response, provider=self._provider, model=self._model)


# ── Translation between domain VOs and langchain_core messages ────


def _message_content(msg: LLMMessage, provider: str) -> str | list[str | dict[Any, Any]]:
    """Plain text, unless the caller asked to cache this prefix on Anthropic — then a
    single text block with `cache_control: ephemeral`, so a large repeated prefix
    (e.g. the document in Contextual Retrieval) is billed once and read cheaply on
    later calls within the cache TTL. Other providers cache stable prefixes on their
    own, so the hint is a no-op there."""
    if msg.cache and provider == _ANTHROPIC:
        return [{"type": "text", "text": msg.content, "cache_control": {"type": "ephemeral"}}]
    return msg.content


def _to_lc_message(msg: LLMMessage, provider: str = "") -> Any:
    content = _message_content(msg, provider)
    match msg.role:
        case LLMMessageRole.SYSTEM:
            return SystemMessage(content=content)
        case LLMMessageRole.USER:
            return HumanMessage(content=content)
        case LLMMessageRole.ASSISTANT:
            return AIMessage(content=content)
        case LLMMessageRole.TOOL:
            return ToolMessage(content=content, tool_call_id=msg.tool_call_id or "")


def _to_call_result(response: AIMessage, *, provider: str, model: str) -> LLMCallResult:
    text = response.content if isinstance(response.content, str) else ""
    tool_calls = tuple(
        LLMToolCall(
            id=tc.get("id") or "",
            name=tc.get("name") or "",
            arguments=tc.get("args") or {},
        )
        for tc in (response.tool_calls or [])
    )
    usage_meta = getattr(response, "usage_metadata", None) or {}
    usage = TokenUsage(
        input_tokens=int(usage_meta.get("input_tokens", 0) or 0),
        output_tokens=int(usage_meta.get("output_tokens", 0) or 0),
        cache_read_tokens=int((usage_meta.get("input_token_details") or {}).get("cache_read", 0) or 0),
    )
    return LLMCallResult(
        text=text,
        tool_calls=tool_calls,
        usage=usage,
        provider=provider,
        model=model,
    )
