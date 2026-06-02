"""LangGraph state graph for the agent loop.

This is the ONLY file in the codebase that imports `langgraph`. The graph
implements: route → tool_call → tool_execute → route (loop). No checkpointer
is used — the DB messages table is the cross-turn source of truth, and the
graph runs fresh per turn.

The graph nodes translate between domain value objects (LLMMessage) and
LangChain message types at the boundary, so the rest of the ai/ layer
never sees `langgraph` or `langchain_core` types.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, TypedDict
from uuid import UUID

import structlog
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.constants import END
from langgraph.graph import StateGraph

from src.ai.tools.escalate_question import run_escalate_question
from src.ai.tools.remove_key_fact import run_remove_key_fact
from src.ai.tools.save_key_fact import run_save_key_fact
from src.ai.tools.search_documents import run_search_documents
from src.ai.types import AgentLoopResult, ToolCallResult, ToolDef
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.llm.ports import LLMClientPort
from src.domain.llm.value_objects import LLMMessage, LLMMessageRole
from src.domain.rag.ports import RetrieverPort

logger = structlog.get_logger()

_MAX_ITERATIONS = 5

# Sent to the asker when the agent loop ends without a usable reply — e.g. the
# model hit the iteration cap while still requesting tools (its last message
# carries tool calls and empty content). Better a graceful message than a blank.
_FALLBACK_REPLY = (
    "I'm sorry — I couldn't put together a complete answer just now. "
    "Could you rephrase your question, or I can pass this to a team member?"
)


def _final_reply_text(messages: Sequence[BaseMessage]) -> str:
    """Extract the assistant's final reply text, with a safe fallback.

    The loop can terminate on the iteration cap while the last LLM message
    still carries tool calls and empty content; returning that empty string
    would send the asker a blank reply. Fall back to a graceful message.
    """
    if not messages:
        return _FALLBACK_REPLY
    last = messages[-1]
    content = last.content if isinstance(last, AIMessage) else str(last.content)
    text = content if isinstance(content, str) else str(content)
    return text if text.strip() else _FALLBACK_REPLY


class AgentState(TypedDict):
    messages: list[BaseMessage]
    tool_calls_made: list[ToolCallResult]
    total_input_tokens: int
    total_output_tokens: int
    total_cache_tokens: int
    iteration: int
    # Injected context (read-only).
    tenant_id: str
    channel: str
    conversation_id: str | None
    contact_id: str | None


async def _execute_tools_node(
    state: AgentState,
    *,
    retriever: RetrieverPort,
    uow: UnitOfWork,
) -> dict[str, Any]:
    last_msg = state["messages"][-1]
    if not isinstance(last_msg, AIMessage) or not last_msg.tool_calls:
        return dict(state)

    new_messages: list[BaseMessage] = []
    new_tool_calls: list[ToolCallResult] = []
    tenant_id = UUID(state["tenant_id"])
    channel = ConversationChannel(state["channel"])
    conversation_id = UUID(state["conversation_id"]) if state["conversation_id"] else None
    contact_id = UUID(state["contact_id"]) if state["contact_id"] else None

    for tc in last_msg.tool_calls:
        tool_name = tc["name"]
        args = tc.get("args") or {}
        logger.info("graph.tool_call", tool=tool_name, iteration=state["iteration"])

        try:
            result = await _dispatch_tool(
                tool_name=tool_name,
                arguments=args,
                tenant_id=tenant_id,
                channel=channel,
                conversation_id=conversation_id,
                contact_id=contact_id,
                retriever=retriever,
                uow=uow,
            )
        except Exception:
            # A single tool failure must not crash the whole turn — surface it as a
            # result so the model can recover (apologize, escalate, or answer anyway).
            logger.warning("graph.tool_error", tool=tool_name, iteration=state["iteration"], exc_info=True)
            result = {"error": f"The {tool_name} tool failed and returned no result."}
        result_str = json.dumps(result, default=str)
        new_messages.append(ToolMessage(content=result_str, tool_call_id=tc.get("id", "")))
        new_tool_calls.append(
            ToolCallResult(
                tool_name=tool_name,
                arguments=args,
                result=result,
                summary=result_str[:300],
            )
        )

    return {
        "messages": [*state["messages"], *new_messages],
        "tool_calls_made": [*state["tool_calls_made"], *new_tool_calls],
        "iteration": state["iteration"] + 1,
    }


def _should_continue(state: AgentState) -> str:
    last = state["messages"][-1]
    if isinstance(last, AIMessage) and last.tool_calls and state["iteration"] < _MAX_ITERATIONS:
        return "execute_tools"
    return END


def build_agent_graph(
    *,
    llm: LLMClientPort,
    tools: Sequence[ToolDef],
    retriever: RetrieverPort,
    uow: UnitOfWork,
    max_tokens: int = 1024,
    temperature: float | None = None,
) -> StateGraph[AgentState]:
    """Build a fresh (stateless) LangGraph for one agent turn."""

    tool_schemas = [_to_openai_schema(t) for t in tools]

    async def call_llm(state: AgentState) -> dict[str, Any]:
        response = await llm.chat_with_tools(
            _from_lc_messages(state["messages"]),
            tools=tool_schemas if tool_schemas else None,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        ai_msg = _to_ai_message(response.text, response.tool_calls)
        return {
            "messages": [*state["messages"], ai_msg],
            "total_input_tokens": state["total_input_tokens"] + response.usage.input_tokens,
            "total_output_tokens": state["total_output_tokens"] + response.usage.output_tokens,
            "total_cache_tokens": state["total_cache_tokens"] + response.usage.cache_read_tokens,
        }

    async def execute_tools(state: AgentState) -> dict[str, Any]:
        return await _execute_tools_node(state, retriever=retriever, uow=uow)

    graph: StateGraph[AgentState] = StateGraph(AgentState)
    graph.add_node("call_llm", call_llm)
    graph.add_node("execute_tools", execute_tools)
    graph.set_entry_point("call_llm")
    graph.add_conditional_edges("call_llm", _should_continue, {"execute_tools": "execute_tools", END: END})
    graph.add_edge("execute_tools", "call_llm")

    return graph


async def run_graph(
    graph: StateGraph[AgentState],
    *,
    messages: list[LLMMessage],
    tenant_id: UUID,
    channel: ConversationChannel,
    conversation_id: UUID | None,
    contact_id: UUID | None,
) -> AgentLoopResult:
    """Compile and invoke the graph. Returns domain-typed result."""
    compiled = graph.compile()

    lc_messages = _to_lc_messages(messages)
    initial_state: AgentState = {
        "messages": lc_messages,
        "tool_calls_made": [],
        "total_input_tokens": 0,
        "total_output_tokens": 0,
        "total_cache_tokens": 0,
        "iteration": 0,
        "tenant_id": str(tenant_id),
        "channel": channel.value,
        "conversation_id": str(conversation_id) if conversation_id else None,
        "contact_id": str(contact_id) if contact_id else None,
    }

    final_state = await compiled.ainvoke(initial_state)

    return AgentLoopResult(
        text=_final_reply_text(final_state["messages"]),
        tool_calls=final_state["tool_calls_made"],
        input_tokens=final_state["total_input_tokens"],
        output_tokens=final_state["total_output_tokens"],
        cache_read_tokens=final_state["total_cache_tokens"],
    )


# ── Internal helpers ──────────────────────────────────────────────


async def _dispatch_tool(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    tenant_id: UUID,
    channel: ConversationChannel,
    conversation_id: UUID | None,
    contact_id: UUID | None,
    retriever: RetrieverPort,
    uow: UnitOfWork,
) -> Any:
    if tool_name == "search_documents":
        return await run_search_documents(arguments=arguments, tenant_id=tenant_id, retriever=retriever)

    if tool_name == "escalate_question":
        return await run_escalate_question(
            arguments=arguments,
            tenant_id=tenant_id,
            channel=channel,
            conversation_id=conversation_id,
            contact_id=contact_id,
            uow=uow,
        )

    if tool_name in ("save_key_fact", "remove_key_fact"):
        if contact_id is None:
            return {"error": f"Cannot {tool_name} without a resolved contact"}
        runner = run_save_key_fact if tool_name == "save_key_fact" else run_remove_key_fact
        return await runner(
            arguments=arguments,
            tenant_id=tenant_id,
            contact_id=contact_id,
            uow=uow,
        )

    return {"error": f"Unknown tool: {tool_name}"}


def _to_lc_messages(msgs: list[LLMMessage]) -> list[BaseMessage]:
    out: list[BaseMessage] = []
    for m in msgs:
        match m.role:
            case LLMMessageRole.SYSTEM:
                out.append(SystemMessage(content=m.content))
            case LLMMessageRole.USER:
                out.append(HumanMessage(content=m.content))
            case LLMMessageRole.ASSISTANT:
                out.append(AIMessage(content=m.content))
            case LLMMessageRole.TOOL:
                out.append(ToolMessage(content=m.content, tool_call_id=m.tool_call_id or ""))
    return out


def _from_lc_messages(msgs: list[BaseMessage]) -> list[LLMMessage]:
    out: list[LLMMessage] = []
    for m in msgs:
        if isinstance(m, SystemMessage):
            out.append(LLMMessage(role=LLMMessageRole.SYSTEM, content=str(m.content)))
        elif isinstance(m, HumanMessage):
            out.append(LLMMessage(role=LLMMessageRole.USER, content=str(m.content)))
        elif isinstance(m, AIMessage):
            out.append(LLMMessage(role=LLMMessageRole.ASSISTANT, content=str(m.content)))
        elif isinstance(m, ToolMessage):
            out.append(LLMMessage(role=LLMMessageRole.TOOL, content=str(m.content), tool_call_id=m.tool_call_id))
    return out


def _to_ai_message(text: str, tool_calls: tuple[Any, ...]) -> AIMessage:
    if tool_calls:
        return AIMessage(
            content=text or "",
            tool_calls=[{"id": tc.id, "name": tc.name, "args": tc.arguments} for tc in tool_calls],
        )
    return AIMessage(content=text)


def _to_openai_schema(tool: ToolDef) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters_schema,
        },
    }
