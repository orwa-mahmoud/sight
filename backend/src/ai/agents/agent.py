"""Main tool-calling agent — runs the LLM → tool → LLM loop.

The loop is intentionally simple and synchronous (no LangGraph state machine
for v1). The LLM is called with the available tools. If it returns tool_calls,
we execute them and feed the results back. Repeat until the LLM gives a text
reply with no tool_calls, or we hit the max-iterations safety cap.

This file is allowed to import `langchain_core.messages.ToolMessage` as a
type — per the DDD rule, that's the only langchain symbol the ai/ layer sees.
The actual LLM call goes through the `LLMClientPort`.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any
from uuid import UUID

import structlog

from src.ai.types import AgentLoopResult, ToolCallResult, ToolDef
from src.application.shared.unit_of_work import UnitOfWork
from src.domain.conversations.value_objects import ConversationChannel
from src.domain.llm.ports import LLMClientPort
from src.domain.llm.value_objects import LLMCallResult, LLMMessage, LLMMessageRole
from src.domain.rag.ports import RetrieverPort

from ..tools.escalate_question import run_escalate_question
from ..tools.search_documents import run_search_documents

logger = structlog.get_logger()

_MAX_TOOL_ITERATIONS = 5


async def run_agent_loop(
    *,
    messages: list[LLMMessage],
    tools: Sequence[ToolDef],
    llm: LLMClientPort,
    tenant_id: UUID,
    channel: ConversationChannel,
    conversation_id: UUID | None,
    asker_name: str | None,
    asker_contact: str | None,
    retriever: RetrieverPort,
    uow: UnitOfWork,
    max_tokens: int = 1024,
) -> AgentLoopResult:
    tool_schemas = [_to_openai_schema(t) for t in tools]
    all_tool_calls: list[ToolCallResult] = []
    total_input = 0
    total_output = 0
    total_cache = 0

    for iteration in range(_MAX_TOOL_ITERATIONS):
        response: LLMCallResult = await llm.chat_with_tools(
            messages,
            tools=tool_schemas if tool_schemas else None,
            max_tokens=max_tokens,
        )
        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens
        total_cache += response.usage.cache_read_tokens

        if not response.tool_calls:
            return AgentLoopResult(
                text=response.text,
                tool_calls=all_tool_calls,
                input_tokens=total_input,
                output_tokens=total_output,
                cache_read_tokens=total_cache,
            )

        # Process each tool call.
        for tc in response.tool_calls:
            logger.info("agent.tool_call", tool=tc.name, iteration=iteration)
            result = await _execute_tool(
                tool_name=tc.name,
                arguments=tc.arguments,
                tenant_id=tenant_id,
                channel=channel,
                conversation_id=conversation_id,
                asker_name=asker_name,
                asker_contact=asker_contact,
                retriever=retriever,
                uow=uow,
            )
            result_str = json.dumps(result, default=str)
            summary = result_str[:300] if len(result_str) > 300 else result_str
            all_tool_calls.append(
                ToolCallResult(
                    tool_name=tc.name,
                    arguments=tc.arguments,
                    result=result,
                    summary=summary,
                )
            )
            # Feed the tool call + result back to the LLM for the next iteration.
            messages.append(LLMMessage(role=LLMMessageRole.ASSISTANT, content="", tool_calls=(tc,)))
            messages.append(LLMMessage(role=LLMMessageRole.TOOL, content=result_str, tool_call_id=tc.id))

    # Safety cap: if we hit max iterations, return whatever text we have.
    logger.warning("agent.max_iterations_reached", iterations=_MAX_TOOL_ITERATIONS)
    return AgentLoopResult(
        text="I apologize, but I'm having trouble processing your request right now. Please try again.",
        tool_calls=all_tool_calls,
        input_tokens=total_input,
        output_tokens=total_output,
        cache_read_tokens=total_cache,
    )


async def _execute_tool(
    *,
    tool_name: str,
    arguments: dict[str, Any],
    tenant_id: UUID,
    channel: ConversationChannel,
    conversation_id: UUID | None,
    asker_name: str | None,
    asker_contact: str | None,
    retriever: RetrieverPort,
    uow: UnitOfWork,
) -> Any:
    match tool_name:
        case "search_documents":
            return await run_search_documents(arguments=arguments, tenant_id=tenant_id, retriever=retriever)
        case "escalate_question":
            return await run_escalate_question(
                arguments=arguments,
                tenant_id=tenant_id,
                channel=channel,
                conversation_id=conversation_id,
                asker_name=asker_name,
                asker_contact=asker_contact,
                uow=uow,
            )
        case _:
            logger.warning("agent.unknown_tool", tool=tool_name)
            return {"error": f"Unknown tool: {tool_name}"}


def _to_openai_schema(tool: ToolDef) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters_schema,
        },
    }
