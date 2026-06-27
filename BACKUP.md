# Backup & restore

The Postgres `pgdata` volume holds **everything** — tenants, conversations,
documents, chunks/embeddings, questions, key facts, usage, encrypted credentials.
Lose it and you lose all tenants. Set up backups before you have real data.

> The `ENCRYPTION_KEY` is **not** in the database — it's in your environment.
> A database backup is useless without it. Back up the key separately (a secrets
> manager), and test that pairing in a restore drill.

## Back up (logical dump — recommended)

`pg_dump` produces a portable, compressed snapshot:

```bash
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U postgres -d "$POSTGRES_DB" -Fc \
  > "backup-$(date +%F).dump"
```

Copy it **off the host** (object storage / another machine). Keep a rotation
(e.g. 7 daily + 4 weekly). Automate with cron:

```cron
0 3 * * * cd /opt/sight && docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_dump -U postgres -d sight_db -Fc > /backups/sight-$(date +\%F).dump
```

## Restore

```bash
# Into a running, EMPTY database (drops + recreates objects):
docker compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U postgres -d "$POSTGRES_DB" --clean --if-exists < backup-YYYY-MM-DD.dump
```

If you restore onto a fresh stack, bring up Postgres first, restore, then start
the backend (it will see the schema already at head).

## Volume snapshot (alternative)

For a physical copy of the whole volume (stop the DB first for consistency):

```bash
docker compose -f docker-compose.prod.yml stop postgres
docker run --rm -v sight_pgdata:/data -v "$PWD":/out alpine \
  tar czf /out/pgdata-$(date +%F).tgz -C /data .
docker compose -f docker-compose.prod.yml start postgres
```

(Confirm the volume name with `docker volume ls`.)

## Redis

Redis holds only ephemeral state (idempotency keys, thread locks) — it does **not**
need backing up. On restart, dedup/locks simply start fresh.

## Restore drill

Backups you haven't restored aren't backups. Quarterly: restore the latest dump
into a throwaway stack with your `ENCRYPTION_KEY`, log in, and confirm a tenant's
documents and conversations are intact.
