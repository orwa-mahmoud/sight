# 0004 — Per-tenant LLM config in the database, not env

**Status:** Accepted

## Context

A multi-tenant product can't share one global LLM key from `.env`: tenants want
their own provider, model, and billing, and the platform operator shouldn't
foot every tenant's token bill. Config also has to change at runtime without a
redeploy.

## Decision

LLM and embedding configuration live per-tenant in the `tenant_configs` table:
provider, model, API key, embedding model/key, plus bot personality. They are:

- **encrypted at rest** (Fernet, `enc:` prefix) for the secret fields;
- resolved at request time through a **cached factory**
  (`TenantLLMClientFactory`) so we don't rebuild a client per turn;
- **invalidated immediately** when the owner updates settings
  (`invalidate_tenant_llm_client`), otherwise a stale client could serve for up
  to the cache TTL.

Token usage is recorded per call with `Decimal(18,8)` cost, segmented by
source/channel, with pricing computed in the domain.

## Consequences

**Good:** true tenant-level isolation of cost and model choice; owners change
provider/model live; secrets never sit in plaintext config; cost is auditable.

**Costs:** a cache-invalidation path to maintain; embedding **dimensions** are
currently fixed at 1536 across three sites while the model is editable — changing
to a different-dimension model needs a migration/re-ingest (tracked). Encryption
key has no rotation mechanism yet (tracked).
