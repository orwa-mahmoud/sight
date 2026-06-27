#!/usr/bin/env bash
# Reset the demo instance to a clean slate — truncates all tenant data while
# preserving the schema and migration history. Intended for a nightly cron on a
# public "try it" demo. Re-seed afterwards (register an owner + upload the
# sample KB in backend/eval/fixtures/, or your own seeding step).
#
# Usage:  ./scripts/reset_demo.sh [compose-file]
#   compose-file defaults to docker-compose.prod.yml
set -euo pipefail

COMPOSE_FILE="${1:-docker-compose.prod.yml}"
DB="${POSTGRES_DB:-sight_db}"

# Order/CASCADE handles FKs; RESTART IDENTITY resets sequences. alembic_version
# is intentionally left untouched so the schema stays at head.
TABLES="questions, token_usages, messages, conversations, chunks, documents, \
invitations, user_tenants, tenant_configs, key_facts, contacts, telegram_phones, \
users, tenants"

echo "==> Resetting demo data in '$DB' (schema preserved)…"
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  psql -U postgres -d "$DB" -v ON_ERROR_STOP=1 \
  -c "TRUNCATE TABLE ${TABLES} RESTART IDENTITY CASCADE;"

echo "✅ demo reset. Re-seed: register an owner, add an LLM key, upload the sample KB."
