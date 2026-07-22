#!/usr/bin/env bash
# lifecycle: permanent; canonical D4C command. It creates only a labelled tmpfs PostgreSQL project and always destroys it.
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
compose_file="$repo_root/tests/integration/odds_staging/docker-compose.ephemeral.yml"
nonce="$(date +%s)_${RANDOM}"
project="fp_m3_d4c_${nonce}"
export M3_D4C_DB_NAME="fp_m3_d4c_ephemeral_${nonce}"
export M3_D4C_DB_USER="m3_d4c_${RANDOM}"
export M3_D4C_DB_PASSWORD="$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"

cleanup() {
  docker compose -p "$project" -f "$compose_file" down -v --remove-orphans >/dev/null 2>&1 || true
  remaining_containers="$(docker ps -aq --filter label=com.footballprediction.scope=m3-d4c-ephemeral --filter label=com.docker.compose.project="$project")"
  remaining_networks="$(docker network ls -q --filter label=com.footballprediction.scope=m3-d4c-ephemeral --filter label=com.docker.compose.project="$project")"
  remaining_volumes="$(docker volume ls -q --filter label=com.footballprediction.scope=m3-d4c-ephemeral --filter label=com.docker.compose.project="$project")"
  if [[ -n "$remaining_containers$remaining_networks$remaining_volumes" ]]; then
    echo "D4C cleanup verification failed for $project" >&2
    exit 1
  fi
}
trap cleanup EXIT INT TERM

echo "D4C ephemeral project=$project database=$M3_D4C_DB_NAME (password redacted)"
docker compose -p "$project" -f "$compose_file" up --abort-on-container-exit --exit-code-from runner runner
