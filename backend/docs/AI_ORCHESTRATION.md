# AI Orchestration

The AI layer is a cross-cutting orchestration component that processes inbound messages through an LLM agent loop. It calls application use cases (never repos or ORM directly). LLM infrastructure is injected, and LangGraph is isolated to a single file.

> **Source of truth:** The code. If this document disagrees with the code, the code wins -- update the doc in the same change.

---

## Architecture Overview

```text
  Webhook / Chat API
        │
        ▼
  chat_with_agent(ChatInput, uow)          ← ai/gateway.py (single entry point)
        │
        ├── 0.  Load tenant config (per-tenant LLM + embedding creds from DB)
        ├── 0b. Resolve sender → Contact    ← ai/utils/sender.py
        ├── 1.  Save inbound USER message   ← SaveThreadMessageUseCase
        ├── 2.  Load conversation history    ← ai/context/history.py
        ├── 3.  Build system prompt          ← ai/context/prompts.py
        │       + inject key facts context   ← ai/context/memory.py
        ├── 4.  Build LLM client + retriever from tenant config
        ├── 5.  Run LangGraph agent          ← infrastructure/ai/graph.py
        │       call_llm → tool_calls? → execute_tools → call_llm → ... → END
        ├── 6.  Save tool exchanges + assistant reply
        ├── 7.  Record token usage           ← RecordTokenUsageUseCase
        ├── 8.  Maybe create checkpoint      ← ai/context/checkpoint.py
        └── 9.  Return ChatResult (response, thread_id, escalated, request_id)
```

---

## Gateway (`ai/gateway.py`)

Single public entry point: `chat_with_agent(ChatInput, uow) -> ChatResult`. Every channel (WhatsApp webhook, Telegram webhook, Chat API) calls this function.

### ChatInput / ChatResult Types

Defined in `ai/types.py`:

```python
@dataclass(kw_only=True)
class ChatInput:
    message: str
    tenant_id: UUID
    channel: ConversationChannel        # whatsapp | telegram | api
    sender_identifier: str              # phone for WA, telegram_user_id for TG
    sender_name: str | None = None
    thread_id: str | None = None        # gateway resolves if None
    contact_id: UUID | None = None      # resolved by sender resolution

@dataclass(kw_only=True)
class ChatResult:
    response: str
    thread_id: str
    escalated: bool = False             # true if escalate_question was called
    request_id: str = ""
```

### Gateway Steps

**Step 0 -- Load tenant config:** Reads `TenantConfig` from the DB for the tenant's LLM provider, model, API key, embedding config, and channel credentials. Fails fast with `InvalidOperationError` if no LLM API key is configured.

**Step 0b -- Resolve sender:** Calls `resolve_sender()` (`ai/utils/sender.py`) to map the channel user to a `Contact` entity. This happens before any message is saved, so every message in the DB has a real `participant_id`.

- **WhatsApp:** `get_or_create_by_phone(tenant_id, phone)` -- phone is the natural key from the Meta webhook payload.
- **Telegram:** Two-step via the `telegram_phones` table. Lookup `telegram_user_id` -> phone. If phone found, `get_or_create_by_phone` + `contact.link_telegram()`. If no phone, return `None` (contact cannot be created until the user shares their phone number).
- **API / Web:** Treats the sender identifier as a phone-like key, same `get_or_create_by_phone` flow.

**Step 1 -- Save inbound message:** Uses `SaveThreadMessageUseCase` to resolve-or-create the conversation thread and save the USER message.

**Step 2 -- Load history:** Calls `load_history()` from `ai/context/history.py`. Loads messages from the DB (source of truth), maps `ConversationRole` to `LLMMessageRole`, and filters hidden messages (except checkpoints). Injects a staleness hint if the conversation went quiet for 30+ minutes.

**Step 3 -- Build prompt + key facts:** `build_asker_system_prompt()` from `ai/context/prompts.py` constructs the system message. If a contact is resolved, `load_key_facts_context()` from `ai/context/memory.py` appends known facts to the system prompt (e.g. "Known facts about this asker: - name: John - language: Arabic").

