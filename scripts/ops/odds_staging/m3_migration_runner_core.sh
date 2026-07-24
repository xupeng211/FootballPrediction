#!/usr/bin/env bash
# lifecycle: permanent
# Internal runner core; wrappers own identity validation and migration allowlists.
set -euo pipefail
container= database= file= checksum= pause_seconds=0
while [[ $# -gt 0 ]]; do case "$1" in --container) container="$2"; shift 2;; --database) database="$2"; shift 2;; --file) file="$2"; shift 2;; --checksum) checksum="$2"; shift 2;; --pause-seconds) pause_seconds="$2"; shift 2;; *) echo RUNNER_ERROR_invalid_argument >&2; exit 2;; esac; done
base_file="$(basename "$file")"
[[ "$container" =~ ^[A-Za-z0-9_.-]+$ && "$database" =~ ^[A-Za-z0-9_]+$ && "$base_file" =~ ^V[0-9]+\.[0-9]+__[A-Za-z0-9_]+\.sql$ && "$checksum" =~ ^[0-9a-f]{64}$ && "$pause_seconds" =~ ^[0-8]$ && -f "$file" ]] || { echo RUNNER_ERROR_invalid_identity_or_file >&2; exit 2; }
version="${base_file%%__*}"
runner_file="m3-runner-${base_file}.${RANDOM}.$$"
docker cp "$file" "$container:/tmp/${runner_file}"
set +e
out="$(docker exec -i "$container" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -v version="$1" -v filename="$2" -v checksum="$3" -v pause_seconds="$4" -U "$POSTGRES_USER" -d "$POSTGRES_DB"' sh "$version" "$runner_file" "$checksum" "$pause_seconds" 2>&1 <<'SQL'
\set VERBOSITY verbose
SELECT pg_backend_pid() AS runner_pid, pg_try_advisory_lock(731642941) AS lock_acquired \gset
\echo RUNNER_PID_LOCK :runner_pid
\if :lock_acquired
SELECT pg_backend_pid() AS critical_pid \gset
\echo RUNNER_PID_CRITICAL :critical_pid
SELECT EXISTS (SELECT 1 FROM odds_staging_schema_migrations WHERE version=:'version') AS has_record \gset
\if :has_record
SELECT (SELECT sha256_checksum FROM odds_staging_schema_migrations WHERE version=:'version') = :'checksum' AS checksum_matches \gset
\if :checksum_matches
\echo RUNNER_ALREADY_APPLIED :version
\else
\echo RUNNER_CHECKSUM_CONFLICT :version
SELECT 1 / 0;
\endif
\else
SELECT pg_sleep(:'pause_seconds');
BEGIN;
SET ROLE fp_m3_sandbox_migrator;
\i /tmp/:filename
INSERT INTO odds_staging_schema_migrations (version,filename,sha256_checksum,applied_by,execution_duration_ms) VALUES (:'version',:'filename',:'checksum',current_user,0);
COMMIT;
\echo RUNNER_APPLIED :version
\endif
SELECT pg_backend_pid() AS release_pid \gset
\echo RUNNER_PID_RELEASE :release_pid
SELECT pg_advisory_unlock(731642941);
\else
\echo RUNNER_LOCK_BUSY
SELECT 1 / 0;
\endif
SQL
)"; rc=$?
set -e
docker exec "$container" rm -f "/tmp/${runner_file}" >/dev/null 2>&1 || true
if [[ $rc -eq 0 && "$out" == *"ERROR:"* ]]; then rc=3; fi
printf '%s\n' "$out"
exit "$rc"
