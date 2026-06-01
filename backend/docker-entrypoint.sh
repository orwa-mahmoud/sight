#!/bin/sh
# Container entrypoint: apply pending DB migrations, then run the given command.
# Keeping migrations here (rather than in CMD) means `docker-compose up` brings a
# fresh database to the current schema with no manual step.
set -e

echo "==> Applying database migrations (alembic upgrade head)"
uv run alembic upgrade head

echo "==> Starting: $*"
exec "$@"
