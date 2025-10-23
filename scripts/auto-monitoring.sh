#!/bin/bash

# 自动化监控脚本
# Automated Monitoring Script

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
LOG_FILE="$PROJECT_ROOT/logs/auto-monitoring-$(date +%Y%m%d).log"
ALERT_LOG="$PROJECT_ROOT/logs/monitoring-alerts.log"
HEALTH_CACHE="$PROJECT_ROOT/.cache/health-status.json"
MONITORING_INTERVAL="${MONITORING_INTERVAL:-300}" # 5分钟

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 日志函数
log() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] $1"
    echo -e "${GREEN}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

error() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1"
    echo -e "${RED}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
    echo "$msg" >> "$ALERT_LOG"
}

warn() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1"
    echo -e "${YELLOW}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
    echo "$msg" >> "$ALERT_LOG"
}

info() {
    local msg="[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1"
    echo -e "${BLUE}$msg${NC}"
    echo "$msg" >> "$LOG_FILE"
}

# 创建必要目录
setup_directories() {
    mkdir -p "$PROJECT_ROOT/logs"
    mkdir -p "$PROJECT_ROOT/.cache"
}

# 检查服务健康状态
check_service_health() {
    local service_name="$1"
    local health_url="$2"
    local timeout="${3:-10}"

    if curl -s -f --max-time "$timeout" "$health_url" > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 获取系统指标
get_metric_value() {
    local metric_name="$1"
    local prometheus_url="http://localhost:9090"

    local query_result
    query_result=$(curl -s -G "$prometheus_url/api/v1/query" \
        --data-urlencode "query=$metric_name" 2>/dev/null | \
        jq -r '.data.result[0].value[1]' 2>/dev/null || echo "null")

    if [[ "$query_result" != "null" && -n "$query_result" ]]; then
        echo "$query_result"
    else
        echo "0"
    fi
}

# 检查系统指标
check_system_metrics() {
    local issues_found=0

    # CPU使用率检查
    local cpu_usage
    cpu_usage=$(get_metric_value "100 * (1 - avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])))")
    if (( $(echo "$cpu_usage > 85" | bc -l 2>/dev/null || echo "0") )); then
        warn "CPU使用率过高: ${cpu_usage}%"
        ((issues_found++))
    fi

    # 内存使用率检查
    local mem_usage
    mem_usage=$(get_metric_value "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100")
    if (( $(echo "$mem_usage > 90" | bc -l 2>/dev/null || echo "0") )); then
        warn "内存使用率过高: ${mem_usage}%"
        ((issues_found++))
    fi

    # 磁盘使用率检查
    local disk_usage
    disk_usage=$(get_metric_value "(1 - (node_filesystem_avail_bytes{mountpoint=\"/\"} / node_filesystem_size_bytes{mountpoint=\"/\"})) * 100")
    if (( $(echo "$disk_usage > 85" | bc -l 2>/dev/null || echo "0") )); then
        warn "磁盘使用率过高: ${disk_usage}%"
        ((issues_found++))
    fi

    return $issues_found
}

# 检查应用指标
check_application_metrics() {
    local issues_found=0

    # API错误率检查
    local error_rate
    error_rate=$(get_metric_value "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100")
    if (( $(echo "$error_rate > 5" | bc -l 2>/dev/null || echo "0") )); then
        error "API错误率过高: ${error_rate}%"
        ((issues_found++))
    fi

    # 响应时间检查
    local response_time_p95
    response_time_p95=$(get_metric_value "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))")
    if (( $(echo "$response_time_p95 > 1" | bc -l 2>/dev/null || echo "0") )); then
        warn "P95响应时间过长: ${response_time_p95}s"
        ((issues_found++))
    fi

    # 请求速率检查
    local request_rate
    request_rate=$(get_metric_value "rate(http_requests_total[5m])")
    if (( $(echo "$request_rate < 1" | bc -l 2>/dev/null || echo "0") )); then
        warn "API请求速率过低: ${request_rate} RPS"
        ((issues_found++))
    fi

    return $issues_found
}

# 检查数据库指标
check_database_metrics() {
    local issues_found=0

    # 数据库连接数检查
    if docker-compose ps | grep -q "db.*Up"; then
        local db_connections
        db_connections=$(docker-compose exec -T db psql -U prod_user -t -c "SELECT count(*) FROM pg_stat_activity;" 2>/dev/null | xargs || echo "0")

        if [[ $db_connections -gt 80 ]]; then
            warn "数据库连接数过高: $db_connections"
            ((issues_found++))
        fi

        # 检查数据库健康状态
        if ! docker-compose exec -T db pg_isready -U prod_user > /dev/null 2>&1; then
            error "数据库连接失败"
            ((issues_found++))
        fi
    else
        error "数据库服务未运行"
        ((issues_found++))
    fi

    return $issues_found
}

# 检查缓存指标
check_cache_metrics() {
    local issues_found=0

    if docker-compose ps | grep -q "redis.*Up"; then
        # 检查Redis连接
        if ! docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            error "Redis连接失败"
            ((issues_found++))
        fi

        # 检查Redis内存使用
        local redis_memory
        redis_memory=$(get_metric_value "redis_memory_used_bytes / 1024 / 1024")
        if [[ -n "$redis_memory" ]] && (( $(echo "$redis_memory > 1024" | bc -l 2>/dev/null || echo "0") )); then
            warn "Redis内存使用过高: ${redis_memory}MB"
            ((issues_found++))
        fi
    else
        error "Redis服务未运行"
        ((issues_found++))
    fi

    return $issues_found
}

# 检查业务指标
check_business_metrics() {
    local issues_found=0

    # 检查预测准确率
    local prediction_accuracy
    prediction_accuracy=$(get_metric_value "prediction_accuracy_rate * 100")
    if [[ -n "$prediction_accuracy" ]] && (( $(echo "$prediction_accuracy < 75" | bc -l 2>/dev/null || echo "0") )); then
        warn "预测准确率过低: ${prediction_accuracy}%"
        ((issues_found++))
    fi

    # 检查数据同步状态
    local data_sync_status
    data_sync_status=$(get_metric_value "data_sync_status")
    if [[ -n "$data_sync_status" && "$data_sync_status" != "1" ]]; then
        error "数据同步状态异常: $data_sync_status"
        ((issues_found++))
    fi

    return $issues_found
}

# 更新健康状态缓存
update_health_cache() {
    local overall_status="$1"
    local timestamp
    timestamp=$(date +%s)

    local health_data
    health_data=$(cat << EOF
{
    "timestamp": $timestamp,
    "status": "$overall_status",
    "checks": {
        "system": $(check_system_metrics > /dev/null && echo "true" || echo "false"),
        "application": $(check_application_metrics > /dev/null && echo "true" || echo "false"),
        "database": $(check_database_metrics > /dev/null && echo "true" || echo "false"),
        "cache": $(check_cache_metrics > /dev/null && echo "true" || echo "false"),
        "business": $(check_business_metrics > /dev/null && echo "true" || echo "false")
    }
}
EOF
)

    echo "$health_data" > "$HEALTH_CACHE"
}

# 发送告警通知
send_alert() {
    local alert_type="$1"
    local message="$2"
    local severity="${3:-warning}"

    log "发送告警: $message"

    # 记录告警
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] [$severity] $alert_type: $message" >> "$ALERT_LOG"

    # 调用通知脚本
    if [[ -f "$SCRIPT_DIR/notify-team.sh" ]]; then
        "$SCRIPT_DIR/notify-team.sh" "$message" "$severity"
    fi

    # 如果是严重告警，执行应急响应
    if [[ "$severity" == "critical" ]]; then
        warn "检测到严重问题，执行应急响应..."
        "$SCRIPT_DIR/emergency-response.sh" check
    fi
}

