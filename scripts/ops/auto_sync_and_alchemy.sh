#!/bin/bash
###############################################################################
# V36.3 Auto Sync & Alchemy - 数据链路全自动闭环
#
# 功能: 每 15 分钟自动执行数据同步和特征提取
# 数据流: matches_mapping → matches → match_features
#
# 使用:
#   ./auto_sync_and_alchemy.sh [--once] [--interval N]
#
# 选项:
#   --once       只执行一次，不循环
#   --interval N 设置循环间隔（分钟），默认 15
#
# Author: SRE Team
# Version: V36.3
# Date: 2026-01-12
###############################################################################

set -euo pipefail

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/auto_sync_and_alchemy.log"
PID_FILE="$LOG_DIR/auto_sync_and_alchemy.pid"

# 默认配置
INTERVAL_MINUTES=15
RUN_ONCE=false

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
        --once)
            RUN_ONCE=true
            shift
            ;;
        --interval)
            INTERVAL_MINUTES="$2"
            shift 2
            ;;
        -h|--help)
            echo "用法: $0 [--once] [--interval N]"
            echo ""
            echo "选项:"
            echo "  --once       只执行一次，不循环"
            echo "  --interval N 设置循环间隔（分钟），默认 15"
            echo ""
            echo "示例:"
            echo "  $0                 # 每 15 分钟循环执行"
            echo "  $0 --once          # 只执行一次"
            echo "  $0 --interval 30   # 每 30 分钟循环执行"
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

# 检查是否已在运行
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")
    if ps -p "$OLD_PID" > /dev/null 2>&1; then
        log "⚠️  进程已在运行 (PID: $OLD_PID)"
        log "如需重启，请先运行: kill $OLD_PID"
        exit 1
    else
        log "🧹 清理过期的 PID 文件"
        rm -f "$PID_FILE"
    fi
fi

# 记录当前 PID
echo $$ > "$PID_FILE"

# ============================================================================
# 清理函数
# ============================================================================

cleanup() {
    log "🛑 收到停止信号，正在清理..."
    rm -f "$PID_FILE"
    exit 0
}

trap cleanup SIGINT SIGTERM

# ============================================================================
# 核心功能
# ============================================================================

sync_matches_mapping() {
    log "📦 [Step 1/2] 同步 matches_mapping → matches"

    cd "$PROJECT_ROOT"

    if python scripts/ops/sync_matches_mapping_to_matches.py >> "$LOG_FILE" 2>&1; then
        log "✅ 数据同步完成"
        return 0
    else
        log "❌ 数据同步失败 (退出码: $?)"
        return 1
    fi
}

extract_features() {
    log "🧪 [Step 2/2] 特征炼金 (extract_features_v1.py)"

    cd "$PROJECT_ROOT"

    # 使用增量模式，限制每次处理 500 条记录
    if python scripts/ml/extract_features_v1.py --limit 500 >> "$LOG_FILE" 2>&1; then
        log "✅ 特征提取完成"
        return 0
    else
        log "❌ 特征提取失败 (退出码: $?)"
        return 1
    fi
}

run_pipeline() {
    log "══════════════════════════════════════════════════════════════════"
    log "🚀 V36.3 Auto Sync & Alchemy - 数据链路全自动闭环"
    log "══════════════════════════════════════════════════════════════════"

    local sync_success=0
    local extract_success=0

    # Step 1: 同步数据
    if sync_matches_mapping; then
        sync_success=1
    else
        log "⚠️  同步失败，跳过特征提取"
        return 1
    fi

    # Step 2: 提取特征
    if extract_features; then
        extract_success=1
    fi

    # 统计
    log "📊 本次执行统计:"
    log "   数据同步: $([ "$sync_success" -eq 1 ] && echo '✅ 成功' || echo '❌ 失败')"
    log "   特征提取: $([ "$extract_success" -eq 1 ] && echo '✅ 成功' || echo '❌ 失败')"

    if [ "$sync_success" -eq 1 ] && [ "$extract_success" -eq 1 ]; then
        log "🎉 数据链路闭环完成"
        return 0
    else
        log "⚠️  数据链路存在异常"
        return 1
    fi
}

# ============================================================================
# 主循环
# ============================================================================

log "🎯 V36.3 Auto Sync & Alchemy 启动"
log "   循环间隔: ${INTERVAL_MINUTES} 分钟"
log "   运行模式: $([ "$RUN_ONCE" = true ] && echo '单次执行' || echo '循环执行')"
log "══════════════════════════════════════════════════════════════════"

# 首次执行
run_pipeline

# 循环执行（如果未指定 --once）
if [ "$RUN_ONCE" = false ]; then
    while true; do
        log "⏰ 下次执行时间: $(date -d "+${INTERVAL_MINUTES} minutes" '+%Y-%m-%d %H:%M:%S')"
        sleep "$((INTERVAL_MINUTES * 60))"
        run_pipeline
    done
fi

log "🏁 Auto Sync & Alchemy 正常退出"
