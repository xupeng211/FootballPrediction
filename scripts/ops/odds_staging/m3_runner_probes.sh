#!/usr/bin/env bash
# lifecycle: permanent
# REV3-only disposable migration-runner evidence. Never reads project .env.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
CORE="$ROOT/scripts/ops/odds_staging/m3_migration_runner_core.sh"
BASE=(V26.8__create_odds_historical_staging_contract.sql V26.9__add_odds_historical_observation_fingerprint.sql)
die(){ echo "RUNNER_PROBE_FAIL $*" >&2; exit 1; }
scalar(){ printf '%s\n' "$1" | docker exec -i "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -At -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"'; }
run_file(){ local f="$1" pause="$2"; bash "$CORE" --container "$name" --database "$database" --file "$dir/$f" --checksum "$(sha256sum "$dir/$f" | awk '{print $1}')" --pause-seconds "$pause"; }
inventory(){ [[ "$(scalar "SELECT (SELECT count(*) FROM odds_historical_import_runs),(SELECT count(*) FROM odds_historical_source_files),(SELECT count(*) FROM odds_historical_staging_observations),(SELECT count(*) FROM odds_historical_quarantine),(SELECT count(*) FROM odds_historical_staging_observations WHERE business_fingerprint IS NULL)")" == '0|0|0|0|0' ]] || die business_rows; [[ "$(scalar "SELECT count(*) FROM pg_constraint WHERE conrelid='odds_historical_staging_observations'::regclass AND to_regclass('matches') IS NOT NULL AND confrelid=to_regclass('matches')")" == 0 ]] || die matches_fk; }
start(){
  probe="$1"; nonce="$(date -u +%s)_$RANDOM"; project="fp_m3_runner_probe_${probe}_${nonce}"; database="fp_m3_runner_probe_${probe}_${nonce}"; name="${project}-m3-runner-probe-postgres-1"; net="${project}_default"; dir="$(mktemp -d /tmp/m3-runner-probe.XXXXXX)"; chmod 700 "$dir"
  [[ "$project" =~ ^fp_m3_runner_probe_(rollback|checksum|lock)_[0-9]+_[0-9]+$ && "$database" =~ ^fp_m3_runner_probe_ ]] || die identity
  cleanup(){ docker rm -f "$name" >/dev/null 2>&1 || true; docker network rm "$net" >/dev/null 2>&1 || true; rm -rf "$dir"; }; trap cleanup EXIT INT TERM
  umask 077; printf 'POSTGRES_DB=%s\nPOSTGRES_USER=fp_m3_sandbox_owner\nPOSTGRES_PASSWORD=%s\n' "$database" "$(openssl rand -hex 32)" > "$dir/env"; chmod 600 "$dir/env"
  docker network create --label com.footballprediction.scope=m3-d4d-b1-runner-probe --label com.footballprediction.probe="$probe" --label com.footballprediction.production=false --label com.footballprediction.staging=false "$net" >/dev/null
  docker run -d --name "$name" --network "$net" --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,size=256m --env-file "$dir/env" --label com.footballprediction.scope=m3-d4d-b1-runner-probe --label com.footballprediction.probe="$probe" --label com.footballprediction.production=false --label com.footballprediction.staging=false postgres:15-alpine >/dev/null
  for _ in $(seq 1 30); do docker exec "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1 && break; sleep 1; done
  docker exec "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null || die postgres_unavailable
  docker exec -i "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
CREATE ROLE fp_m3_sandbox_migrator NOLOGIN NOINHERIT;
CREATE TABLE odds_staging_schema_migrations (version TEXT PRIMARY KEY, filename TEXT NOT NULL UNIQUE, sha256_checksum CHAR(64) NOT NULL, applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW(), applied_by TEXT NOT NULL, execution_duration_ms INTEGER NOT NULL CHECK (execution_duration_ms >= 0));
ALTER TABLE odds_staging_schema_migrations OWNER TO fp_m3_sandbox_migrator;
GRANT USAGE,CREATE ON SCHEMA public TO fp_m3_sandbox_migrator;
SQL
  for f in "${BASE[@]}"; do cp "$ROOT/database/migrations/$f" "$dir/$f"; [[ "$(sha256sum "$dir/$f" | awk '{print $1}')" == "$(sha256sum "$ROOT/database/migrations/$f" | awk '{print $1}')" ]] || die base_checksum; run_file "$f" 0 >/dev/null || die base_apply; done
  [[ "$(scalar 'SELECT count(*) FROM odds_staging_schema_migrations')" == 2 ]] || die base_ledger; inventory
}
rollback(){
  start rollback; f=V99.1__intentional_failure_probe.sql
  cat >"$dir/$f" <<'SQL'
CREATE TABLE m3_failed_migration_partial_probe (id integer PRIMARY KEY);
SELECT 1 / 0;
SQL
  set +e; out="$(run_file "$f" 0 2>&1)"; rc=$?; set -e; [[ $rc -ne 0 && "$out" == *22012* ]] || die "rollback_sqlstate exit=$rc output=${out//$'\n'/ }"
  [[ "$(scalar "SELECT count(*) FROM pg_class WHERE relname='m3_failed_migration_partial_probe'")" == 0 && "$(scalar "SELECT count(*) FROM odds_staging_schema_migrations WHERE version='V99.1'")" == 0 && "$(scalar 'SELECT count(*) FROM odds_staging_schema_migrations')" == 2 ]] || die rollback_state; inventory
  cat >"$dir/$f" <<'SQL'
CREATE TABLE m3_failed_migration_partial_probe (id integer PRIMARY KEY);
SQL
  run_file "$f" 0 >/dev/null; before="$(scalar 'SELECT count(*) FROM odds_staging_schema_migrations')"; run_file "$f" 0 | grep -q RUNNER_ALREADY_APPLIED; [[ "$(scalar 'SELECT count(*) FROM odds_staging_schema_migrations')" == "$before" ]] || die rerun_delta; inventory
  echo "PROBE rollback project=$project database=$database failure_exit=$rc sqlstate=22012 ledger=2_to_3 resume=PASS rerun=noop PASS"; cleanup; trap - EXIT INT TERM
}
checksum(){
  start checksum; f=V99.2__checksum_probe.sql
  cat >"$dir/$f" <<'SQL'
CREATE TABLE m3_checksum_probe_applied (id integer PRIMARY KEY);
SQL
  original="$(sha256sum "$dir/$f" | awk '{print $1}')"; run_file "$f" 0 >/dev/null; applied_at="$(scalar "SELECT applied_at FROM odds_staging_schema_migrations WHERE version='V99.2'")"
  cat >"$dir/$f" <<'SQL'
CREATE TABLE m3_checksum_probe_applied (id integer PRIMARY KEY);
CREATE TABLE m3_checksum_probe_should_never_execute (id integer PRIMARY KEY);
SQL
  drifted="$(sha256sum "$dir/$f" | awk '{print $1}')"; [[ "$original" != "$drifted" ]] || die no_drift
  set +e; out="$(run_file "$f" 0 2>&1)"; rc=$?; set -e; [[ $rc -ne 0 && "$out" == *RUNNER_CHECKSUM_CONFLICT* ]] || die "checksum_conflict exit=$rc output=${out//$'\n'/ }"
  [[ "$(scalar "SELECT count(*) FROM pg_class WHERE relname='m3_checksum_probe_should_never_execute'")" == 0 && "$(scalar "SELECT sha256_checksum FROM odds_staging_schema_migrations WHERE version='V99.2'")" == "$original" && "$(scalar "SELECT applied_at FROM odds_staging_schema_migrations WHERE version='V99.2'")" == "$applied_at" ]] || die checksum_state; inventory
  echo "PROBE checksum project=$project original=$original drifted=$drifted exit=$rc category=checksum-conflict sentinel=0 PASS"; cleanup; trap - EXIT INT TERM
}
lock(){
  start lock; f=V99.3__advisory_lock_probe.sql
  cat >"$dir/$f" <<'SQL'
CREATE TABLE m3_advisory_lock_probe_applied (id integer PRIMARY KEY);
SQL
  run_file "$f" 6 >"$dir/a.out" 2>&1 & a_proc=$!; sleep 1; set +e; out_b="$(run_file "$f" 0 2>&1)"; rc_b=$?; wait "$a_proc"; rc_a=$?; set -e; out_a="$(<"$dir/a.out")"
  [[ $rc_a -eq 0 && $rc_b -ne 0 && "$out_b" == *RUNNER_LOCK_BUSY* ]] || die "lock_behavior A=$rc_a B=$rc_b out_a=${out_a//$'\n'/ } out_b=${out_b//$'\n'/ }"
  p1="$(printf '%s\n' "$out_a" | awk '/RUNNER_PID_LOCK/{print $2}')"; p2="$(printf '%s\n' "$out_a" | awk '/RUNNER_PID_CRITICAL/{print $2}')"; p3="$(printf '%s\n' "$out_a" | awk '/RUNNER_PID_RELEASE/{print $2}')"; pb="$(printf '%s\n' "$out_b" | awk '/RUNNER_PID_LOCK/{print $2}')"; [[ -n "$p1" && -n "$pb" && "$p1" != "$pb" && "$p1" == "$p2" && "$p1" == "$p3" ]] || die "lock_pid output_a=${out_a//$'\n'/ } output_b=${out_b//$'\n'/ }"
  [[ "$(scalar "SELECT count(*) FROM odds_staging_schema_migrations WHERE version='V99.3'")" == 1 && "$(scalar "SELECT count(*) FROM pg_class WHERE relname='m3_advisory_lock_probe_applied'")" == 1 && "$(scalar "SELECT count(*) FROM (SELECT version,count(*) FROM odds_staging_schema_migrations GROUP BY version HAVING count(*)>1)x")" == 0 ]] || die lock_final; inventory
  echo "PROBE lock project=$project A_pid=$p1 B_pid=$pb B_exit=$rc_b B=lock-busy key=731642941 ledger=1 object=1 partial=0 PASS"; cleanup; trap - EXIT INT TERM
}
rollback; checksum; lock; echo 'RUNNER_PROBES PASS rollback=passed checksum=passed lock=passed'
