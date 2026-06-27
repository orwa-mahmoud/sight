# 0001 — Hexagonal DDD + CQRS over active-record/MVC

**Status:** Accepted

## Context

Sight is an AI app, and AI apps rot fast: framework calls (LangChain,
HTTP clients, ORMs) leak into business logic until the "agent" is inseparable
from the plumbing. I wanted the domain — tenants, conversations, escalation,
documents, billing — to stay testable and framework-free as the AI stack churns.

## Decision

Strict **ports-and-adapters (hexagonal)** layering with **CQRS**:

```
drivers/ → application/ → domain/ ← infrastructure/
```

- `domain/` is pure: rich entities with invariants + domain events, **zero** IO,
  zero framework imports. Dependencies are expressed as Python `Protocol` ports
  (e.g. `LLMClientPort`, `RetrieverPort`, `PasswordHasher`).
- `application/` holds use cases as frozen command/query handlers; it depends on
  ports, never concrete adapters.
- `infrastructure/` implements the ports (Postgres, LangChain, channels).
- `drivers/` (FastAPI routes, webhooks) translate transport ↔ commands.

Boundaries are enforced, not aspirational — see the forbidden-import table in
[backend/CLAUDE.md](../../backend/CLAUDE.md) and the grep checks in CI/docs.

## Consequences

**Good:** the domain is unit-testable with no DB/LLM; swapping an LLM provider or
the web framework touches one layer; the code reads as the business, not the
framework. It's the structure a reviewer can navigate in minutes.

**Costs:** more files and indirection than a Flask/Django CRUD app; a learning
curve for contributors new to DDD; some boilerplate (DTO mapping, ports). Two
deliberate composition-root exceptions exist — the `UnitOfWork` wires concrete
repos, and the AI gateway wires its adapters — documented rather than hidden.

**Rejected alternatives:** active-record/MVC (fast to start, but business logic
ends up in views/models and the AI plumbing bleeds everywhere); a service layer
over an ORM without a pure domain (better, but still couples invariants to the
ORM).