# 执行监控检查
run_monitoring_check() {
    local total_issues=0
    local critical_issues=0

    info "开始自动化监控检查..."

    # 检查系统指标
    check_system_metrics
    local system_issues=$?
    ((total_issues += system_issues))

    # 检查应用指标
    check_application_metrics
    local app_issues=$?
    ((total_issues += app_issues))

    # 检查数据库指标
    check_database_metrics
    local db_issues=$?
    ((total_issues += db_issues))
    if [[ $db_issues -gt 0 ]]; then
        ((critical_issues++))
    fi

    # 检查缓存指标
    check_cache_metrics
    local cache_issues=$?
    ((total_issues += cache_issues))

    # 检查业务指标
    check_business_metrics
    local business_issues=$?
    ((total_issues += business_issues))

    # 总体评估
    if [[ $critical_issues -gt 0 ]]; then
        send_alert "系统异常" "发现 $critical_issues 个严重问题，总共 $total_issues 个问题" "critical"
        update_health_cache "critical"
    elif [[ $total_issues -gt 0 ]]; then
        send_alert "系统警告" "发现 $total_issues 个问题需要关注" "warning"
        update_health_cache "warning"
    else
        log "系统运行正常，未发现问题"
        update_health_cache "healthy"
    fi

    info "监控检查完成，发现问题: $total_issues 个 (严重: $critical_issues 个)"
}

