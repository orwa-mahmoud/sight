# 0002 — LangGraph runs per-turn, isolated to one file; the DB is the source of truth

**Status:** Accepted

## Context

The agent is an LLM → tool → LLM loop. LangGraph models that well, but it also
offers persistent checkpointers that would make it the owner of conversation
state. I already have a relational model for conversations and messages, and I
did not want two competing sources of truth, nor LangGraph/LangChain types
spreading through the codebase.

## Decision

- **No LangGraph checkpointer.** The `messages` table is the single source of
  truth. Each inbound message builds a **fresh, stateless graph** for that turn
  ([infrastructure/ai/graph.py](../../backend/src/infrastructure/ai/graph.py)),
  seeded from DB history (bounded to the latest checkpoint window).
- **LangGraph is confined to that one file.** It is the only `langgraph` import
  site; it translates domain `LLMMessage` ↔ LangChain message types at the
  boundary, so the rest of `ai/` never sees the framework.
- **The loop is capped** at 5 iterations with a graceful fallback reply, and a
  single failing tool is returned to the model as an error, never crashing the
  turn.
- **Tools call use cases, not repositories** — the agent reaches business logic
  through the same application layer as the REST API.

## Consequences

**Good:** conversation state lives in one place (queryable, backup-able,
RLS-protected); the framework can be swapped or upgraded by editing one file;
horizontal scaling is trivial because turns are stateless. Replays/inspection use
ordinary SQL.

**Costs:** history is re-read and re-sent each turn (mitigated by checkpoint
summarization to bound context); no built-in cross-turn graph memory, by design.
A couple of `ai/` boundary pragmatics remain (the gateway wires infra adapters;
two key-fact tools touch the repo directly) — tracked for cleanup.
