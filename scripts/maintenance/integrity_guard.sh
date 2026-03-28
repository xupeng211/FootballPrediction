#!/usr/bin/env bash
set -euo pipefail

COMPOSE=(docker-compose -f docker-compose.dev.yml)
DB_USER="${DB_USER:-football_user}"
DB_NAME="${DB_NAME:-football_db}"

run_psql() {
  "${COMPOSE[@]}" exec -T db psql -U "$DB_USER" -d "$DB_NAME" -t -A -F '|' -c "$1"
}

run_scalar() {
  run_psql "$1" | tr -d '[:space:]'
}

calc_rate() {
  local numerator="$1"
  local denominator="$2"
  awk -v numerator="$numerator" -v denominator="$denominator" 'BEGIN {
    if (denominator == 0) {
      printf "0.0"
    } else {
      printf "%.1f", (numerator / denominator) * 100
    }
  }'
}

print_matches() {
  local rows="$1"
  while IFS='|' read -r match_id home_team away_team; do
    [[ -n "${match_id}" ]] || continue
    echo "  - ${home_team} vs ${away_team} (${match_id})"
  done <<<"$rows"
}

print_header() {
  printf '%0.s=' {1..60}
  printf '\nTITAN 数据完整性卫士\n'
  printf '%0.s=' {1..60}
  printf '\n检查时间: %s\n' "$(date '+%Y-%m-%d %H:%M:%S')"
  printf '%0.s-' {1..60}
  printf '\n'
}

print_header

counts="$(run_psql "SELECT (SELECT COUNT(*) FROM matches), (SELECT COUNT(*) FROM raw_match_data), (SELECT COUNT(*) FROM l3_features);")"
IFS='|' read -r l1_count l2_count l3_count <<<"$counts"

echo "  L1 (matches): ${l1_count} 条记录"
echo "  L2 (raw_match_data): ${l2_count} 条记录"
echo "  L3 (l3_features): ${l3_count} 条记录"
echo "  L2 完整性: $(calc_rate "$l2_count" "$l1_count")%"
echo "  L3 完整性: $(calc_rate "$l3_count" "$l1_count")%"

missing_l2_total="$(run_scalar "SELECT COUNT(*) FROM matches m LEFT JOIN raw_match_data r ON m.match_id = r.match_id WHERE r.match_id IS NULL;")"
missing_l3_total="$(run_scalar "SELECT COUNT(*) FROM matches m LEFT JOIN l3_features l ON m.match_id = l.match_id WHERE l.match_id IS NULL;")"

if [[ "${missing_l2_total}" != "0" ]]; then
  missing_l2_rows="$(run_psql "SELECT m.match_id, COALESCE(m.home_team, 'UNKNOWN_HOME'), COALESCE(m.away_team, 'UNKNOWN_AWAY') FROM matches m LEFT JOIN raw_match_data r ON m.match_id = r.match_id WHERE r.match_id IS NULL ORDER BY m.match_id LIMIT 20;")"
  echo
  echo "⚠️  检测到 ${missing_l2_total} 条缺失 L2 数据的记录（仅显示前 20 条）"
  print_matches "$missing_l2_rows"
fi

if [[ "${missing_l3_total}" != "0" ]]; then
  missing_l3_rows="$(run_psql "SELECT m.match_id, COALESCE(m.home_team, 'UNKNOWN_HOME'), COALESCE(m.away_team, 'UNKNOWN_AWAY') FROM matches m LEFT JOIN l3_features l ON m.match_id = l.match_id WHERE l.match_id IS NULL ORDER BY m.match_id LIMIT 20;")"
  echo
  echo "⚠️  检测到 ${missing_l3_total} 条缺失 L3 数据的记录（仅显示前 20 条）"
  print_matches "$missing_l3_rows"
fi

if [[ "${missing_l2_total}" == "0" && "${missing_l3_total}" == "0" ]]; then
  echo
  echo "✅ 数据完整性良好，无需修复"
else
  echo
  printf '%0.s=' {1..60}
  printf '\n修复建议\n'
  printf '%0.s=' {1..60}
  printf '\n'

  if [[ "${missing_l2_total}" != "0" ]]; then
    missing_l2_ids="$(run_psql "SELECT m.match_id FROM matches m LEFT JOIN raw_match_data r ON m.match_id = r.match_id WHERE r.match_id IS NULL ORDER BY m.match_id LIMIT 10;" | paste -sd, -)"
    echo
    echo "缺失 L2 数据的修复命令:"
    echo "  docker-compose -f docker-compose.dev.yml exec dev npm start -- --match-ids ${missing_l2_ids}"
  fi

  if [[ "${missing_l3_total}" != "0" ]]; then
    missing_l3_ids="$(run_psql "SELECT m.match_id FROM matches m LEFT JOIN l3_features l ON m.match_id = l.match_id WHERE l.match_id IS NULL ORDER BY m.match_id LIMIT 10;" | paste -sd, -)"
    echo
    echo "缺失 L3 数据的修复命令:"
    echo "  docker-compose -f docker-compose.dev.yml exec dev npm run smelt -- --match-ids ${missing_l3_ids}"
  fi
fi

echo
printf '%0.s=' {1..60}
printf '\n检查完成\n'
printf '%0.s=' {1..60}
printf '\n'
