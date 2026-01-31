#!/bin/bash
#
# V20.3 流式回填脚本
# ==================
#
# 功能：
# - 按联赛/赛季分批执行 L1 + L2 采集
# - 每采集 100 场，自动调用 FeatureForgeV20 进行全维度解析
# - API 限速保护 (DELAY_SECONDS=2.0)
# - 每小时打印统计摘要
# - 每个赛季完成后自动快照
#
# 作者: DataOps Team
# 日期: 2025-12-24
# 版本: V20.3
#

set -euo pipefail

# ==================== 配置 ====================
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${PROJECT_ROOT}"

# API 限速配置
DELAY_SECONDS=${DELAY_SECONDS:-2.0}
BATCH_SIZE=${BATCH_SIZE:-100}

# 五大联赛配置
declare -A LEAGUE_NAMES=(
    [47]="Premier_League"
    [53]="Serie_A"
    [54]="Bundesliga"
    [55]="Ligue_1"
    [87]="LaLiga"
)

declare -a SEASONS=("2122" "2223" "2324" "2425")

# 统计文件
STATS_DIR="${PROJECT_ROOT}/data/backfill_stats"
mkdir -p "${STATS_DIR}"
STATS_LOG="${STATS_DIR}/backfill_$(date +%Y%m%d_%H%M%S).log"

# ==================== 工具函数 ====================

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "${STATS_LOG}"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    log "SUCCESS" "$@"
}

format_duration() {
    local seconds=$1
    local hours=$((seconds / 3600))
    local minutes=$(((seconds % 3600) / 60))
    local secs=$((seconds % 60))
    printf "%02d:%02d:%02d" $hours $minutes $secs
}

# ==================== 数据库统计 ====================

print_db_stats() {
    log_info "=== 数据库统计摘要 ==="

    # 使用 Python 查询数据库
    docker exec football_prediction_app python3 -c "
import os
os.environ['DB_HOST'] = 'db'
os.environ['DB_NAME'] = 'football_db'
os.environ['DB_USER'] = 'football_user'
os.environ['DB_PASSWORD'] = 'football_pass'

from src.config_unified import get_settings
from psycopg2.extras import RealDictCursor
import psycopg2

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
    cursor_factory=RealDictCursor
)

cur = conn.cursor()

# L2 采集统计
cur.execute('SELECT COUNT(*) as count, COUNT(l2_raw_json) as with_json FROM l2_match_data')
l2_stats = cur.fetchone()
print(f'L2 采集: {l2_stats[\"count\"]} 场 (含 JSON: {l2_stats[\"with_json\"]})')

# 特征表统计
cur.execute('SELECT COUNT(*) as count, COUNT(features_json) as with_features FROM match_features')
feature_stats = cur.fetchone()
print(f'特征表: {feature_stats[\"count\"]} 场 (含特征: {feature_stats[\"with_features\"]})')

# 球员基准统计
cur.execute('SELECT COUNT(DISTINCT player_id) as count FROM player_baselines WHERE player_id IS NOT NULL')
player_stats = cur.fetchone()
print(f'球员基准: {player_stats[\"count\"]} 人')

# 核心 xG 特征非空比例
cur.execute('''
    SELECT
        COUNT(*) as total,
        COUNT(CASE WHEN features_json::text LIKE '%xg%' THEN 1 END) as with_xg
    FROM match_features
''')
xg_stats = cur.fetchone()
xg_ratio = 0
if xg_stats['total'] > 0:
    xg_ratio = (xg_stats['with_xg'] / xg_stats['total']) * 100
print(f'xG 特征覆盖率: {xg_ratio:.1f}% ({xg_stats[\"with_xg\"]}/{xg_stats[\"total\"]})')

cur.close()
conn.close()
" 2>&1 | grep -v "^INFO:" | tee -a "${STATS_LOG}"
}

# ==================== 单赛季回填 ====================

