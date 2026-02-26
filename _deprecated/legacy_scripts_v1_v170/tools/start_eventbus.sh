#!/bin/bash
###############################################################################
# V37.2 EventBus 生产守护启动脚本
#
# 功能:
#   - 后台运行 EventBus 服务
#   - PID 文件管理
#   - 日志文件管理
#   - 信号处理 (SIGINT/SIGTERM/EXIT)
#   - 集成 check_tdd_status.sh
#
# 使用方法:
#   # 启动 EventBus
#   ./scripts/ops/start_eventbus.sh
#
#   # 停止 EventBus
#   kill $(cat logs/eventbus.pid)
#
#   # 检查状态
#   ./scripts/ops/check_tdd_status.sh
#
# Author: 首席 SRE & 数据库架构师
# Version: V37.2
# Date: 2026-01-12
###############################################################################

set -euo pipefail

# ===========================================================================
# 配置
# ===========================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PID_FILE="${PROJECT_ROOT}/logs/eventbus.pid"
LOG_FILE="${PROJECT_ROOT}/logs/eventbus.log"
ERROR_LOG="${PROJECT_ROOT}/logs/eventbus_error.log"
MAX_LOG_SIZE=$((100 * 1024 * 1024))  # 100 MB

# 确保日志目录存在
mkdir -p "$(dirname "${PID_FILE}")"
mkdir -p "$(dirname "${LOG_FILE}")"
mkdir -p "$(dirname "${ERROR_LOG}")"

# ===========================================================================
# 工具函数
# ===========================================================================

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $*" | tee -a "${ERROR_LOG}" >&2
}

rotate_log() {
    local log_file="$1"
    if [[ -f "${log_file}" ]]; then
        local size=$(stat -f%z "${log_file}" 2>/dev/null || stat -c%s "${log_file}" 2>/dev/null || echo 0)
        if [[ ${size} -gt ${MAX_LOG_SIZE} ]]; then
            local timestamp=$(date '+%Y%m%d_%H%M%S')
            mv "${log_file}" "${log_file}.${timestamp}"
            gzip "${log_file}.${timestamp}" &
            log_info "日志文件已轮转: ${log_file} -> ${log_file}.${timestamp}.gz"
        fi
    fi
}

cleanup() {
    local exit_code=$?
    log_info "EventBus 停止 (exit code: ${exit_code})"

    # 清理 PID 文件
    if [[ -f "${PID_FILE}" ]]; then
        rm -f "${PID_FILE}"
        log_info "PID 文件已清理"
    fi

    exit ${exit_code}
}

# 注册信号处理
trap cleanup SIGINT SIGTERM EXIT

# ===========================================================================
# 主函数
# ===========================================================================

main() {
    log_info "======================================================================"
    log_info "V37.2 EventBus 启动"
    log_info "======================================================================"
    log_info "项目根目录: ${PROJECT_ROOT}"
    log_info "PID 文件: ${PID_FILE}"
    log_info "日志文件: ${LOG_FILE}"

    # -----------------------------------------------------------------------
    # 1. 检查是否已有实例运行
    # -----------------------------------------------------------------------
    if [[ -f "${PID_FILE}" ]]; then
        local old_pid=$(cat "${PID_FILE}")
        if kill -0 "${old_pid}" 2>/dev/null; then
            log_error "EventBus 已在运行 (PID: ${old_pid})"
            log_error "如需重启，请先执行: kill ${old_pid}"
            exit 1
        else
            log_info "发现过期的 PID 文件 (${old_pid})，自动清理"
            rm -f "${PID_FILE}"
        fi
    fi

    # -----------------------------------------------------------------------
    # 2. 环境变量校验
    # -----------------------------------------------------------------------
    if [[ "${DB_NAME:-}" != "football_db" ]]; then
        log_error "DB_NAME 必须为 'football_db'，当前: '${DB_NAME:-}'"
        exit 1
    fi

    # -----------------------------------------------------------------------
    # 3. 日志轮转
    # -----------------------------------------------------------------------
    rotate_log "${LOG_FILE}"
    rotate_log "${ERROR_LOG}"

    # -----------------------------------------------------------------------
    # 4. 启动 EventBus
    # -----------------------------------------------------------------------
    log_info "启动 EventBus 服务..."

    cd "${PROJECT_ROOT}"

    # 使用 nohup 启动后台进程
    nohup python -m src.services.event_bus \
        >> "${LOG_FILE}" \
        2>> "${ERROR_LOG}" \
        &

    local pid=$!
    echo ${pid} > "${PID_FILE}"

    # 等待确认进程启动
    sleep 2

    if ! kill -0 ${pid} 2>/dev/null; then
        log_error "EventBus 启动失败，请检查日志: ${ERROR_LOG}"
        rm -f "${PID_FILE}"
        exit 1
    fi

    log_info "======================================================================"
    log_info "✅ EventBus 启动成功 (PID: ${pid})"
    log_info "======================================================================"
    log_info ""
    log_info "管理命令:"
    log_info "  查看日志: tail -f ${LOG_FILE}"
    log_info "  停止服务: kill ${pid}"
    log_info "  检查状态: ./scripts/ops/check_tdd_status.sh"
    log_info "======================================================================"
}

# ===========================================================================
# 执行
# ===========================================================================

main "$@"