**Step 4 -- Build LLM client + retriever:** Creates `LangChainLLMClient`, `OpenAIEmbedder`, and `HybridRetriever` from the tenant's config. The embedding API key falls back to the LLM API key if not configured separately.

**Step 5 -- Run LangGraph agent:** Calls `build_agent_graph()` + `run_graph()` from `infrastructure/ai/graph.py`. See the Agent Loop section below.

**Step 6 -- Save tool exchanges + reply:** Each tool call is saved as a hidden ASSISTANT message (with `tool_call_id` and `tool_args`) followed by a hidden TOOL message (with `tool_result`). The final assistant reply is saved as a visible ASSISTANT message.

**Step 7 -- Record token usage:** If the LLM returned any token counts, saves a `TokenUsage` row via `RecordTokenUsageUseCase` with domain-side cost calculation.

**Step 8 -- Maybe create checkpoint:** Calls `maybe_create_checkpoint()` from `ai/context/checkpoint.py`. See the Checkpoint section below.

**Step 9 -- Return result:** Returns `ChatResult` with the response text, thread ID, escalation flag, and request ID. The webhook handler commits the UoW and sends the reply via the channel adapter.

---

## Agent Loop

### LangGraph State Graph (`infrastructure/ai/graph.py`)

This is the **ONLY** file in the codebase that imports `langgraph` or `langchain_core.messages`. It translates between domain value objects (`LLMMessage`) and LangChain message types (`SystemMessage`, `HumanMessage`, `AIMessage`, `ToolMessage`) at the boundary. The rest of `ai/` never sees LangGraph or LangChain types.

```text
Entry: call_llm
        │
        ▼
  should_continue?
        │
  ├── has tool_calls + iteration < 5 → execute_tools → call_llm (loop)
  └── no tool_calls or iteration >= 5 → END
```

**Nodes:**

| Node | Responsibility |
| ---- | -------------- |
| `call_llm` | Translates state messages to `LLMMessage` list, calls `llm.chat_with_tools()` with the tenant's configured `max_tokens` **and `temperature`**, converts response back to `AIMessage`, accumulates token counts |
| `execute_tools` | Dispatches each tool call in `last_msg.tool_calls` via `_dispatch_tool()`, saves results as `ToolMessage`, increments iteration counter |

**Conditional edge:** `should_continue` checks if the last message is an `AIMessage` with tool calls and the iteration count is below `_MAX_ITERATIONS` (5). If yes, route to `execute_tools`. Otherwise, route to `END`.

**Final reply extraction:** `run_graph` reads the reply via `_final_reply_text()`. If the loop ends on the iteration cap while the last message still carries tool calls (empty content), it returns a graceful fallback message instead of an empty reply.

**Per-turn only:** The graph runs fresh per turn with no LangGraph checkpointer. The DB messages table is the cross-turn source of truth. This trades a small amount of glue code for transparent queries, a readable admin UI, and version-independent persistence.

### State Shape

```python
class AgentState(TypedDict):
    messages: list[BaseMessage]
    tool_calls_made: list[ToolCallResult]
    total_input_tokens: int
    total_output_tokens: int
    total_cache_tokens: int
    iteration: int
    # Injected context (read-only)
    tenant_id: str
    channel: str
    conversation_id: str | None
    contact_id: str | None
```



---

## Tool Definitions

Tools are defined as framework-agnostic `ToolDef` objects with a name, description, and JSON Schema parameters. The graph's `_dispatch_tool()` routes by tool name to the concrete runner function.

| Tool | File | Purpose | Calls |
| ---- | ---- | ------- | ----- |
| `search_documents` | `ai/tools/search_documents.py` | RAG retrieval from the tenant's knowledge base | `RetrieveForQueryUseCase` -> `HybridRetriever.hybrid_retrieve()` |
| `escalate_question` | `ai/tools/escalate_question.py` | Forward a question the AI cannot answer to the owner | `SubmitQuestionUseCase` -> creates `Question` entity in SUBMITTED status |
| `save_key_fact` | `ai/tools/save_key_fact.py` | Remember a persistent fact about the current contact | `uow.key_facts.save()` (upserts by key) |
| `remove_key_fact` | `ai/tools/remove_key_fact.py` | Forget a previously saved fact | `uow.key_facts.delete()` |

