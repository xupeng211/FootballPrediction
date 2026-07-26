#!/usr/bin/env bash
# lifecycle: permanent
# Fixed local-only D4E operator wrapper; no project .env and no arbitrary database target.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
PROJECT=fp_m3_persistent_sandbox; SERVICE=m3-persistent-postgres; DATABASE=fp_m3_persistent_sandbox
SECRET_DIR="${HOME}/.config/footballprediction/m3-persistent-sandbox"; RUNTIME_ENV_FILE="$SECRET_DIR/runtime.env"
die(){ echo "BLOCKED: $*" >&2; exit 1; }
[[ "${ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE:-}" == 1 ]] || die "ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE=1 required"
[[ "${M3_D4E_AUTHORIZATION_PHRASE:-}" == I_AUTHORIZE_M3_D4E_PERSISTENT_SANDBOX_WRITE ]] || die "exact D4E authorization phrase required"
[[ -f "$RUNTIME_ENV_FILE" && "$(stat -c '%a' "$RUNTIME_ENV_FILE")" == 600 ]] || die "sandbox runtime secret file unavailable or unsafe"
[[ "$PROJECT" == fp_m3_persistent_sandbox && "$SERVICE" == m3-persistent-postgres && "$DATABASE" == fp_m3_persistent_sandbox ]] || die "fixed identity mismatch"
docker network inspect "${PROJECT}_default" >/dev/null || die "sandbox network unavailable"
action="${1:-preflight}"; [[ "$action" =~ ^(preflight|write|replay|accepted-conflict|quarantine-conflict)$ ]] || die "usage: $0 {preflight|write|replay|accepted-conflict|quarantine-conflict}"
[[ -z "$(git -C "$ROOT" status --porcelain)" ]] || die "D4E operator image requires a clean committed repository worktree"
code_sha="$(git -C "$ROOT" rev-parse HEAD)"
image="footballprediction-m3-d4e-operator:$(git -C "$ROOT" rev-parse --short HEAD)"
if ! docker image inspect "$image" >/dev/null 2>&1; then
  docker build -f "$ROOT/docker/odds-staging/Dockerfile.m3-d4e-operator" -t "$image" "$ROOT"
fi
docker run --rm --network "${PROJECT}_default" --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --env-file "$RUNTIME_ENV_FILE" -e NODE_ENV=m3_sandbox -e PGHOST="$SERVICE" -e PGDATABASE="$DATABASE" -e PGUSER=fp_m3_sandbox_writer -e PGPORT=5432 -e DATABASE_URL= -e PGHOSTADDR= -e PGSERVICE= -e PGSERVICEFILE= -e DB_HOST="$SERVICE" -e M3_D4E_DATABASE="$DATABASE" -e M3_D4E_PROJECT="$PROJECT" -e M3_D4E_SERVICE="$SERVICE" -e M3_D4E_WRITER=fp_m3_sandbox_writer -e M3_D4E_SAMPLE_KIND=synthetic -e M3_D4E_PRODUCTION=false -e M3_D4E_STAGING=false -e ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE -e M3_D4E_AUTHORIZATION_PHRASE -e M3_D4E_PIPELINE_CODE_SHA="$code_sha" -e ALLOW_DB_WRITE=yes -e FINAL_DB_WRITE_CONFIRMATION=yes -e ALLOW_ODDS_WRITE=yes -e DRY_RUN=false \
  "$image" scripts/ops/odds_staging/m3_d4e_controlled_write.js "$action"
