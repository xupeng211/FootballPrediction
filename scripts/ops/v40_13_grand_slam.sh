#!/bin/bash
###############################################################################
# V40.13 "大满贯收官" - 最终执行脚本
#
# 功能: 使用暴力加载 2.0 补齐西甲和法甲的 23/24 赛季数据
#
# V40.13 核心特性:
#   - 暴力加载 2.0: 直接注入 results/#/page/{n}/
#   - 针对 n > 7 的页面使用 networkidle + 30s timeout
#   - 熔断保护: 连续 3 次无进展自动终止
#   - 增强版 Slug 映射: 支持重音符号、简写、历史队名
#
# 使用:
#   ./v40_13_grand_slam.sh [--dry-run] [--league "La Liga|Ligue 1"]
#
# Author: 首席逆向数据架构师
# Version: V40.13
# Date: 2026-01-13
###############################################################################

set -euo pipefail

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/v40_13_grand_slam.log"

# 默认配置
DRY_RUN=false
TARGET_LEAGUE="all"

# 时间戳函数
ts() {
    date '+%Y-%m-%d %H:%M:%S'
}

log() {
    echo "[$(ts)] $*" | tee -a "$LOG_FILE"
}

# ============================================================================
# 参数解析
# ============================================================================

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --league)
            TARGET_LEAGUE="$2"
            shift 2
            ;;
        -h|--help)
            echo "用法: $0 [--dry-run] [--league La Liga|Ligue 1]"
            echo ""
            echo "选项:"
            echo "  --dry-run       干跑模式（不实际采集）"
            echo "  --league        目标联赛 (La Liga, Ligue 1, all)"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看帮助"
            exit 1
            ;;
    esac
done

# ============================================================================
# 初始化
# ============================================================================

# 创建日志目录
mkdir -p "$LOG_DIR"

log "=" "70"
log "🚀 V40.13 大满贯收官 - 最终执行"
log "=" "70"
log "模式: $([ "$DRY_RUN" = true ] && echo "干跑" || echo "生产")"
log "目标联赛: $TARGET_LEAGUE"
log ""

# ============================================================================
# 数据库覆盖率检查
# ============================================================================

check_coverage() {
    local league_name="$1"
    local target_matches="$2"

    log "📊 检查 $league_name 覆盖率..."

    # 查询当前比赛数量
    local current_matches=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
        SELECT COUNT(*)
        FROM matches_mapping
        WHERE league_name = '$league_name'
          AND season = '23/24';
    " | tr -d ' ')

    # 计算覆盖率
    local coverage=$(echo "scale=2; $current_matches * 100 / $target_matches" | bc)

    log "   当前: $current_matches / $target_matches ($coverage%)"

    # 返回当前比赛数量
    echo "$current_matches"
}

# ============================================================================
# 执行暴力采集
# ============================================================================

run_brutal_harvest() {
    local league_name="$1"

    log "=" "70"
    log "🎯 开始采集: $league_name"
    log "=" "70"

    cd "$PROJECT_ROOT"

    if [ "$DRY_RUN" = true ]; then
        log "🔍 干跑模式: 跳过实际采集"
        return 0
    fi

    # 执行暴力采集
    python scripts/ops/v40_13_brutal_harvest.py 2>&1 | tee -a "$LOG_FILE"
}

# ============================================================================
# 主流程
# ============================================================================

# 1. 检查初始覆盖率
log "📊 初始覆盖率检查:"
log "-" "70"

if [ "$TARGET_LEAGUE" = "all" ] || [ "$TARGET_LEAGUE" = "La Liga" ]; then
    LALIGA_CURRENT=$(check_coverage "La Liga" 380)
fi

if [ "$TARGET_LEAGUE" = "all" ] || [ "$TARGET_LEAGUE" = "Ligue 1" ]; then
    LIGUE1_CURRENT=$(check_coverage "Ligue 1" 342)
fi

log ""

# 2. 执行采集
if [ "$TARGET_LEAGUE" = "all" ] || [ "$TARGET_LEAGUE" = "La Liga" ]; then
    run_brutal_harvest "La Liga"
fi

if [ "$TARGET_LEAGUE" = "all" ] || [ "$TARGET_LEAGUE" = "Ligue 1" ]; then
    run_brutal_harvest "Ligue 1"
fi

# 3. 验证最终覆盖率
log ""
log "=" "70"
log "📊 最终覆盖率验证:"
log "-" "70"

if [ "$TARGET_LEAGUE" = "all" ] || [ "$TARGET_LEAGUE" = "La Liga" ]; then
    LALIGA_FINAL=$(check_coverage "La Liga" 380)
    LALIGA_GAIN=$((LALIGA_FINAL - LALIGA_CURRENT))
    log "✅ 西甲: +$LALIGA_GAIN 场"
fi

if [ "$TARGET_LEAGUE" = "all" ] || [ "$TARGET_LEAGUE" = "Ligue 1" ]; then
    LIGUE1_FINAL=$(check_coverage "Ligue 1" 342)
    LIGUE1_GAIN=$((LIGUE1_FINAL - LIGUE1_CURRENT))
    log "✅ 法甲: +$LIGUE1_GAIN 场"
fi

log "=" "70"
log ""
log "🏁 V40.13 大满贯收官 - 执行完成"
log ""
