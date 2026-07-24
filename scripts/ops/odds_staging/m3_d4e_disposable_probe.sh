#!/usr/bin/env bash
# lifecycle: permanent
# D4E disposable PostgreSQL 15 proof; creates only exact nonce-labelled tmpfs resources.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"; nonce="$(date -u +%s)_$RANDOM"
project="fp_m3_d4e_probe_${nonce}"; db="fp_m3_d4e_probe_${nonce}"; name="${project}-postgres"; net="${project}_default"; dir="$(mktemp -d /tmp/m3-d4e-probe.XXXXXX)"
cleanup(){ docker rm -f "$name" >/dev/null 2>&1 || true; docker network rm "$net" >/dev/null 2>&1 || true; rm -rf "$dir"; }
trap cleanup EXIT INT TERM
chmod 700 "$dir"; umask 077
owner_password="$(openssl rand -hex 24)"; writer_password="$(openssl rand -hex 24)"
printf 'POSTGRES_DB=%s\nPOSTGRES_USER=fp_m3_sandbox_owner\nPOSTGRES_PASSWORD=%s\n' "$db" "$owner_password" > "$dir/postgres.env"
printf 'M3_SANDBOX_WRITER_PASSWORD=%s\nALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE=1\nM3_D4E_AUTHORIZATION_PHRASE=I_AUTHORIZE_M3_D4E_PERSISTENT_SANDBOX_WRITE\nM3_D4E_SAMPLE_KIND=synthetic\nM3_D4E_DATABASE=fp_m3_persistent_sandbox\nM3_D4E_PROJECT=fp_m3_persistent_sandbox\nM3_D4E_SERVICE=m3-persistent-postgres\nM3_D4E_WRITER=fp_m3_sandbox_writer\nM3_D4E_PRODUCTION=false\nM3_D4E_STAGING=false\nM3_D4E_PIPELINE_CODE_SHA=d4e-disposable-probe\n' "$writer_password" > "$dir/writer.env"
chmod 600 "$dir"/*.env
docker network create --label com.footballprediction.scope=m3-d4e-disposable --label com.footballprediction.production=false "$net" >/dev/null
docker run -d --name "$name" --network "$net" --tmpfs /var/lib/postgresql/data:rw,noexec,nosuid,size=256m --env-file "$dir/postgres.env" --label com.footballprediction.scope=m3-d4e-disposable --label com.footballprediction.production=false postgres:15-alpine >/dev/null
for _ in $(seq 1 30); do docker exec "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null 2>&1 && break; sleep 1; done
docker exec "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null
docker exec -i "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<SQL
CREATE ROLE fp_m3_sandbox_writer LOGIN NOINHERIT PASSWORD '${writer_password}';
CREATE ROLE fp_m3_sandbox_migrator NOLOGIN NOINHERIT;
CREATE ROLE fp_m3_sandbox_reader LOGIN NOINHERIT;
SQL
docker cp "$ROOT/database/migrations/V26.8__create_odds_historical_staging_contract.sql" "$name:/tmp/V26.8.sql"
docker cp "$ROOT/database/migrations/V26.9__add_odds_historical_observation_fingerprint.sql" "$name:/tmp/V26.9.sql"
docker exec "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/V26.8.sql -f /tmp/V26.9.sql' >/dev/null
docker cp "$ROOT/database/sandbox/m3_odds_staging/finalize_staging_grants.sql" "$name:/tmp/grants.sql"
docker exec "$name" sh -lc 'PGPASSWORD="$POSTGRES_PASSWORD" psql -X -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f /tmp/grants.sql' >/dev/null
# The operator code deliberately refuses this nonpersistent identity; the integration adapter exercise below uses a fixed test-only identity override.
docker run -i --rm --network "$net" --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m --env-file "$dir/writer.env" -e PGHOST="$name" -e M3_D4E_PROBE_DB="$db" -e M3_D4E_DATABASE=fp_m3_persistent_sandbox -v "$ROOT:/app:ro" -w /app node:20-alpine node - <<'NODE'
const {Client}=require('pg'); const {buildD4ESyntheticResult}=require('./src/infrastructure/odds_staging/d4eSyntheticFixture'); const {buildPersistencePlan}=require('./src/infrastructure/odds_staging/persistenceContracts'); const {HistoricalOddsStagingPersistenceRepository}=require('./src/infrastructure/odds_staging/persistenceRepository'); const {M3D4EPersistentAdapter}=require('./scripts/ops/odds_staging/m3_d4e_persistent_adapter'); const {authorizeD4EWrite}=require('./scripts/ops/odds_staging/m3_d4e_authorizer'); const {sha256Text,stableStringify}=require('./src/infrastructure/odds_staging/contracts');
(async()=>{const c=new Client({host:process.env.PGHOST,database:process.env.POSTGRES_DB||process.env.M3_D4E_PROBE_DB,user:'fp_m3_sandbox_writer',password:process.env.M3_SANDBOX_WRITER_PASSWORD}); await c.connect(); const r=buildD4ESyntheticResult(process.cwd());const p=buildPersistencePlan(r,{runMode:'controlled_write',manifest_hash:sha256Text(stableStringify(r.normalized_manifest)),candidate_business_hash:sha256Text('m3-d4e-synthetic-candidate/v1'),pipeline_code_sha:'d4e-disposable-probe'});const repo=new HistoricalOddsStagingPersistenceRepository({adapter:new M3D4EPersistentAdapter(c),authorizeWrite:req=>authorizeD4EWrite(req,process.env)}); const first=await repo.execute(p,{authorization:'write_authorized'});const replay=await repo.execute(p,{authorization:'write_authorized'});p.accepted[0].business_fingerprint=sha256Text('divergent');let conflict='none';try{await repo.execute(p,{authorization:'write_authorized'})}catch(e){conflict=e.code}const counts=(await c.query("SELECT (SELECT count(*)::int FROM odds_historical_import_runs) runs,(SELECT count(*)::int FROM odds_historical_source_files) sources,(SELECT count(*)::int FROM odds_historical_staging_observations) accepted,(SELECT count(*)::int FROM odds_historical_quarantine) quarantine")).rows[0];if(JSON.stringify(first)!==JSON.stringify({status:'persisted',accepted_count:6,quarantine_count:3,duplicate_count:0})||JSON.stringify(replay)!==JSON.stringify({status:'persisted',accepted_count:0,quarantine_count:0,duplicate_count:9})||conflict!=='PERSISTENCE_CONFLICT'||JSON.stringify(counts)!==JSON.stringify({runs:1,sources:1,accepted:6,quarantine:3}))throw new Error('D4E disposable assertions failed'); console.log('D4E_DISPOSABLE first=6/3 replay=0/0/9 conflict=rollback counts=1/1/6/3');await c.end()})().catch(e=>{console.error(e);process.exit(1)})
NODE
cleanup; trap - EXIT INT TERM