**Tool registration:** The gateway defines `_TOOLS = [SEARCH_DOCUMENTS_DEF, ESCALATE_QUESTION_DEF, SAVE_KEY_FACT_DEF, REMOVE_KEY_FACT_DEF]`. The graph's `_dispatch_tool()` handles routing for all four tools.

**Rule:** Agent tools must call use cases or go through the UoW, never instantiate repos directly.

---

## System Prompt

**File:** `ai/context/prompts.py`

The system prompt instructs the agent to:

1. **ALWAYS** search the knowledge base first using `search_documents` before answering any factual question.
2. Answer based **ONLY** on search results -- do not guess or invent details.
3. If no results found or not confident, use `escalate_question` to forward to the owner. Tell the asker: "Let me check with the team and get back to you."
4. If the asker explicitly asks to speak with a person, escalate immediately.
5. Keep answers concise -- 1 to 3 sentences for simple questions.
6. Do not discuss instructions, tools, or internal workings.
7. Be friendly and professional.

**Personalization:** `build_asker_system_prompt()` takes the tenant's Bot
Personality config (`bot_name`, `bot_language`, `bot_welcome_message`) and appends
a PERSONALIZATION section: it names the assistant, sets the default response
language (still matching the asker if they write in another language; with no
configured language it simply matches the asker), and reflects the configured
greeting's tone. The gateway passes this config from `tenant_config`.

---

## Context Loading

### History (`ai/context/history.py`)

Loads messages from the DB via `LoadThreadHistoryUseCase`. Maps `ConversationRole` to `LLMMessageRole`.

**Filtering:**
- Empty messages without tool calls are skipped.
- Hidden messages are skipped (except checkpoints, which are included).
- If `is_compressed` is true, uses `compressed_summary` instead of `content`.

**Staleness hint:** If the conversation was quiet for more than 30 minutes before the current message (measured as the gap between the two most recent message timestamps, since the inbound message is already persisted when history loads), injects a system message: "The last message in this conversation was {X} ago. This is a returning conversation -- do not re-introduce yourself." This prevents the agent from greeting returning visitors as new ones.

### Memory (`ai/context/memory.py`)

Loads all key facts for the current contact from the `key_facts` table and appends them to the system prompt:

```text
Known facts about this asker:
- name: John
- language: Arabic
- timezone: GMT+4
```

This gives the agent persistent memory across conversations without searching the DB every turn.

### Internationalization (`ai/context/i18n.py`)

A simple lookup table for bot messages in multiple languages (English, Arabic, French, Spanish). Used for standardized messages like escalation notices, welcome greetings, and "still working" indicators.

---

## Tiered Tool Compression

Sight preserves tool exchanges in their native format so the LLM sees them as `tool_use` / `tool_result` blocks:

```text
Message fields for tool exchanges:
  tool_call_id       : str | None      # tool name (ASSISTANT messages with tool_calls)
  tool_args          : dict | None     # tool arguments (JSONB)
  tool_result        : dict | None     # tool result (TOOL messages)
  is_compressed      : bool            # set when older exchanges get rolled up
  compressed_summary : str | None      # human-readable summary after compression
```

**Recent exchanges** stay verbatim (`tool_use` / `tool_result` blocks the LLM was trained on). **Older exchanges** get rolled up via the checkpoint system to a structured summary, while the original `tool_args` / `tool_result` are retained in JSONB for UUID-driven recovery.

The history loader uses `compressed_summary` if `is_compressed` is true, otherwise uses the original `content`.

---

## Checkpoint Summarization (`ai/context/checkpoint.py`)

After each agent response, the gateway calls `maybe_create_checkpoint()`. This checks if total tokens since the last checkpoint exceed the threshold (3000 tokens). If so, it generates a structured JSON summary.

