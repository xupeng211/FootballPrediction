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
action="${1:-preflight}"; [[ "$action" =~ ^(preflight|write|conflict)$ ]] || die "usage: $0 {preflight|write|conflict}"
code_sha="$(git -C "$ROOT" rev-parse HEAD)"
docker run --rm --network "${PROJECT}_default" --read-only --tmpfs /tmp:rw,noexec,nosuid,size=32m \
  --env-file "$RUNTIME_ENV_FILE" -e PGHOST="$SERVICE" -e M3_D4E_DATABASE="$DATABASE" -e M3_D4E_PROJECT="$PROJECT" -e M3_D4E_SERVICE="$SERVICE" -e M3_D4E_WRITER=fp_m3_sandbox_writer -e M3_D4E_SAMPLE_KIND=synthetic -e M3_D4E_PRODUCTION=false -e M3_D4E_STAGING=false -e ALLOW_M3_D4E_PERSISTENT_SANDBOX_WRITE -e M3_D4E_AUTHORIZATION_PHRASE -e M3_D4E_PIPELINE_CODE_SHA="$code_sha" \
  -v "$ROOT:/app:ro" -w /app node:20-alpine node scripts/ops/odds_staging/m3_d4e_controlled_write.js "$action"
