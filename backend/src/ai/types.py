"""Types shared across the AI orchestration layer."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from src.domain.conversations.value_objects import ConversationChannel


@dataclass(kw_only=True)
class ChatInput:
    """Everything the gateway needs to process one inbound message."""

    message: str
    tenant_id: UUID
    channel: ConversationChannel
    sender_identifier: str  # phone for WA, telegram_user_id for TG
    sender_name: str | None = None
    thread_id: str | None = None  # if known; gateway resolves if None
    contact_id: UUID | None = None  # resolved by sender resolution; None for anonymous


@dataclass(kw_only=True)
class ChatSource:
    """A knowledge-base chunk the agent retrieved to ground its answer.

    Surfaced to the dashboard chat so an owner can see *which* of their
    documents the AI used (filename is resolved client-side from document_id).
    """

    document_id: str
    snippet: str
    score: float


@dataclass(kw_only=True)
class ChatResult:
    """What the gateway returns after processing."""

    response: str
    thread_id: str
    escalated: bool = False  # true if a Question was submitted
    request_id: str = ""
    sources: list[ChatSource] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass(frozen=True, kw_only=True)
class ToolDef:
    """Framework-agnostic tool definition — adapters convert to LangChain
    StructuredTool or OpenAI function schema at call time."""

    name: str
    description: str
    parameters_schema: dict[str, Any]


@dataclass(kw_only=True)
class ToolCallResult:
    """Result of one tool execution."""

    tool_name: str
    arguments: dict[str, Any]
    result: Any
    summary: str = ""


@dataclass(kw_only=True)
class AgentLoopResult:
    """Output of the agent loop — final text + any tool calls that happened."""

    text: str
    tool_calls: list[ToolCallResult] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