# 生成监控摘要
generate_monitoring_summary() {
    local summary_file="$PROJECT_ROOT/logs/monitoring-summary-$(date +%Y%m%d).md"

    cat > "$summary_file" << EOF
# 监控摘要报告 - $(date +%Y-%m-%d)

## 系统状态概览

### 检查结果统计
- 检查时间: $(date)
- 系统问题: $(check_system_metrics > /dev/null && echo "正常" || echo "异常")
- 应用问题: $(check_application_metrics > /dev/null && echo "正常" || echo "异常")
- 数据库问题: $(check_database_metrics > /dev/null && echo "正常" || echo "异常")
- 缓存问题: $(check_cache_metrics > /dev/null && echo "正常" || echo "异常")
- 业务问题: $(check_business_metrics > /dev/null && echo "正常" || echo "异常")

### 关键指标
- CPU使用率: $(get_metric_value "100 * (1 - avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])))")%
- 内存使用率: $(get_metric_value "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100")%
- API错误率: $(get_metric_value "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100")%
- P95响应时间: $(get_metric_value "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))")s

### 告警记录
\`\`\`
$(tail -20 "$ALERT_LOG" 2>/dev/null || echo "暂无告警记录")
\`\`\`

---
报告生成时间: $(date)
EOF

    log "监控摘要报告已生成: $summary_file"
}

# 清理过期日志
cleanup_old_logs() {
    # 清理30天前的监控日志
    find "$PROJECT_ROOT/logs" -name "auto-monitoring-*.log" -mtime +30 -delete 2>/dev/null || true
    find "$PROJECT_ROOT/logs" -name "monitoring-*.log" -mtime +30 -delete 2>/dev/null || true

    # 清理旧的缓存文件
    find "$PROJECT_ROOT/.cache" -name "*.json" -mtime +7 -delete 2>/dev/null || true

    log "过期日志清理完成"
}

# 后台监控进程
start_background_monitoring() {
    info "启动后台监控进程，监控间隔: ${MONITORING_INTERVAL}秒"

    while true; do
        run_monitoring_check
        sleep "$MONITORING_INTERVAL"
    done
}

# 停止后台监控
stop_background_monitoring() {
    local pid_file="$PROJECT_ROOT/.cache/auto-monitoring.pid"

    if [[ -f "$pid_file" ]]; then
        local monitor_pid
        monitor_pid=$(cat "$pid_file")
        if kill -0 "$monitor_pid" 2>/dev/null; then
            kill "$monitor_pid"
            rm -f "$pid_file"
            log "后台监控进程已停止 (PID: $monitor_pid)"
        else
            warn "监控进程不存在，清理PID文件"
            rm -f "$pid_file"
        fi
    else
        warn "未找到监控进程PID文件"
    fi
}

# 检查监控进程状态
check_monitoring_status() {
    local pid_file="$PROJECT_ROOT/.cache/auto-monitoring.pid"

    if [[ -f "$pid_file" ]]; then
        local monitor_pid
        monitor_pid=$(cat "$pid_file")
        if kill -0 "$monitor_pid" 2>/dev/null; then
            log "后台监控进程正在运行 (PID: $monitor_pid)"
            return 0
        else
            warn "监控进程已停止，清理PID文件"
            rm -f "$pid_file"
            return 1
        fi
    else
        warn "后台监控进程未运行"
        return 1
    fi
}

# 主函数
main() {
    local command="${1:-check}"

    setup_directories

    case "$command" in
        "check")
            run_monitoring_check
            ;;
        "start")
            stop_background_monitoring  # 先停止现有进程
            start_background_monitoring &
            echo $! > "$PROJECT_ROOT/.cache/auto-monitoring.pid"
            log "后台监控已启动"
            ;;
        "stop")
            stop_background_monitoring
            ;;
        "status")
            check_monitoring_status
            ;;
        "summary")
            generate_monitoring_summary
            ;;
        "cleanup")
            cleanup_old_logs
            ;;
        "daemon")
            # 用于systemd服务模式
            start_background_monitoring
            ;;
        *)
            echo "使用方法: $0 {check|start|stop|status|summary|cleanup|daemon}"
            echo "  check    - 执行一次监控检查"
            echo "  start    - 启动后台监控进程"
            echo "  stop     - 停止后台监控进程"
            echo "  status   - 检查监控进程状态"
            echo "  summary  - 生成监控摘要报告"
            echo "  cleanup  - 清理过期日志"
            echo "  daemon   - 守护进程模式 (用于systemd)"
            exit 1
            ;;
    esac
}

# 信号处理
trap 'stop_background_monitoring; exit 0' SIGINT SIGTERM

# 执行主函数
main "$@"