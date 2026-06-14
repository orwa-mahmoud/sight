# Deployment

How to run frontdesk for real, beyond `docker compose up` on a laptop. For local
dev see the [README](README.md#quick-start); for backups see [BACKUP.md](BACKUP.md).

## What you're deploying

One public surface: the **frontend** container (nginx) on port 80/443. It serves
the SPA and reverse-proxies `/api` and `/webhooks` to the backend over the
internal Docker network. Postgres and Redis stay private. Inbound channel
webhooks (WhatsApp/Telegram) reach the backend through that same nginx, so the
host must be reachable from the internet over HTTPS for channels to work.

## 1. Prerequisites

- A host with Docker + Docker Compose v2.
- A domain name pointing at the host (channels require a public HTTPS URL).
- TLS — terminate at an external reverse proxy / load balancer (Caddy, Traefik,
  nginx, or your cloud LB) in front of the frontend container. Channel webhooks
  must be HTTPS.

## 2. Secrets & environment

```bash
cp .env.docker.example .env.docker          # or: make setup (generates the two secrets)
```

Set, at minimum:

| Var | How |
|---|---|
| `JWT_SECRET_KEY` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `ENCRYPTION_KEY` | `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `POSTGRES_PASSWORD` | a strong random value |
| `APP_ENV` | `production` |
| `CORS_ORIGINS` | your public origin(s) |

**Never commit `.env.docker`.** `ENCRYPTION_KEY` protects tenant secrets at rest;
if you lose it, encrypted LLM/channel credentials become unrecoverable — store it
in a secrets manager and back it up separately from the database.

## 3. Bring it up

```bash
docker compose -f docker-compose.prod.yml up -d --build
```

This adds, over the dev compose: private Postgres/Redis (no host ports), restart
policies, healthchecks on every service, and memory limits. Migrations run
automatically on backend start (`docker-entrypoint.sh`).

Verify:

```bash
docker compose -f docker-compose.prod.yml ps          # all healthy
curl -fsS http://localhost/api/v1/health || true       # via nginx
```

## 4. Activate RLS (recommended for multi-tenant prod)

Row-Level Security ships implemented but **inert under the default `postgres`
superuser** (which bypasses RLS). To turn the database-level backstop on:

```bash
# 1. Create the least-privilege app role (run once, as the DB owner):
docker compose -f docker-compose.prod.yml exec -T postgres \
  psql -U postgres -d "$POSTGRES_DB" -v app_password="'a-strong-password'" \
  -f - < backend/scripts/create_app_role.sql

# 2. Point the app at it (migrations still run as postgres via DATABASE_URL_SYNC):
#    in .env.docker
DATABASE_URL=postgresql+asyncpg://frontdesk_app:a-strong-password@postgres:5432/${POSTGRES_DB}
```

Then `up -d` again. Validate each flow under the new role before going live — a
new query that reads an RLS table without first setting tenant scope will
(correctly) see nothing. Background and rationale:
[backend/docs/TENANT_ISOLATION.md](backend/docs/TENANT_ISOLATION.md) and
[docs/decisions/0003](docs/decisions/0003-tenant-isolation-app-plus-rls.md).

> RLS is already proven in CI: `tests/integration/test_rls_enforcement.py`
> provisions a real `NOBYPASSRLS` role and asserts cross-tenant queries return
> nothing — it runs on every PR.

## 5. Connect channels

Per tenant, in Settings → Channels (see
[backend/docs/CHANNEL_INTEGRATION.md](backend/docs/CHANNEL_INTEGRATION.md)):

- **WhatsApp**: set the webhook to `https://<your-domain>/webhooks/<tenant_id>/whatsapp`
  with the verify token + app secret you configure in Settings.
- **Telegram**: set the bot webhook to `https://<your-domain>/webhooks/<tenant_id>/telegram`.

## 6. A public demo (optional)

To run a try-it demo:

1. Deploy as above on a small instance (Railway / Render / Fly / a VPS).
2. Register an owner, add an LLM API key in Settings, and upload a few KB docs —
   the `backend/eval/fixtures/*.md` files make a good sample knowledge base.
3. Reset nightly so the demo stays clean — schedule
   [`scripts/reset_demo.sh`](scripts/reset_demo.sh) via cron (it truncates tenant
   data, preserving schema).
4. Put the URL in the README (replace `_Live demo: coming soon_`).

## 7. Operate

- **Backups**: see [BACKUP.md](BACKUP.md). Do this before you have real tenants.
- **Logs**: `docker compose -f docker-compose.prod.yml logs -f backend`
  (structured JSON via structlog; each request carries a request id).
- **Metrics**: Prometheus metrics are exposed at `/metrics` (proxied by nginx).
- **Updates**: `git pull && docker compose -f docker-compose.prod.yml up -d --build`
  — migrations apply on start.
- **Scaling**: turns are stateless (no LangGraph checkpointer), so the backend
  scales horizontally behind the proxy; Postgres + Redis are the shared state.
