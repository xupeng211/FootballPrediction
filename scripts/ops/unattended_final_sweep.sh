#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.dev.yml"
SEASON="2025/2026"
BUDGET_SECONDS=30000
THRESHOLD="0.15"
CONCURRENCY=5
ALL_NON_LINKED=1
FORCE_DOM_MODE=0
RUN_LOG=""
AUDIT_LOG=""

timestamp() {
  date '+%Y-%m-%d %H:%M:%S %Z'
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*"
}

usage() {
  cat <<'EOF'
用法:
  scripts/ops/unattended_final_sweep.sh
    [--season 2025/2026]
    [--budget-seconds 30000]
    [--threshold 0.15]
    [--concurrency 5]
    [--force-dom-mode]
    [--run-log path]
    [--audit-log path]
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --season)
      SEASON="$2"
      shift 2
      ;;
    --budget-seconds)
      BUDGET_SECONDS="$2"
      shift 2
      ;;
    --threshold)
      THRESHOLD="$2"
      shift 2
      ;;
    --concurrency)
      CONCURRENCY="$2"
      shift 2
      ;;
    --force-dom-mode)
      FORCE_DOM_MODE=1
      shift
      ;;
    --run-log)
      RUN_LOG="$2"
      shift 2
      ;;
    --audit-log)
      AUDIT_LOG="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "未知参数: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

mkdir -p "${ROOT_DIR}/logs/ops"

if [[ -z "${RUN_LOG}" ]]; then
  RUN_LOG="${ROOT_DIR}/logs/ops/unattended_final_sweep_${SEASON//\//}_$(date +%Y%m%d_%H%M%S).log"
fi

if [[ -z "${AUDIT_LOG}" ]]; then
  AUDIT_LOG="${ROOT_DIR}/logs/ops/unattended_final_audit_${SEASON//\//}_$(date +%Y%m%d_%H%M%S).log"
fi

{
  log "UNATTENDED_FINAL_SWEEP_START season=${SEASON} budget_seconds=${BUDGET_SECONDS} threshold=${THRESHOLD} concurrency=${CONCURRENCY} force_dom_mode=${FORCE_DOM_MODE}"
  set +e
  bash "${ROOT_DIR}/scripts/ops/loop_harvest.sh" \
    --season "${SEASON}" \
    --all-non-linked \
    --budget-seconds "${BUDGET_SECONDS}" \
    --threshold "${THRESHOLD}" \
    --concurrency "${CONCURRENCY}" \
    $([[ "${FORCE_DOM_MODE}" == "1" ]] && printf '%s' '--force-dom-mode')
  harvest_exit_code=$?
  set -e
  log "UNATTENDED_FINAL_SWEEP_END exit_code=${harvest_exit_code}"
  log "FINAL_AUDIT_TRIGGERED audit_log=${AUDIT_LOG}"
} >> "${RUN_LOG}" 2>&1

{
  log "FINAL_AUDIT_START season=${SEASON}"
  docker-compose -f "${COMPOSE_FILE}" exec -T db \
    psql -U football_user -d football_db \
    -c "SELECT pipeline_status, COUNT(*) FROM matches WHERE season = '${SEASON}' GROUP BY 1 ORDER BY COUNT(*) DESC, 1;"
  docker-compose -f "${COMPOSE_FILE}" exec -T db \
    psql -U football_user -d football_db \
    -c "SELECT COUNT(*) AS total_formal_mappings, COUNT(*) FILTER (WHERE full_url ILIKE '%/h2h/%') AS h2h_rows, ROUND(100.0 * COUNT(*) FILTER (WHERE full_url ILIKE '%/h2h/%') / NULLIF(COUNT(*), 0), 4) AS h2h_ratio_pct FROM matches_oddsportal_mapping WHERE season = '${SEASON}' AND COALESCE(is_evidence_only, FALSE) = FALSE;"
  docker-compose -f "${COMPOSE_FILE}" exec -T db \
    psql -U football_user -d football_db \
    -c "SELECT COUNT(*) FILTER (WHERE pipeline_status = 'RECON_LINKED') AS recon_linked, COUNT(*) FILTER (WHERE pipeline_status = 'harvested') AS harvested_backlog FROM matches WHERE season = '${SEASON}';"
  log "FINAL_AUDIT_END"
} > "${AUDIT_LOG}" 2>&1

{
  log "FINAL_AUDIT_FINISHED audit_log=${AUDIT_LOG}"
} >> "${RUN_LOG}" 2>&1
