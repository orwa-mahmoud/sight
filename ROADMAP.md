# Roadmap

Direction, not promises. This reflects what I think matters next; priorities
shift with feedback and contributions. Want something here sooner, or something
not listed? Open a [Discussion](https://github.com/orwa-mahmoud/sight/discussions)
or an issue.

## Shipped (v0.1)

- Multi-tenant core: tenants, users, owner registration, invitations, super-admin
- AI agent: LangGraph per-turn loop, tools (search / escalate / key facts)
- Hybrid RAG: vector (HNSW) + BM25 + RRF, per-tenant knowledge base
- Channels: WhatsApp Cloud API, Telegram, dashboard chat
- Escalation inbox with relay-back replies
- Per-tenant LLM config + token/cost accounting
- Tenant isolation: app-layer + Postgres RLS (opt-in)
- Bilingual dashboard (EN/AR + RTL), light/dark
- Docker Compose, CI, load-test smoke

## Next — hardening & operability (v0.2)

The focus is making the "self-hosted, production-ready" claim fully true.

- ~~Security backlog: prompt-injection hardening on key facts, encrypt the
  Telegram webhook secret, re-auth on password change, durable DB-backed webhook
  idempotency, encryption-key rotation~~ — **done** (see [SECURITY.md](SECURITY.md))
- Server-side token revocation on logout (jti blocklist or short-TTL + refresh)
- RLS **on by default** + exercised in CI under a NOBYPASSRLS role
- ~~Deployment + backup/restore docs~~ — **done** ([DEPLOYMENT.md](DEPLOYMENT.md),
  [BACKUP.md](BACKUP.md)); still to do: container healthchecks + resource limits
- A hosted demo with a seeded demo tenant — tooling is in place
  ([`scripts/reset_demo.sh`](scripts/reset_demo.sh) + [DEPLOYMENT.md §6](DEPLOYMENT.md));
  still to do: stand up the live instance
- **Publish** RAG/agent eval quality numbers in the README — the harness already
  ships (`make eval` offline, `make eval-db` over the real retriever)

## Then — product depth (v0.3)

- Per-user tenant switcher (multi-tenant membership is already in the data model)
- Email delivery for invitation links
- Streaming agent responses in the dashboard chat
- More channels (Slack, web widget) via the existing adapter pattern
- Bulk actions in the dashboard (e.g. documents)

## Exploring — bigger bets

- Background worker via the (already-present, dormant) outbox: async ingestion,
  notifications, webhook dead-letter
- Reranking with a real cross-encoder (the port already exists)
- Eval-gated prompt/retrieval changes in CI
- Analytics: answer rate, escalation rate, deflection per tenant

See [docs/decisions/](docs/decisions/) for the reasoning behind the current
architecture.
