#!/usr/bin/env bash
# lifecycle: permanent; canonical task-specific PostgreSQL 15 proof launcher.
# It creates only a labelled tmpfs database/container set and verifies removal.
set -euo pipefail

expected_schema_authorization='authorized-synthetic-disposable-schema-v1'
expected_proof_authorization='authorized-synthetic-disposable-proof-v1'
if [[ "${M3_CANONICAL_DISPOSABLE_SCHEMA_AUTHORIZATION:-}" != "$expected_schema_authorization" ]]; then
  echo "BLOCKED: requires M3_CANONICAL_DISPOSABLE_SCHEMA_AUTHORIZATION=$expected_schema_authorization" >&2
  exit 1
fi
if [[ "${M3_CANONICAL_DISPOSABLE_PROOF_AUTHORIZATION:-}" != "$expected_proof_authorization" ]]; then
  echo "BLOCKED: requires M3_CANONICAL_DISPOSABLE_PROOF_AUTHORIZATION=$expected_proof_authorization" >&2
  exit 1
fi

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
if [[ -n "$(git -C "$repo_root" status --porcelain)" ]]; then
  echo "BLOCKED: disposable proof requires a clean checked-out worktree" >&2
  exit 1
fi
compose_file="$repo_root/tests/integration/canonical_inventory/docker-compose.disposable.yml"
nonce="$(date +%s)_${RANDOM}"
project="fp_m3_canonical_${nonce}"
export M3_CANONICAL_DB_NAME="fp_m3_canonical_ephemeral_${nonce}"
export M3_CANONICAL_DB_ADMIN_USER="m3_canonical_admin"
export M3_CANONICAL_DB_ADMIN_PASSWORD="$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
export M3_CANONICAL_WRITER_CODE_REVISION="$(git -C "$repo_root" rev-parse HEAD)"
if [[ ! "$M3_CANONICAL_WRITER_CODE_REVISION" =~ ^[0-9a-f]{40}$ ]]; then
  echo "M3 canonical disposable proof requires a checked-out git revision" >&2
  exit 1
fi

cleanup() {
  docker compose -p "$project" -f "$compose_file" down -v --remove-orphans >/dev/null 2>&1 || true
  local remaining
  remaining="$(docker ps -aq --filter label=com.footballprediction.scope=m3-canonical-inventory-disposable --filter label=com.docker.compose.project="$project")$(docker network ls -q --filter label=com.footballprediction.scope=m3-canonical-inventory-disposable --filter label=com.docker.compose.project="$project")$(docker volume ls -q --filter label=com.footballprediction.scope=m3-canonical-inventory-disposable --filter label=com.docker.compose.project="$project")"
  if [[ -n "$remaining" ]]; then
    echo "M3 canonical disposable cleanup verification failed for $project" >&2
    exit 1
  fi
}
trap cleanup EXIT INT TERM

echo "M3 canonical disposable project=$project database=$M3_CANONICAL_DB_NAME (password redacted)"
docker compose -p "$project" -f "$compose_file" up --abort-on-container-exit --exit-code-from restore-baseline-verifier \
  --attach bootstrap --attach schema-verifier --attach prewrite-backup --attach owner-phase-seal \
  --attach runner --attach restore-verifier --attach restore-baseline-verifier restore-baseline-verifier
