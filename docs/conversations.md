# Conversations

How threads, messages, and tool exchanges are stored.

## Why DB-as-truth (not LangGraph's checkpointer)

LangGraph offers `AsyncPostgresSaver` to persist agent state per-thread.
That works, but the persisted blob is opaque JSONB keyed by `thread_id`
with no schema. It's hard to render in an admin UI, hard to migrate when
LangGraph's internal shape changes, and hard to query analytically.

frontdesk uses LangGraph for **per-turn orchestration only** and keeps
the `messages` table as the cross-turn source of truth. Each invocation
loads history from the DB, builds the LangGraph state, runs the graph,
persists the result. Slightly more glue code; vastly simpler audit,
admin UI, and migration story.

## Schema

```sql
CREATE TABLE conversations (
  id              UUID PRIMARY KEY,
  tenant_id       UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  thread_id       VARCHAR(128) UNIQUE NOT NULL,        -- channel-derived
  channel         VARCHAR(32)  NOT NULL,
  participant_id  UUID,                                -- asker id, null for owner-AI chat
  created_at      TIMESTAMPTZ NOT NULL,
  updated_at      TIMESTAMPTZ NOT NULL,
  last_message_at TIMESTAMPTZ
);

CREATE TABLE messages (
  id                  UUID PRIMARY KEY,
  conversation_id     UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
  tenant_id           UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  role                VARCHAR(16) NOT NULL,    -- user | assistant | system | tool
  content             TEXT NOT NULL,
  hidden              BOOLEAN NOT NULL DEFAULT FALSE,

  -- tool exchange (assistant->tool_use or tool->tool_result row)
  tool_call_id        VARCHAR(128),
  tool_args           JSONB,                   -- what the LLM asked
  tool_result         JSONB,                   -- raw provider result

  -- tiered compression (older tool turns get rolled up)
  is_compressed       BOOLEAN NOT NULL DEFAULT FALSE,
  compressed_summary  TEXT,

  -- structured checkpoint row (PropertyBot's pattern, generalized)
  is_checkpoint       BOOLEAN NOT NULL DEFAULT FALSE,

  token_count         INTEGER NOT NULL DEFAULT 0,
  request_id          VARCHAR(64),
  created_at          TIMESTAMPTZ NOT NULL
);
```

## Tool exchange fidelity

The `tool_args` + `tool_result` JSONB columns are deliberate. They fix a
gap in the naive "paraphrase tool result into a system message" pattern
where the LLM loses awareness of what arguments it previously passed.

```text
Naive (lossy):
  assistant: "I'll search for documents about returns."
  system:    "Tool search_documents responded — summary: 3 chunks found."   ← what did I ask?

frontdesk:
  assistant: AIMessage(tool_calls=[
    {"id": "call_xyz", "name": "search_documents",
     "args": {"query": "return policy 30 days"}}
  ])
  tool:      ToolMessage(tool_call_id="call_xyz",
                          content="3 chunks found",
                          tool_result={"chunks": [...]})
```

The LLM sees real `tool_use` / `tool_result` blocks (the format it was
trained on) for recent turns. Older tool exchanges roll up to a summary
while `tool_args` + `tool_result` are retained in JSONB so a `[tool_ctx=
<uuid>]` reference can recover the full payload when needed.

## Tiered tool compression (planned, Phase 5b)

```text
Recent N tool exchanges (e.g. last 5)
  ✓ Full tool_use / tool_result blocks in native format
  ✓ LLM sees what it asked AND what came back, in trained format

Older tool exchanges (rolled off)
  ✓ Compressed to a single summary message
  ✓ tool_args preserved in the summary text:
      "called search_documents with {query: 'return policy 30 days'} → 3 results"
  ✓ tool_args + tool_result JSONB retained for UUID-driven recovery

Beyond the checkpoint threshold
  ✓ Structured JSON checkpoint summarises current state
    (PropertyBot's pattern, generalised: documents_discussed,
     current_query_state, open_questions, key_decisions)
```

This pattern is what Anthropic recommends for long agentic conversations:
lossless near-term, lossy long-term, with arg preservation so the LLM
never wonders "what did I ask?"

## Checkpoint query helpers

```python
# messages_repo.py
async def list_since_last_checkpoint(self, conversation_id) -> list[Message]:
    """Latest checkpoint + everything newer — what the summariser sees."""

async def sum_tokens_since_checkpoint(self, conversation_id) -> int:
    """Drives the checkpoint trigger (default 3000 tokens)."""
```

Used by the upcoming checkpoint generator in `ai/context/checkpoint.py`
(modeled on PropertyBot's `src/ai/context/checkpoint.py` but with a
generalized JSON schema for the frontdesk domain).
