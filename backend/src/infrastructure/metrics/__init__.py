"""Prometheus metrics — HTTP, LLM, agent, and tool counters.

Imported by the ai/ layer (the one allowed exception to the DDD
infrastructure import rule) for recording per-call observability.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

# ── HTTP ──────────────────────────────────────────────────────────
HTTP_REQUESTS_TOTAL = Counter(
    "sight_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION = Histogram(
    "sight_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "path"],
)

# ── LLM ───────────────────────────────────────────────────────────
LLM_CALLS_TOTAL = Counter(
    "sight_llm_calls_total",
    "Total LLM API calls",
    ["provider", "model", "status"],
)

LLM_TOKENS_TOTAL = Counter(
    "sight_llm_tokens_total",
    "Total tokens consumed",
    ["provider", "model", "direction"],  # direction: input, output, cache_read
)

# ── Agent ─────────────────────────────────────────────────────────
AGENT_INVOCATIONS_TOTAL = Counter(
    "sight_agent_invocations_total",
    "Total agent loop invocations",
    ["channel"],
)

AGENT_TOOL_CALLS_TOTAL = Counter(
    "sight_agent_tool_calls_total",
    "Total tool calls made by the agent",
    ["tool_name"],
)

# ── RAG ───────────────────────────────────────────────────────────
RAG_RETRIEVALS_TOTAL = Counter(
    "sight_rag_retrievals_total",
    "Total hybrid retrieval queries",
)

# ── Secrets / encryption ──────────────────────────────────────────
# Fires when a stored tenant secret fails to decrypt — almost always ENCRYPTION_KEY
# rotated away without keeping the old key in ENCRYPTION_KEY_FALLBACKS. Alert on any
# increase: each failure means a secret silently read back as "" (e.g. webhook 403s).
CRYPTO_DECRYPT_FAILURES_TOTAL = Counter(
    "sight_crypto_decrypt_failures_total",
    "Total tenant-secret decryptions that failed (likely a key rotated away without its fallback)",
)

# ── Escalation ────────────────────────────────────────────────────
QUESTIONS_SUBMITTED_TOTAL = Counter(
    "sight_questions_submitted_total",
    "Total questions escalated to the owner",
    ["channel"],
)

QUESTIONS_RESOLVED_TOTAL = Counter(
    "sight_questions_resolved_total",
    "Total questions resolved by the owner",
)
