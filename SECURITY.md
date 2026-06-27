# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems.

- Preferred: open a private report via **GitHub → Security → Report a
  vulnerability** (Private Vulnerability Reporting) on this repository.
- Or email **orwa.mahmoud.uae@gmail.com** with `[sight security]` in the
  subject.

Include what you found, how to reproduce it, and the impact. I aim to acknowledge
within 72 hours and to agree on a disclosure timeline once the issue is
confirmed. Please give a reasonable window to fix before public disclosure.

## Supported versions

This is a young project; security fixes target the `main` branch and the latest
tagged release.

## Security model (what's enforced today)

- **Tenant isolation is defense-in-depth.** Every query filters by `tenant_id`
  at the application layer, and Postgres **Row-Level Security** policies are a
  second backstop (fail-closed predicate). RLS is implemented but inert under the
  default superuser role — see [backend/docs/TENANT_ISOLATION.md](backend/docs/TENANT_ISOLATION.md)
  for how to activate it.
- **`tenant_id` is never trusted from the client** — it is resolved from the
  authenticated JWT or the webhook URL path.
- **Auth is cookie-based.** Login/register set an httpOnly `sight_token`
  cookie; the SPA never stores the JWT in JS (no localStorage → no XSS token
  theft). A `Bearer` token is also accepted for programmatic clients.
- **Secrets at rest are encrypted** (Fernet) — tenant LLM/embedding keys and
  channel credentials.
- **Webhook authenticity** — WhatsApp uses HMAC-SHA256 over the body; both
  channels use constant-time comparisons.

## Hardening status

Recently addressed:

- **Prompt injection via key facts** — facts are rendered inside `<known_facts>`
  delimiters with control characters stripped and values length-capped, so a
  crafted value can't pose as an instruction (`ai/context/memory.py`).
- **Telegram webhook secret** is now encrypted at rest like every other secret,
  with a backfill migration for existing rows.
- **Password change requires re-authentication** — the current password must be
  supplied and verified.
- **Encryption-key rotation** — set the new key in `ENCRYPTION_KEY` and the
  previous one(s) in `ENCRYPTION_KEY_FALLBACKS`; old ciphertext keeps decrypting
  until you re-encrypt and drop the fallback. A botched rotation is surfaced rather
  than silent: the app runs a **startup self-check** that refuses to boot if any
  configured key is malformed, and every failed decrypt at runtime increments the
  `sight_crypto_decrypt_failures_total` metric — alert on it, since each failure
  means a secret read back as `""` (e.g. webhook signature 403s).
- **Durable webhook idempotency** — inbound messages carry the provider id under a
  partial unique index `(conversation_id, provider_message_id)` and save via
  `INSERT … ON CONFLICT DO NOTHING`, so a redelivered webhook is never processed
  twice even if Redis is down. The inbound message is also committed *before* the
  agent runs, so a failed turn leaves a visible unanswered message rather than
  silently dropping it.

Still on the backlog (tracked in [ROADMAP.md](ROADMAP.md)):

- No server-side token revocation on logout (JWT valid until expiry); a jti
  blocklist or short-TTL + refresh grant is planned.

Run `docker compose down -v` only when you intend to wipe all data — the `pgdata`
volume holds every tenant's data. See backup guidance in `DEPLOYMENT.md`.
