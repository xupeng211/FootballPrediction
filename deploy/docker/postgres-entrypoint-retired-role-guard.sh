#!/bin/sh

set -eu

retired_role='claude_reader'
postgres_data_dir="${PGDATA:-/var/lib/postgresql/data}"

# POSTGRES_USER is interpreted by the official image before any initdb.d script
# runs.  A stale DB_USER=claude_reader must therefore be rejected here, before
# initdb can recreate the retired identity as a LOGIN bootstrap owner.
if [ ! -s "${postgres_data_dir}/PG_VERSION" ] && [ "${POSTGRES_USER:-}" = "${retired_role}" ]; then
    printf '%s\n' \
        'ERROR: fresh PostgreSQL bootstrap refuses retired POSTGRES_USER=claude_reader' \
        >&2
    exit 78
fi

exec /usr/local/bin/docker-entrypoint.sh "$@"
