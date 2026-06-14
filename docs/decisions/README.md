# Architecture Decision Records

Short records of the non-obvious choices in frontdesk — the *why* behind the
structure, and the trade-offs accepted. Format: Context → Decision →
Consequences. Newest decisions supersede older ones explicitly.

| # | Decision | Status |
|---|----------|--------|
| [0001](0001-hexagonal-ddd-cqrs.md) | Hexagonal DDD + CQRS over active-record/MVC | Accepted |
| [0002](0002-langgraph-per-turn-isolated.md) | LangGraph runs per-turn, isolated to one file; DB is the source of truth | Accepted |
| [0003](0003-tenant-isolation-app-plus-rls.md) | Tenant isolation: app-layer filters **and** Postgres RLS (opt-in) | Accepted |
| [0004](0004-per-tenant-llm-config.md) | Per-tenant LLM config in the database, not env | Accepted |
| [0005](0005-cookie-auth-sliding-session.md) | httpOnly cookie auth + sliding session (no refresh-token grant yet) | Accepted |
| [0006](0006-idempotency-and-thread-lock.md) | Redis for webhook idempotency + per-thread locking | Accepted (with known caveat) |
