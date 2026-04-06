#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="${ROOT_DIR}/docker-compose.dev.yml"
SEASON="2025/2026"
LIMIT=150
THRESHOLD="0.15"
CONCURRENCY=5
SLEEP_MIN=30
SLEEP_MAX=60
BUDGET_SECONDS=7200
RUN_JANITOR=1
JANITOR_MODE="audit"
ALL_NON_LINKED=0
FORCE_DOM_MODE=0

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

log() {
  printf '[%s] %s\n' "$(timestamp)" "$*"
}

usage() {
  cat <<'EOF'
用法:
  scripts/ops/loop_harvest.sh [--season 2025/2026] [--budget-seconds 7200]
                              [--limit 150] [--threshold 0.15] [--concurrency 5]
                              [--sleep-min 30] [--sleep-max 60] [--no-janitor]
                              [--janitor-repair] [--all-non-linked] [--force-dom-mode]
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
    --limit)
      LIMIT="$2"
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
    --sleep-min)
      SLEEP_MIN="$2"
      shift 2
      ;;
    --sleep-max)
      SLEEP_MAX="$2"
      shift 2
      ;;
    --no-janitor)
      RUN_JANITOR=0
      shift
      ;;
    --janitor-repair)
      JANITOR_MODE="repair"
      shift
      ;;
    --all-non-linked)
      ALL_NON_LINKED=1
      shift
      ;;
    --force-dom-mode)
      FORCE_DOM_MODE=1
      shift
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

if (( SLEEP_MIN < 0 || SLEEP_MAX < 0 || SLEEP_MAX < SLEEP_MIN )); then
  echo "非法休眠区间: ${SLEEP_MIN}-${SLEEP_MAX}" >&2
  exit 1
fi

if (( BUDGET_SECONDS < 0 )); then
  echo "非法 budget-seconds: ${BUDGET_SECONDS}" >&2
  exit 1
fi

db_query() {
  local sql="$1"
  docker compose -f "${COMPOSE_FILE}" exec -T db \
    psql -U football_user -d football_db -At -F $'\t' -c "${sql}"
}

run_scan() {
  local league_id="$1"
  shift
  local phase_label="$1"
  shift
  local extra_args=("$@")

  if (( ALL_NON_LINKED == 1 )); then
    extra_args+=(--all-non-linked)
  fi

  if (( FORCE_DOM_MODE == 1 )); then
    extra_args+=(--force-dom-mode)
  else
    extra_args+=(--force-pure-protocol)
  fi

  log "开始 ${phase_label}: league_id=${league_id}"
  set +e
  docker compose -f "${COMPOSE_FILE}" exec -T dev \
    node scripts/ops/recon_scanner.js \
    --season "${SEASON}" \
    --league "${league_id}" \
    --limit "${LIMIT}" \
    --threshold "${THRESHOLD}" \
    --concurrency "${CONCURRENCY}" \
    "${extra_args[@]}"
  local exit_code=$?
  set -e

  if (( exit_code != 0 )); then
    log "${phase_label} 结束但退出码非 0: league_id=${league_id}, exit_code=${exit_code}"
  else
    log "${phase_label} 完成: league_id=${league_id}"
  fi
}

random_sleep() {
  if (( SLEEP_MAX == 0 )); then
    return
  fi

  local duration="${SLEEP_MIN}"
  if (( SLEEP_MAX > SLEEP_MIN )); then
    duration=$(( RANDOM % (SLEEP_MAX - SLEEP_MIN + 1) + SLEEP_MIN ))
  fi

  if (( duration > 0 )); then
    log "随机休眠 ${duration}s，规避频率限制"
    sleep "${duration}"
  fi
}

print_status_distribution() {
  log "冻结全库 pipeline_status 分布"
  db_query "
    SELECT COALESCE(pipeline_status, 'NULL') AS pipeline_status, COUNT(*)
    FROM matches
    WHERE season = '${SEASON}'
    GROUP BY 1
    ORDER BY COUNT(*) DESC, pipeline_status ASC;
  "
}

print_focus_distribution() {
  log "输出巴甲 / 美洲杯 / 世界杯对齐分布"
  db_query "
    SELECT
      CASE
        WHEN split_part(match_id, '_', 1) = '268' THEN 'Brazil 268'
        WHEN split_part(match_id, '_', 1) = '131' THEN 'Copa America 131'
        WHEN league_name = 'FIFA World Cup' THEN 'FIFA World Cup'
        ELSE 'Other'
      END AS bucket,
      COUNT(*) FILTER (WHERE pipeline_status = 'RECON_LINKED') AS linked,
      COUNT(*) FILTER (WHERE pipeline_status IN ('harvested', 'RECON_MISMATCH')) AS pending_or_mismatch,
      COUNT(*) AS total
    FROM matches
    WHERE season = '${SEASON}'
      AND (split_part(match_id, '_', 1) IN ('268', '131') OR league_name = 'FIFA World Cup')
    GROUP BY 1
    ORDER BY 1;
  "
}

