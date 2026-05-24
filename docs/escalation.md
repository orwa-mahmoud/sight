# Escalation

The differentiating feature. When the AI doesn't know an answer, it
doesn't bluff — it submits a `Question` and the asker is told the owner
will follow up. The owner sees a clean inbox, replies, and the resolution
relays back through the original channel.

## State machine

```text
                  ┌──────────────────┐
   AI tool        │                  │   owner reply
   submits   ───▶ │   SUBMITTED      │ ───────────────▶ ┌─────────────┐
                  │                  │                  │  RESOLVED   │
                  └──────────────────┘                  └─────────────┘
                          │
                          │ owner closes (spam / N/A)
                          ▼
                  ┌──────────────────┐
                  │     CLOSED       │
                  └──────────────────┘
```

Transitions are enforced by domain methods. `Question.resolve()` raises
`InvalidOperationError` if status isn't `SUBMITTED` — no double-reply,
no reopening a closed question without an explicit `reopen()` method
(reserved for v2).

## Why a single `Question` table

Three options were on the table:

1. **One row per question with status enum** ← chosen
2. **Status as separate rows (`question_events` log)**
3. **One table per channel (`whatsapp_questions`, `telegram_questions`)**

Option 1 is the right scope for v1:
- Simple to query for the inbox
- Single source of truth — no event-log replay to determine current state
- Channel-agnostic — `channel` is a value, not a schema dimension
- Easy to migrate to event-sourced (option 2) later by adding a log
  table that snapshots into the questions table on each transition

Option 2 is overkill for v1. Option 3 would have created N parallel
inbox queries — wrong abstraction.

## Domain shape

```python
@dataclass(eq=False, kw_only=True)
class Question(BaseEntity):
    tenant_id: UUID
    conversation_id: UUID | None    # set when escalation arose from chat
    channel: ConversationChannel    # whatsapp | telegram | email | ...
    asker_name: str | None          # captured during conversation if known
    asker_contact: str | None       # phone / email / handle
    question_text: str
    ai_answer_attempt: str | None   # what the AI tried before giving up
    status: QuestionStatus
    owner_reply: str | None
    replied_by_user_id: UUID | None
    replied_at: datetime | None
```

The `ai_answer_attempt` field is doing real work — it lets the owner see
*why* the AI escalated. Sometimes the answer is "actually that response
was fine, the AI was just under-confident" and the owner can confirm.
Sometimes it's "no, here's the real answer," and the AI learns from the
reply in v2.

## Lifecycle from asker's perspective

1. Asker (WhatsApp): "What's your return policy?"
2. AI runs RAG, gets some chunks, decides confidence too low (Phase 8
   wires this routing logic into the agent loop)
3. AI submits via the `submit_question` tool → `POST /api/v1/questions`
   on behalf of the tenant → `Question(status=SUBMITTED)` row
4. AI replies to asker: *"Let me check with the team and get back to you."*
5. Owner opens dashboard → escalation inbox → sees the question with
   `ai_answer_attempt` shown for context
6. Owner taps Reply, types answer, submits → `POST /api/v1/questions/{id}/reply`
7. `Question.resolve()` fires `QuestionResolved` event
8. Phase 8: channels adapter subscribes to `QuestionResolved`, sends
   the reply via WhatsApp / Telegram with `notify_user` tool semantics

## API surface

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `POST` | `/api/v1/questions` | owner | Submit (agent tool or test) |
| `GET` | `/api/v1/questions?status=submitted` | owner | Inbox |
| `GET` | `/api/v1/questions/{id}` | owner | Detail (cross-tenant blocked) |
| `POST` | `/api/v1/questions/{id}/reply` | owner | Resolve with reply |
| `POST` | `/api/v1/questions/{id}/close` | owner | Dismiss without reply |

Phase 8 adds a channel-webhook-callable internal endpoint that submits
under a tenant scope derived from the channel's verified signature,
bypassing JWT.

## Tenant isolation

Every operation that touches a `Question` checks `question.tenant_id ==
caller_tenant_id` before any state change. Tested in
`tests/integration/test_questions_flow.py::test_cross_tenant_access_forbidden`.
