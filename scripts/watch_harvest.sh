#!/bin/bash
# V114.0 The Watchdog - Phase 1 深夜监控哨兵
# 确保 9950X 收割任务不中断
#
# Usage:
#   bash scripts/watch_harvest.sh
#
# Features:
#   - 每 30 秒检查一次进程状态
#   - 每 5 分钟输出进度摘要
#   - 自动检测速率归零并发出警告
#   - 彩色输出，易于识别

set -euo pipefail

# ============================================================================
# V114.0 Configuration
# ============================================================================

CHECK_INTERVAL=30              # 进程检查间隔（秒）
SUMMARY_INTERVAL=300           # 进度摘要间隔（秒）
ZERO_RATE_THRESHOLD=5          # 速率归零阈值（分钟）= 连续 5 次检查无数据
LOG_FILE="logs/watch_harvest.log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ============================================================================
# V114.0 Functions
# ============================================================================

log_message() {
    local level="$1"
    local message="$2"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

check_process() {
    # 检查 run_sync.py 进程是否在运行
    if pgrep -f "python.*run_sync.py" > /dev/null; then
        return 0
    else
        return 1
    fi
}

get_entity_p_count() {
    # 查询 Entity_P 总数
    python3 -c "
import psycopg2
from src.config_unified import get_settings
settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value()
)
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM metrics_multi_source_data WHERE source_name = \\'Entity_P\\'')
count = cursor.fetchone()[0]
cursor.close()
conn.close()
print(count)
" 2>/dev/null || echo "ERROR"
}

get_recent_rate() {
    # 查询最近 5 分钟的入库速率
    python3 -c "
import psycopg2
from src.config_unified import get_settings
settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value()
)
cursor = conn.cursor()
cursor.execute('''
    SELECT COUNT(*) FROM metrics_multi_source_data
    WHERE source_name = \\'Entity_P\\'
    AND created_at > NOW() - INTERVAL \\'5 minutes\\'
''')
count = cursor.fetchone()[0]
cursor.close()
conn.close()
print(count)
" 2>/dev/null || echo "ERROR"
}

get_pending_count() {
    # 查询待处理数量
    python3 -c "
import psycopg2
from src.config_unified import get_settings
settings = get_settings()
conn = psycopg2.connect(
    host=settings.database.host,
    port=settings.database.port,
    database=settings.database.name,
    user=settings.database.user,
    password=settings.database.password.get_secret_value()
)
cursor = conn.cursor()
cursor.execute('''
    SELECT COUNT(*) FROM matches
    WHERE oddsportal_url IS NOT NULL AND oddsportal_url != \\'\\'
    AND match_id NOT IN (
        SELECT match_id FROM metrics_multi_source_data
        WHERE source_name = \\'Entity_P\\'
    )
''')
count = cursor.fetchone()[0]
cursor.close()
conn.close()
print(count)
" 2>/dev/null || echo "ERROR"
}

print_header() {
    echo ""
    echo -e "${CYAN}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}            V114.0 The Watchdog - Phase 1 深夜监控哨兵                           ${CYAN}║${NC}"
    echo -e "${CYAN}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_summary() {
    local total_count="$1"
    local recent_count="$2"
    local pending_count="$3"

    local rate_per_hour=$((recent_count * 12))  # 5分钟 * 12 = 1小时

    # 计算预计剩余时间
    if [ "$rate_per_hour" -gt 0 ]; then
        local hours_remaining=$((pending_count / rate_per_hour))
        local eta_seconds=$(date -d "+${hours_remaining} hours" +%s 2>/dev/null || echo "")
        if [ -n "$eta_seconds" ]; then
            local eta_date=$(date -d "@$eta_seconds" '+%Y-%m-%d %H:%M' 2>/dev/null || echo "计算中...")
        else
            local eta_date="计算中..."
        fi
    else
        local eta_date="∞"
    fi

    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}📊 进度摘要${NC} - $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "  Entity_P 已入库: ${GREEN}${total_count}${NC} 条"
    echo -e "  最近 5 分钟入库: ${YELLOW}${recent_count}${NC} 条 (约 ${rate_per_hour} 条/小时)"
    echo -e "  待处理剩余: ${CYAN}${pending_count}${NC} 场"
    echo -e "  预计完成时间: ${MAGENTA}${eta_date}${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_alert() {
    local message="$1"
    echo ""
    echo -e "${RED}╔══════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${RED}║${NC} $(printf "%76s" "$message") ${RED}║${NC}"
    echo -e "${RED}╚══════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# ============================================================================
# V114.0 Main Loop
# ============================================================================

main() {
    print_header

    log_message "INFO" "Watchdog 启动，开始监控 Phase 1 收割任务..."

    local zero_rate_count=0
    local iteration=0
    local last_count=0

    while true; do
        iteration=$((iteration + 1))

        # 检查进程
        if ! check_process; then
            print_alert "⚠️  警告: run_sync.py 进程未运行！"
            log_message "ERROR" "run_sync.py 进程已停止"
            sleep 60
            continue
        fi

        # 获取数据
        current_count=$(get_entity_p_count)
        recent_count=$(get_recent_rate)
        pending_count=$(get_pending_count)

        if [ "$current_count" = "ERROR" ] || [ "$recent_count" = "ERROR" ]; then
            log_message "ERROR" "数据库查询失败"
            sleep 30
            continue
        fi

        # 检查速率归零
        if [ "$recent_count" -eq 0 ]; then
            zero_rate_count=$((zero_rate_count + 1))

            if [ "$zero_rate_count" -ge $ZERO_RATE_THRESHOLD ]; then
                print_alert "⚠️  警告: 速率已归零 ${zero_rate_count} 次检查！可能需要人工介入。"
                log_message "WARN" "速率归零 ${zero_rate_count} 次连续检查"
            fi
        else
            zero_rate_count=0
        fi

        # 定期输出摘要
        if [ $((iteration % (SUMMARY_INTERVAL / CHECK_INTERVAL))) -eq 0 ]; then
            print_summary "$current_count" "$recent_count" "$pending_count"
        fi

        # 首次运行时输出初始状态
        if [ $iteration -eq 1 ]; then
            print_summary "$current_count" "$recent_count" "$pending_count"
            log_message "INFO" "初始状态: Entity_P=${current_count}, 待处理=${pending_count}"
        fi

        last_count=$current_count
        sleep $CHECK_INTERVAL
    done
}

# 捕获退出信号
trap 'echo ""; echo -e "${YELLOW}Watchdog 已停止${NC}"; exit 0' INT TERM

# 启动监控
main
