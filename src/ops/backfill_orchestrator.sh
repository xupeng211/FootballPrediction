#!/bin/bash
# ============================================
# V19.4.1 五大联赛数据回填编排脚本
# ============================================
#
# 功能: 自动化执行五大联赛 4 赛季数据回填
# 目标: 5784 场比赛 (Ligue 1 暂时跳过)
#
# 使用方式:
#   bash src/ops/backfill_orchestrator.sh
#
# ============================================

set -e

# 配置
PYTHON_BIN="python3"
BACKFILL_SCRIPT="src/ops/mass_backfill.py"
LOG_DIR="logs/backfill"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 创建日志目录
mkdir -p "$LOG_DIR"

# 五大联赛配置
declare -A LEAGUES=(
    ["Premier League"]=47
    ["La Liga"]=87
    ["Serie A"]=55
    ["Bundesliga"]=54
)

# 目标赛季
SEASONS=("2122" "2223" "2324" "2425")

# ============================================
# 工具函数
# ============================================

log_info() {
    echo "[INFO] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo "[ERROR] $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

check_db_count() {
    docker-compose exec -T db psql -U football_user -d football_db -t -c \
        "SELECT COUNT(*) FROM matches;" | tr -d ' '
}

check_league_count() {
    local league_id=$1
    docker-compose exec -T db psql -U football_user -d football_db -t -c \
        "SELECT COUNT(*) FROM matches WHERE SUBSTRING(external_id, 1, 2) IN (
            SELECT SUBSTRING(match_id::text, 1, 2)
            FROM (
                SELECT match_id FROM (
                    SELECT match_id, '39' as p
                    UNION ALL SELECT match_id, '41'
                    UNION ALL SELECT match_id, '48'
                ) x
            ) y
        );" | tr -d ' '
}

# ============================================
# 主流程
# ============================================

log_info "========================================"
log_info "V19.4.1 五大联赛数据回填启动"
log_info "========================================"
log_info "目标: ${#LEAGUES[@]} 个联赛 x ${#SEASONS[@]} 个赛季"
log_info "预计: 5784 场比赛"
log_info "日志: $LOG_DIR/backfill_$TIMESTAMP.log"
log_info ""

# 记录初始状态
INITIAL_COUNT=$(check_db_count)
log_info "数据库初始状态: $INITIAL_COUNT 场比赛"
log_info ""

# 执行回填
TOTAL_SUCCESS=0
TOTAL_FAILED=0

for league in "${!LEAGUES[@]}"; do
    league_id=${LEAGUES[$league]}

    log_info "========================================"
    log_info "联赛: $league (ID: $league_id)"
    log_info "========================================"

    for season in "${SEASONS[@]}"; do
        log_info ""
        log_info "--- 赛季: $season ---"

        LOG_FILE="$LOG_DIR/backfill_${league}_${season}_${TIMESTAMP}.log"

        if $PYTHON_BIN $BACKFILL_SCRIPT --league "$league" --season "$season" >> "$LOG_FILE" 2>&1; then
            log_info "✅ $league $season 完成"
            ((TOTAL_SUCCESS++))
        else
            log_error "❌ $league $season 失败，查看日志: $LOG_FILE"
            ((TOTAL_FAILED++))
        fi

        # 短暂休息
        sleep 5
    done
done

# 最终统计
log_info ""
log_info "========================================"
log_info "回填完成统计"
log_info "========================================"

FINAL_COUNT=$(check_db_count)
ADDED_COUNT=$((FINAL_COUNT - INITIAL_COUNT))

log_info "初始数量: $INITIAL_COUNT"
log_info "最终数量: $FINAL_COUNT"
log_info "新增数量: $ADDED_COUNT"
log_info "成功任务: $TOTAL_SUCCESS"
log_info "失败任务: $TOTAL_FAILED"

# 生成数据库报告
log_info ""
log_info "生成数据库报告..."
docker-compose exec db psql -U football_user -d football_db -c "
SELECT
    SUBSTRING(external_id, 1, 2) as id_prefix,
    COUNT(*) as match_count,
    CASE
        WHEN SUBSTRING(external_id, 1, 2) = '39' THEN 'Premier League 22/23'
        WHEN SUBSTRING(external_id, 1, 2) = '41' THEN 'Premier League 23/24'
        WHEN SUBSTRING(external_id, 1, 2) = '48' THEN 'La Liga 22/23'
        WHEN SUBSTRING(external_id, 1, 2) = '49' THEN 'Serie A 22/23'
        ELSE 'Other'
    END as league_season
FROM matches
GROUP BY SUBSTRING(external_id, 1, 2)
ORDER BY id_prefix;
"

log_info ""
log_info "========================================"
log_info "回填任务完成！"
log_info "========================================"
