#!/bin/bash
set -euo pipefail

if [ "${RUN_DB_MIGRATIONS:-1}" = "1" ]; then
  echo "[entrypoint] Running Alembic migrations..."
  alembic upgrade head
  echo "[entrypoint] Database schema is up to date."
else
  echo "[entrypoint] Skipping Alembic migrations (RUN_DB_MIGRATIONS=${RUN_DB_MIGRATIONS})."
fi

exec "$@"
