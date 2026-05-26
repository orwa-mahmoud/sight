"""Prometheus metrics — HTTP, LLM, agent, and tool counters.

Imported by the ai/ layer (the one allowed exception to the DDD
infrastructure import rule) for recording per-call observability.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# ── HTTP ──────────────────────────────────────────────────────────
HTTP_REQUESTS_TOTAL = Counter(
    "frontdesk_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "frontdesk_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)

# ── LLM ───────────────────────────────────────────────────────────
LLM_CALLS_TOTAL = Counter(
    "frontdesk_llm_calls_total",
    "Total LLM API calls",
    ["provider", "model", "status"],
)

LLM_TOKENS_TOTAL = Counter(
    "frontdesk_llm_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "direction"],  # direction: input, output, cache_read
)

# ── Agent ─────────────────────────────────────────────────────────
AGENT_INVOCATIONS_TOTAL = Counter(
    "frontdesk_agent_invocations_total",
    "Total agent loop invocations",
    ["channel"],
)

AGENT_TOOL_CALLS_TOTAL = Counter(
    "frontdesk_agent_tool_calls_total",
    "Total tool calls made by the agent",
    ["tool_name"],
)

AGENT_DURATION = Histogram(
    "frontdesk_agent_duration_seconds",
    "Agent loop latency (includes all LLM + tool calls)",
    ["channel"],
)

# ── RAG ───────────────────────────────────────────────────────────
RAG_RETRIEVALS_TOTAL = Counter(
    "frontdesk_rag_retrievals_total",
    "Total hybrid retrieval queries",
)

# ── Escalation ────────────────────────────────────────────────────
QUESTIONS_SUBMITTED_TOTAL = Counter(
    "frontdesk_questions_submitted_total",
    "Total questions escalated to the owner",
    ["channel"],
)

QUESTIONS_RESOLVED_TOTAL = Counter(
    "frontdesk_questions_resolved_total",
    "Total questions resolved by the owner",
)
