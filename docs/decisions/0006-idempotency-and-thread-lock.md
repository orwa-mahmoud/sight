# 0006 — Webhook idempotency (Redis fast-path + durable DB backstop) + per-thread locking

**Status:** Accepted

## Context

Meta and Telegram deliver webhooks **at least once**, so the same message can
arrive twice — and answering twice means double LLM cost and a confused user.
Separately, two messages on the same thread arriving nearly simultaneously could
interleave the agent loop and corrupt conversation order.

## Decision

Two layers of de-duplication plus a locking and a persistence rule:

- **Fast path (Redis):** before doing any work, check a Redis key for the provider
  message id (`is_duplicate_message`, `SET NX`); skip if seen. Cheap, catches the
  vast majority of redeliveries with no DB hit.
- **Durable backstop (Postgres):** the inbound message row carries the provider's
  id (`messages.provider_message_id` — WhatsApp `wamid`, Telegram `chat_id:message_id`)
  under a **partial unique index** `(conversation_id, provider_message_id) WHERE
  provider_message_id IS NOT NULL`. The save uses `INSERT … ON CONFLICT DO NOTHING`
  (`insert_if_new`); a conflict means "already handled" → the turn is skipped. The
  index lock serializes even concurrent, uncommitted duplicate inserts, so two
  webhooks racing can't both win (a `SELECT`-then-insert check could not do this).
- **Persist-before-process:** the inbound message is committed *before* the agent
  runs. If the agent then fails (LLM timeout, etc.) the asker's message is already
  in the thread — a visible unanswered turn, not a silent drop — and their next
  message carries it forward. (Committing ends the transaction, so the
  transaction-local RLS scope is re-applied immediately after.)
- **Per-thread lock:** a Redis lock keyed by thread id serializes concurrent
  messages on one thread.
- **Graceful degradation:** if Redis is down, the fast path and lock fall open —
  but the Postgres unique index still guarantees no duplicate is processed twice.

## Consequences

**Good:** exactly-once processing that **survives a Redis outage** (the DB is the
source of truth for dedup), no double-billing on redelivery, and failed turns are
**recoverable by the human resending** rather than lost. No status/state-machine
or background worker is needed for channel messages — the human + conversation
history is the retry.

**Costs / notes:** dedup is scoped per conversation (which already encodes
tenant + channel + contact), not a global `(tenant, channel, message_id)` — the
provider id is unique within a conversation, which is the natural grain. API /
dashboard messages have no provider id (NULL), so they are never de-duplicated,
which is correct (each is a distinct user action). A genuinely abandoned failed
turn (the human never resends) is left unanswered with no proactive nudge —
acceptable for v1; a future owner-side "stuck conversations" view could surface it.
