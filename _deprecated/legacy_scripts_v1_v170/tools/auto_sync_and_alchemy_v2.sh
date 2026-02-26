#!/bin/bash
###############################################################################
# V36.6 Auto Sync & Alchemy V2 - 断流修复版
#
# 功能: 每 15 分钟自动执行数据同步和特征提取
# 数据流: matches_mapping → matches → match_features
#
# V36.6 核心修复:
#   - INSERT ON CONFLICT 修复同步断流漏洞
#   - 新比赛能自动创建 matches 记录
#   - 数据流闭环保证 (UPSERT 模式)
#
# V36.4 加固特性 (保留):
#   - 动态 PID 验证 (kill -0)
#   - 过期锁自动突破
#   - EXIT 信号完整处理
#   - 鲁棒性清理保证
#
# 使用:
#   ./auto_sync_and_alchemy_v2.sh [--once] [--interval N]
#
# Author: SRE Team
# Version: V36.6 (断流修复)
# Date: 2026-01-12
###############################################################################

set -euo pipefail

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$PROJECT_ROOT/logs"
LOG_FILE="$LOG_DIR/auto_sync_and_alchemy_v2.log"
PID_FILE="$LOG_DIR/auto_sync_and_alchemy_v2.pid"

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
# 初始化 - V36.4 鲁棒性加固
# ============================================================================

# 创建日志目录
mkdir -p "$LOG_DIR"

# V36.4: 检查是否已在运行（使用 kill -0 标准验证）
if [ -f "$PID_FILE" ]; then
    OLD_PID=$(cat "$PID_FILE")

    # V36.4: 使用 kill -0 进行动态验证（POSIX 标准）
    if kill -0 "$OLD_PID" 2>/dev/null; then
        # 进程确实在运行
        log "⚠️  进程已在运行 (PID: $OLD_PID)"
        log "如需重启，请先运行: kill $OLD_PID"
        exit 1
    else
        # V36.4: 过期锁自动突破
        log "🧹 检测到过期锁文件 (PID: $OLD_PID)"
        log "   该进程已不存在，自动清理并重新启动"
        rm -f "$PID_FILE"
        log "✅ 过期锁已清除，继续启动"
    fi
fi

# 记录当前 PID
echo $$ > "$PID_FILE"

# ============================================================================
# 清理函数 - V36.4 完整信号处理
# ============================================================================

cleanup() {
    local exit_status=$?
    log "🛑 清理函数触发 (exit code: $exit_status)"

    # V36.4: 确保 PID 文件被删除（无论是正常退出还是异常）
    if [ -f "$PID_FILE" ]; then
        rm -f "$PID_FILE"
        log "✅ PID 文件已清理: $PID_FILE"
    fi

    # V36.4: 根据退出状态记录不同信息
    if [ "$exit_status" -eq 0 ]; then
        log "🏁 脚本正常退出"
    else
        log "⚠️  脚本异常退出 (code: $exit_status)"
    fi
}

# V36.4: 同时处理 SIGINT、SIGTERM 和 EXIT（三种退出方式）
trap cleanup SIGINT SIGTERM EXIT

# ============================================================================
# 核心功能
# ============================================================================

sync_matches_mapping() {
    log "📦 [Step 1/2] 同步 matches_mapping → matches (纯 SQL)"

    cd "$PROJECT_ROOT"

    # V36.6: 修复同步断流漏洞 - 使用 INSERT ON CONFLICT 实现数据流闭环
    # 原问题: 只更新已存在的记录，新比赛无法进入 matches 表
    # 新方案: 如果 match 不存在则插入，存在则更新
    local synced_count=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
        -- V36.6: UPSERT 操作 - 确保 matches_mapping 中的数据能流向 matches
        INSERT INTO matches (
            match_id,
            external_id,
            league_name,
            season,
            home_team,
            away_team,
            l3_odds_data,
            l3_extracted_at,
            l3_extraction_status,
            updated_at,
            created_at,
            data_source
        )
        SELECT
            mm.fotmob_id AS match_id,
            mm.fotmob_id AS external_id,
            COALESCE(mm.league_name, 'Unknown League') AS league_name,
            '2324' AS season,
            COALESCE(mm.home_team, 'Unknown Home') AS home_team,
            COALESCE(mm.away_team, 'Unknown Away') AS away_team,
            mm.l2_raw_json::jsonb AS l3_odds_data,
            NOW() AS l3_extracted_at,
            'synced' AS l3_extraction_status,
            NOW() AS updated_at,
            NOW() AS created_at,
            'OddsPortal' AS data_source
        FROM matches_mapping mm
        WHERE mm.l2_raw_json IS NOT NULL
          AND mm.status = 'harvested'
        ON CONFLICT (match_id) DO UPDATE SET
            l3_odds_data = EXCLUDED.l3_odds_data,
            l3_extracted_at = EXCLUDED.l3_extracted_at,
            l3_extraction_status = EXCLUDED.l3_extraction_status,
            updated_at = EXCLUDED.updated_at
        RETURNING (CASE WHEN xmax = 0 THEN 'INSERTED' ELSE 'UPDATED' END);
    " | grep -c -E '(INSERTED|UPDATED)' || echo "0")

    if [ -n "$synced_count" ] && [ "$synced_count" -gt 0 ]; then
        log "✅ 数据同步完成: $synced_count 条记录 (INSERT + UPDATE)"
        return 0
    else
        log "ℹ️  没有新数据需要同步"
        return 0
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
    log "🚀 V36.6 Auto Sync & Alchemy - 断流修复版"
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

log "🎯 V36.6 Auto Sync & Alchemy 启动"
log "   循环间隔: ${INTERVAL_MINUTES} 分钟"
log "   运行模式: $([ "$RUN_ONCE" = true ] && echo '单次执行' || echo '循环执行')"
log "   PID 文件: $PID_FILE"
log "   当前 PID: $$"
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

# V36.6: 此处不需要手动清理，trap EXIT 会自动调用 cleanup()
log "🏁 Auto Sync & Alchemy V2 正常退出"