run_janitor() {
  if (( RUN_JANITOR == 0 )); then
    log "跳过 MatchCanonicalJanitor"
    return
  fi

  log "执行 MatchCanonicalJanitor"
  set +e
  docker compose -f "${COMPOSE_FILE}" exec -T dev \
    node scripts/ops/run_match_canonical_janitor.js \
    --season "${SEASON}" \
    $([[ "${JANITOR_MODE}" == "repair" ]] && printf '%s' '--repair' || printf '%s' '--audit-only')
  local exit_code=$?
  set -e

  if (( exit_code != 0 )); then
    log "MatchCanonicalJanitor 失败，exit_code=${exit_code}"
  else
    log "MatchCanonicalJanitor 完成，mode=${JANITOR_MODE}"
  fi
}

list_target_leagues() {
  local status_condition="m.pipeline_status = 'harvested'"

  if (( ALL_NON_LINKED == 1 )); then
    status_condition="
      m.pipeline_status IS DISTINCT FROM 'RECON_LINKED'
      AND m.pipeline_status NOT IN ('duplicate', 'archived', 'merged')
      AND NOT (
        m.pipeline_status = 'failed'
        AND m.external_id IS NOT NULL
        AND EXISTS (
          SELECT 1
          FROM matches canonical
          WHERE canonical.season = m.season
            AND canonical.data_source = m.data_source
            AND canonical.external_id = m.external_id
            AND canonical.match_id <> m.match_id
            AND canonical.external_id IS NOT NULL
            AND canonical.pipeline_status NOT IN ('failed', 'archived', 'duplicate', 'merged')
        )
      )
    "
  fi

  db_query "
    SELECT
      split_part(m.match_id, '_', 1) AS league_id,
      MAX(m.league_name) AS league_name,
      COUNT(*) FILTER (WHERE m.pipeline_status = 'harvested') AS harvested_count,
      COUNT(*) FILTER (WHERE m.pipeline_status = 'RECON_MISMATCH') AS mismatch_count,
      COUNT(*) FILTER (WHERE m.pipeline_status = 'failed') AS failed_count,
      COUNT(*) FILTER (WHERE m.pipeline_status = 'duplicate') AS duplicate_count,
      COUNT(*) AS eligible_count
    FROM matches m
    LEFT JOIN matches_oddsportal_mapping map
      ON map.match_id = m.match_id
     AND map.season = m.season
     AND COALESCE(map.is_evidence_only, FALSE) = FALSE
    WHERE m.season = '${SEASON}'
      AND map.match_id IS NULL
      AND ${status_condition}
    GROUP BY 1
    HAVING COUNT(*) > 0
    ORDER BY eligible_count DESC, mismatch_count DESC, league_name ASC;
  "
}

START_TS="$(date +%s)"
DEADLINE_TS=$(( START_TS + BUDGET_SECONDS ))
PASS_INDEX=0

log "loop_harvest 启动: season=${SEASON}, budget_seconds=${BUDGET_SECONDS}, limit=${LIMIT}, threshold=${THRESHOLD}, concurrency=${CONCURRENCY}, all_non_linked=${ALL_NON_LINKED}, force_dom_mode=${FORCE_DOM_MODE}"

while :; do
  local_now="$(date +%s)"
  if (( local_now >= DEADLINE_TS )); then
    log "达到预算上限，停止目标轮询"
    break
  fi

  mapfile -t LEAGUE_ROWS < <(list_target_leagues)
  if (( ${#LEAGUE_ROWS[@]} == 0 )); then
    log "当前 season=${SEASON} 已无可收割目标"
    break
  fi

  PASS_INDEX=$(( PASS_INDEX + 1 ))
  log "开始目标轮询 pass=${PASS_INDEX}, league_count=${#LEAGUE_ROWS[@]}, scope=$([[ ${ALL_NON_LINKED} -eq 1 ]] && printf '%s' 'all_non_linked' || printf '%s' 'harvested_only')"

  for row in "${LEAGUE_ROWS[@]}"; do
    local_now="$(date +%s)"
    if (( local_now >= DEADLINE_TS )); then
      log "达到预算上限，提前结束本轮"
      break 2
    fi

    IFS=$'\t' read -r league_id league_name harvested_count mismatch_count failed_count duplicate_count eligible_count <<<"${row}"
    log "处理联赛 ${league_name}(${league_id})，eligible=${eligible_count} harvested=${harvested_count} mismatch=${mismatch_count} failed=${failed_count} duplicate=${duplicate_count}"
    run_scan "${league_id}" "低压收割"

    local_now="$(date +%s)"
    if (( local_now < DEADLINE_TS )); then
      random_sleep
    fi
  done
done

if (( $(date +%s) < DEADLINE_TS )); then
  run_scan "268" "巴甲 mismatch 深度清理" --mismatch-retry-only
  if (( $(date +%s) < DEADLINE_TS )); then
    random_sleep
  fi
fi

if (( $(date +%s) < DEADLINE_TS )); then
  run_scan "131" "美洲杯 mismatch 宽松清理" --mismatch-retry-only
fi

run_janitor
print_status_distribution
print_focus_distribution

log "loop_harvest 结束"