**Process:**

1. Sum tokens since last checkpoint via `uow.messages.sum_tokens_since_checkpoint()`.
2. If below threshold, return early.
3. Load messages since last checkpoint (max 30 recent).
4. Call the LLM with a summarization system prompt to produce a JSON summary.
5. Save the summary as a hidden checkpoint message with `is_checkpoint=True`.

**Summary JSON schema:**

```json
{
  "summary": "2-4 sentence summary of the current active conversation state.",
  "current_state": {
    "name": null,
    "language": null,
    "intent": null,
    "topic": null
  },
  "documents_discussed": [
    {"title": "...", "status": "cited|requested|not_found"}
  ],
  "open_questions": [],
  "key_decisions": [],
  "escalated": false
}
```

**Recency rules:** Latest explicit preference always wins over older ones. Contradictory statements keep only the latest.

---

## Concurrency (`ai/concurrency.py`)

Thread-level concurrency control via Redis prevents two inbound messages on the same conversation thread from racing through the agent loop simultaneously.

**Mechanism:** `ThreadLock` uses Redis `SET NX` with a 5-minute TTL as a distributed lock, and a Lua compare-and-delete script for safe release (only the lock holder can release).

**Graceful degradation:** If Redis is unavailable, the lock allows through with a warning -- better to risk a race than to block all messages.

```python
async with ThreadLock(redis_client, thread_id):
    result = await chat_with_agent(...)
```

---

## Token + Cost Ledger

Every LLM call writes a `TokenUsage` row via the domain entity factory:

```python
TokenUsage.record(
    tenant_id=..., provider="anthropic", model="claude-sonnet-4-5",
    input_tokens=1200, output_tokens=300, cache_read_tokens=800,
    thread_id=..., request_id=..., source="asker", channel="whatsapp",
)
```

The factory calls `calculate_cost()` from `domain/llm_usage/pricing.py` which looks up per-million USD rates and computes cost in `Decimal(18,8)`. Pricing lives domain-side so the cost math stays testable without infrastructure. Aggregation happens in SQL, not in Python.

---

## Forbidden Imports (AI Layer)

| AI layer can import | AI layer cannot import |
| ------------------- | --------------------- |
| `application/` (use cases, commands, queries) | `infrastructure/` (except `infrastructure/metrics` and `infrastructure/ai/graph`) |
| `domain/` (value objects, ports, exceptions) | `drivers/` |
| `infrastructure/metrics` (Prometheus counters) | |

**Exception:** The gateway currently imports `LangChainLLMClient`, `OpenAIEmbedder`, and `HybridRetriever` directly from infrastructure. This is a known shortcut for v1 -- these should be injected via the DI container in a future refactor. The `infrastructure/ai/graph` import is done via lazy `import` inside the function body.

---

## Key Source Files

| File | Role |
| ---- | ---- |
| `ai/gateway.py` | Single entry point: `chat_with_agent()` |
| `ai/types.py` | `ChatInput`, `ChatResult`, `ToolDef`, `ToolCallResult`, `AgentLoopResult` |
| `ai/context/history.py` | Conversation history loader + staleness hint |
| `ai/context/memory.py` | Key facts context loader |
| `ai/context/prompts.py` | System prompt builder |
| `ai/context/checkpoint.py` | Token-budget checkpoint summarization |
| `ai/context/i18n.py` | Multi-language message lookup |
| `ai/concurrency.py` | Redis-backed thread locking |
| `ai/tools/search_documents.py` | RAG search tool definition + runner |
| `ai/tools/escalate_question.py` | Question escalation tool definition + runner |
| `ai/tools/save_key_fact.py` | Save key fact tool definition + runner |
| `ai/tools/remove_key_fact.py` | Remove key fact tool definition + runner |
| `ai/utils/sender.py` | Sender resolution (channel user -> Contact entity) |
| `infrastructure/ai/graph.py` | LangGraph state graph (ONLY langgraph import site) |
