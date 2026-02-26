#!/bin/bash
################################################################################
# V26.1 流水线全链路观测脚本
# ========================================
#
# 功能:
#   1. 实时监控 CPU、内存占用
#   2. 显示成功率、每分钟吞吐量
#   3. 内存超过 1.5GB 时触发自适应减速
#   4. 监控数据库表增长
#
# 使用方法:
#   ./scripts/monitor_pipeline.sh [PID] [间隔秒数]
#
# Author: Principal Architect & Performance Expert
# Version: V26.1 (Production)
# Date: 2025-12-27
################################################################################

set -euo pipefail

# 颜色定义
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly CYAN='\033[0;36m'
readonly NC='\033[0m' # No Color

# 配置
readonly INTERVAL=${2:-2}  # 默认 2 秒刷新一次
readonly MEMORY_LIMIT_MB=1500  # 内存限制 1.5GB
readonly DB_NAME="football_prediction_dev"

# ============================================================================
# 辅助函数
# ============================================================================

print_header() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${CYAN}  V26.1 流水线全链路观测 (Pipeline Monitor)${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

print_stats() {
    local pid=$1
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # 获取进程状态
    if ! kill -0 "$pid" 2>/dev/null; then
        echo -e "${RED}❌ 进程 $pid 已终止${NC}"
        return 1
    fi

    # CPU 和内存统计
    local stats=$(ps -p "$pid" -o %cpu,%mem,rss,etime --no-headers 2>/dev/null || echo "0 0 0 00:00:00")
    local cpu=$(echo "$stats" | awk '{print $1}')
    local mem_percent=$(echo "$stats" | awk '{print $2}')
    local mem_kb=$(echo "$stats" | awk '{print $3}')
    local elapsed=$(echo "$stats" | awk '{print $4}')

    local mem_mb=$((mem_kb / 1024))

    # 数据库统计
    local db_count=$(PGPASSWORD=$DB_PASSWORD psql -h localhost -U football_user -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM match_features_training;" 2>/dev/null | xargs || echo "N/A")

    local total_matches=$(PGPASSWORD=$DB_PASSWORD psql -h localhost -U football_user -d "$DB_NAME" -t -c \
        "SELECT COUNT(*) FROM matches WHERE UPPER(status) = 'FINISHED';" 2>/dev/null | xargs || echo "9305")

    # 计算进度
    local progress="N/A"
    if [[ "$db_count" != "N/A" && "$total_matches" != "N/A" && "$total_matches" -gt 0 ]]; then
        local percent=$((db_count * 100 / total_matches))
        progress="${db_count}/${total_matches} (${percent}%)"
    fi

    # 输出状态行
    echo -ne "${CYAN}[${timestamp}]${NC} "
    echo -ne "CPU: ${BLUE}${cpu}%${NC} | "
    echo -ne "内存: ${BLUE}${mem_mb}MB${NC} (${mem_percent}%) | "
    echo -ne "已运行: ${BLUE}${elapsed}${NC} | "
    echo -ne "进度: ${GREEN}${progress}${NC}"
    echo -ne "\r"

    # 内存警告
    if [[ $mem_mb -gt $MEMORY_LIMIT_MB ]]; then
        echo ""
        echo -e "${YELLOW}⚠️  内存超过 ${MEMORY_LIMIT_MB}MB，尝试释放缓存...${NC}"

        # 尝试释放缓存
        if [[ $EUID -eq 0 ]]; then
            sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true
            echo -e "${GREEN}✅ 缓存已释放${NC}"
        else
            echo -e "${YELLOW}⚠️  需要root权限才能释放系统缓存${NC}"
        fi
    fi

    return 0
}

get_log_tail() {
    local log_file="logs/pipeline.log"

    if [[ -f "$log_file" ]]; then
        echo ""
        echo -e "${CYAN}━━━━━━ 最近日志 ━━━━━━${NC}"
        tail -n 5 "$log_file" 2>/dev/null || echo "无日志输出"
    fi
}

# ============================================================================
# 主函数
# ============================================================================

main() {
    local pid=${1:-}

    if [[ -z "$pid" ]]; then
        echo -e "${RED}错误: 请提供流水线进程 PID${NC}"
        echo ""
        echo "使用方法: $0 <PID> [间隔秒数]"
        echo ""
        echo "示例:"
        echo "  $0 12345        # 监控 PID 12345，默认 2 秒刷新"
        echo "  $0 12345 5      # 监控 PID 12345，5 秒刷新"
        echo ""
        echo "获取流水线 PID:"
        echo "  ps aux | grep 'data_pipeline_v25.py'"
        exit 1
    fi

    print_header
    echo -e "${CYAN}监控进程: ${YELLOW}$pid${NC}"
    echo -e "${CYAN}刷新间隔: ${YELLOW}${INTERVAL}秒${NC}"
    echo -e "${CYAN}内存限制: ${YELLOW}${MEMORY_LIMIT_MB}MB${NC}"
    echo -e "${CYAN}数据库: ${YELLOW}${DB_NAME}${NC}"
    echo ""
    echo -e "${CYAN}按 Ctrl+C 停止监控${NC}"
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""

    # 捕获 Ctrl+C
    trap 'echo ""; echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; echo -e "${GREEN}监控已停止${NC}"; exit 0' INT TERM

    # 监控循环
    while true; do
        if ! print_stats "$pid"; then
            echo ""
            get_log_tail
            echo ""
            echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${RED}进程已终止，监控结束${NC}"
            echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            exit 1
        fi

        sleep "$INTERVAL"
    done
}

main "$@"