backfill_season() {
    local league_id=$1
    local league_name=$2
    local season=$3
    local manifest_file="${PROJECT_ROOT}/data/production/manifest_${league_id}_${season}.csv"

    if [[ ! -f "${manifest_file}" ]]; then
        log_error "Manifest 文件不存在: ${manifest_file}"
        return 1
    fi

    local total_matches=$(wc -l < "${manifest_file}")
    total_matches=$((total_matches - 1))  # 减去表头

    log_info "=== 开始回填: ${league_name} ${season} (${total_matches} 场) ==="

    local start_time=$(date +%s)
    local processed=0
    local batch_num=0

    # 分批处理
    while IFS=',' read -r match_id league_id_raw league_name_raw season_id home_team away_team status collection_date; do
        # 跳过表头
        if [[ "${match_id}" == "match_id" ]]; then
            continue
        fi

        # 去除引号
        match_id="${match_id%\"}"
        match_id="${match_id#\"}"

        # 采集 L2 数据
        log_info "采集比赛 #${processed}: ${match_id} (${home_team} vs ${away_team})"

        docker exec football_prediction_app python3 -c "
import os
os.environ['DB_HOST'] = 'db'
os.environ['DB_NAME'] = 'football_db'
os.environ['DB_USER'] = 'football_user'
os.environ['DB_PASSWORD'] = 'football_pass'

from src.api.collectors.fotmob_core import FotMobDataCollector
from datetime import datetime

collector = FotMobDataCollector()
match_data = collector.collect_match_l2(${match_id})

if match_data:
    from src.config_unified import get_settings
    from psycopg2.extras import RealDictCursor
    import psycopg2

    settings = get_settings()
    conn = psycopg2.connect(
        host=settings.database.host,
        port=settings.database.port,
        database=settings.database.name,
        user=settings.database.user,
        password=settings.database.password.get_secret_value(),
        cursor_factory=RealDictCursor
    )
    cur = conn.cursor()

    cur.execute('''
        INSERT INTO l2_match_data (id, league_id, season_id, home_team, away_team, l2_raw_json, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            l2_raw_json = EXCLUDED.l2_raw_json,
            updated_at = NOW()
    ''', (${match_id}, ${league_id}, '${season}', '${home_team}', '${away_team}', match_data.get('l2_raw_json'), datetime.now()))

    conn.commit()
    cur.close()
    conn.close()
    print('SUCCESS')
else:
    print('FAILED')
" 2>&1 | grep -v "^INFO:" | tail -1

        # 限速
        sleep ${DELAY_SECONDS}

        processed=$((processed + 1))

        # 每批提取特征
        if (( processed % BATCH_SIZE == 0 )); then
            batch_num=$((batch_num + 1))
            log_info "=== 批次 #${batch_num}: 已处理 ${processed}/${total_matches} 场，开始特征提取 ==="

            # 提取特征
            docker exec football_prediction_app python3 -c "
import os
os.environ['DB_HOST'] = 'db'
os.environ['DB_NAME'] = 'football_db'
os.environ['DB_USER'] = 'football_user'
os.environ['DB_PASSWORD'] = 'football_pass'

from src.ml.feature_forge_v20 import FeatureForgeV20
from src.config_unified import get_settings
from psycopg2.extras import RealDictCursor
import psycopg2

settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value(),
    cursor_factory=RealDictCursor
)

# 获取最近采集的比赛
cur = conn.cursor()
cur.execute('''
    SELECT id, league_id, season_id, home_team, away_team, home_score, away_score, l2_raw_json
    FROM l2_match_data
    WHERE l2_raw_json IS NOT NULL
    ORDER BY created_at DESC LIMIT %s
''', (${BATCH_SIZE},))

matches = cur.fetchall()
cur.close()

forge = FeatureForgeV20(n_workers=1)

for match in matches:
    match_data = {
        'id': match[0],
        'league_id': match[1],
        'season_id': match[2],
        'home_team': match[3],
        'away_team': match[4],
        'home_score': match[5],
        'away_score': match[6],
        'l2_raw_json': match[7]
    }

    result = forge.process_match(match_data)
    if result and result.get('status') == 'success':
        print(f'特征提取成功: {match[0]}')

conn.close()
" 2>&1 | grep -v "^INFO:" | tail -5

            # 每小时打印统计
            if (( processed % 500 == 0 )); then
                print_db_stats
            fi
        fi

    done < "${manifest_file}"

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_success "=== 回填完成: ${league_name} ${season} (${processed} 场, 耗时: $(format_duration ${duration})) ==="

    # 赛季完成后自动快照
    log_info "触发自动快照..."
    "${PROJECT_ROOT}/src/ops/snapshot_assets.sh" || true

    return 0
}

# ==================== 主流程 ====================

main() {
    log_info "=== V20.3 流式回填启动 ==="
    log_info "配置: BATCH_SIZE=${BATCH_SIZE}, DELAY_SECONDS=${DELAY_SECONDS}"

    # 打印预计耗时
    local total_matches=7161
    local total_seconds=$((total_matches * (2 + DELAY_SECONDS)))
    local total_hours=$(echo "scale=1; ${total_seconds} / 3600" | bc)
    log_info "预计总耗时: ~${total_hours} 小时 (${total_matches} 场比赛)"
    log_info "预计完成时间: $(date -d "+${total_hours} hours" '+%Y-%m-%d %H:%M:%S')"

    log_info ""

    # 按联赛顺序回填
    for league_id in 47 53 54 55 87; do
        league_name="${LEAGUE_NAMES[$league_id]}"

        log_info "📋 开始处理联赛: ${league_name} (ID: ${league_id})"

        for season in "${SEASONS[@]}"; do
            backfill_season "${league_id}" "${league_name}" "${season}"
        done
    done

    log_success "=== V20.3 流式回填完成 ==="
    print_db_stats
}

# ==================== 执行 ====================

main "$@"
