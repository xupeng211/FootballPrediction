#!/bin/bash

# 监控仪表板脚本
# Monitoring Dashboard Script

set -euo pipefail

# 配置变量
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3000"
GRAFANA_USER="admin"
GRAFANA_PASSWORD="${GRAFANA_PASSWORD:-admin}"
REPORT_DIR="$PROJECT_ROOT/monitoring-reports"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# 创建报告目录
setup_directories() {
    mkdir -p "$REPORT_DIR/daily" "$REPORT_DIR/weekly" "$REPORT_DIR/monthly"
}

# 检查Prometheus连接
check_prometheus() {
    if curl -s -f "$PROMETHEUS_URL/-/healthy" > /dev/null; then
        log "Prometheus连接正常"
        return 0
    else
        warn "Prometheus连接失败"
        return 1
    fi
}

# 检查Grafana连接
check_grafana() {
    if curl -s -f "$GRAFANA_URL/api/health" > /dev/null; then
        log "Grafana连接正常"
        return 0
    else
        warn "Grafana连接失败"
        return 1
    fi
}

# 查询Prometheus指标
query_prometheus() {
    local query="$1"
    local description="$2"

    if check_prometheus; then
        local result
        result=$(curl -s -G --data-urlencode "query=$query" "$PROMETHEUS_URL/api/v1/query" | jq -r '.data.result[0].value[1]' 2>/dev/null || echo "N/A")

        if [[ "$result" != "null" && "$result" != "N/A" ]]; then
            printf "%-25s: %s\n" "$description" "$result"
        else
            printf "%-25s: %s\n" "$description" "无数据"
        fi
    else
        printf "%-25s: %s\n" "$description" "查询失败"
    fi
}

# 获取系统指标
get_system_metrics() {
    echo -e "\n${BLUE}🖥️  系统指标${NC}"
    echo "===================="

    # CPU使用率
    query_prometheus "100 * (1 - avg(rate(node_cpu_seconds_total{mode=\"idle\"}[5m])))" "CPU使用率(%)"

    # 内存使用率
    query_prometheus "(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100" "内存使用率(%)"

    # 磁盘使用率
    query_prometheus "(1 - (node_filesystem_avail_bytes / node_filesystem_size_bytes)) * 100" "磁盘使用率(%)"

    # 网络流量
    query_prometheus "rate(node_network_receive_bytes_total[5m]) * 8 / 1024 / 1024" "网络接收(Mbps)"
    query_prometheus "rate(node_network_transmit_bytes_total[5m]) * 8 / 1024 / 1024" "网络发送(Mbps)"
}

# 获取应用指标
get_application_metrics() {
    echo -e "\n${BLUE}🚀 应用指标${NC}"
    echo "===================="

    # HTTP请求数量
    query_prometheus "rate(http_requests_total[5m])" "请求速率(RPS)"

    # HTTP错误率
    query_prometheus "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100" "错误率(%)"

    # 响应时间P95
    query_prometheus "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) * 1000" "P95响应时间(ms)"

    # 响应时间P99
    query_prometheus "histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) * 1000" "P99响应时间(ms)"

    # 应用正常运行时间
    query_prometheus "time() - process_start_time_seconds" "应用运行时间(s)"
}

# 获取数据库指标
get_database_metrics() {
    echo -e "\n${BLUE}🗄️  数据库指标${NC}"
    echo "===================="

    # 数据库连接数
    query_prometheus "pg_stat_database_numbackends" "活跃连接数"

    # 数据库事务率
    query_prometheus "rate(pg_stat_database_xact_commit_total[5m])" "提交事务/秒"

    # 数据库回滚率
    query_prometheus "rate(pg_stat_database_xact_rollback_total[5m])" "回滚事务/秒"

    # 数据库大小
    query_prometheus "pg_database_size_bytes / 1024 / 1024 / 1024" "数据库大小(GB)"

    # 慢查询数量
    query_prometheus "pg_stat_statements_mean_time_seconds > 1" "慢查询数量"
}

# 获取缓存指标
get_cache_metrics() {
    echo -e "\n${BLUE}💾 缓存指标${NC}"
    echo "===================="

    # Redis连接数
    query_prometheus "redis_connected_clients" "Redis连接数"

    # Redis内存使用
    query_prometheus "redis_memory_used_bytes / 1024 / 1024" "Redis内存使用(MB)"

    # Redis命中率
    query_prometheus "rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) * 100" "缓存命中率(%)"

    # Redis操作速率
    query_prometheus "rate(redis_commands_processed_total[5m])" "操作速率(ops/s)"
}

# 获取业务指标
get_business_metrics() {
    echo -e "\n${BLUE}📊 业务指标${NC}"
    echo "===================="

    # 预测请求数
    query_prometheus "rate(prediction_requests_total[5m])" "预测请求/秒"

    # 预测成功率
    query_prometheus "rate(prediction_successful_total[5m]) / rate(prediction_requests_total[5m]) * 100" "预测成功率(%)"

    # 预测准确率
    query_prometheus "prediction_accuracy_rate * 100" "预测准确率(%)"

    # 活跃用户数
    query_prometheus "active_users_total" "活跃用户数"

    # 数据同步状态
    query_prometheus "data_sync_status" "数据同步状态"
}

# 检查告警状态
check_alerts() {
    echo -e "\n${BLUE}🚨 告警状态${NC}"
    echo "===================="

    if check_prometheus; then
        local active_alerts
        active_alerts=$(curl -s "$PROMETHEUS_URL/api/v1/alerts" | jq '.data.alerts | length' 2>/dev/null || echo "0")

        echo "活跃告警数量: $active_alerts"

        if [[ "$active_alerts" -gt 0 ]]; then
            echo -e "\n${YELLOW}当前活跃告警:${NC}"
            curl -s "$PROMETHEUS_URL/api/v1/alerts" | jq -r '.data.alerts[] | "  • \(.labels.alertname): \(.annotations.summary // .annotations.description)"' 2>/dev/null || echo "  无法获取告警详情"
        else
            echo -e "${GREEN}✅ 无活跃告警${NC}"
        fi
    fi
}

# 生成监控报告
generate_monitoring_report() {
    local report_type="${1:-daily}"
    local report_file
    local timestamp

    timestamp=$(date +%Y%m%d-%H%M%S)

    case "$report_type" in
        "daily")
            report_file="$REPORT_DIR/daily/monitoring-daily-$timestamp.md"
            ;;
        "weekly")
            report_file="$REPORT_DIR/weekly/monitoring-weekly-$timestamp.md"
            ;;
        "monthly")
            report_file="$REPORT_DIR/monthly/monitoring-monthly-$timestamp.md"
            ;;
        *)
            error "未知的报告类型: $report_type"
            return 1
            ;;
    esac

    log "生成 $report_type 监控报告: $report_file"

    cat > "$report_file" << EOF
# 监控报告 - $report_type

## 报告信息
- 生成时间: $(date)
- 报告类型: $report_type
- 系统版本: $(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

## 系统概览
\`\`\`
$(get_system_metrics 2>/dev/null)
\`\`\`

## 应用性能
\`\`\`
$(get_application_metrics 2>/dev/null)
\`\`\`

## 数据库状态
\`\`\`
$(get_database_metrics 2>/dev/null)
\`\`\`

## 缓存性能
\`\`\`
$(get_cache_metrics 2>/dev/null)
\`\`\`

## 业务指标
\`\`\`
$(get_business_metrics 2>/dev/null)
\`\`\`

## 告警状态
\`\`\`
$(check_alerts 2>/dev/null)
\`\`\`

## 总结和建议
[在此添加分析和建议]

---
报告生成时间: $(date)
EOF

    log "监控报告已生成: $report_file"
    echo "$report_file"
}

# 显示Grafana仪表板链接
show_grafana_links() {
    echo -e "\n${BLUE}📈 Grafana仪表板${NC}"
    echo "===================="

    if check_grafana; then
        echo -e "主要仪表板链接:"
        echo "• 系统概览: $GRAFANA_URL/d/system-overview"
        echo "• 应用性能: $GRAFANA_URL/d/application-performance"
        echo "• 数据库监控: $GRAFANA_URL/d/database-monitoring"
        echo "• 业务指标: $GRAFANA_URL/d/business-metrics"
        echo ""
        echo "访问信息:"
        echo "• URL: $GRAFANA_URL"
        echo "• 用户名: $GRAFANA_USER"
        echo "• 密码: [已配置]"
    else
        warn "Grafana不可用，请检查服务状态"
    fi
}

# 健康检查总结
health_summary() {
    echo -e "\n${PURPLE}🏥 系统健康总结${NC}"
    echo "===================="

    local health_score=0
    local max_score=5

    # 检查Prometheus
    if check_prometheus; then
        echo -e "✅ Prometheus: 正常"
        ((health_score++))
    else
        echo -e "❌ Prometheus: 异常"
    fi

    # 检查Grafana
    if check_grafana; then
        echo -e "✅ Grafana: 正常"
        ((health_score++))
    else
        echo -e "❌ Grafana: 异常"
    fi

    # 检查应用健康状态
    if curl -s -f http://localhost/health/ > /dev/null; then
        echo -e "✅ 应用服务: 正常"
        ((health_score++))
    else
        echo -e "❌ 应用服务: 异常"
    fi

    # 检查数据库连接
    if docker-compose exec -T db pg_isready -U prod_user > /dev/null 2>&1; then
        echo -e "✅ 数据库: 正常"
        ((health_score++))
    else
        echo -e "❌ 数据库: 异常"
    fi

    # 检查缓存连接
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo -e "✅ 缓存服务: 正常"
        ((health_score++))
    else
        echo -e "❌ 缓存服务: 异常"
    fi

    # 计算健康分数
    local health_percentage=$((health_score * 100 / max_score))
    echo -e "\n健康评分: $health_score/$max_score ($health_percentage%)"

    if [[ $health_percentage -ge 80 ]]; then
        echo -e "${GREEN}🟢 系统状态: 健康${NC}"
    elif [[ $health_percentage -ge 60 ]]; then
        echo -e "${YELLOW}🟡 系统状态: 警告${NC}"
    else
        echo -e "${RED}🔴 系统状态: 异常${NC}"
    fi
}

# 主函数
main() {
    local command="${1:-overview}"
    local report_type="${2:-daily}"

    setup_directories

    case "$command" in
        "overview")
            echo -e "${PURPLE}🔍 足球预测系统监控仪表板${NC}"
            echo "=================================="
            get_system_metrics
            get_application_metrics
            get_database_metrics
            get_cache_metrics
            get_business_metrics
            check_alerts
            health_summary
            show_grafana_links
            ;;
        "system")
            get_system_metrics
            ;;
        "application")
            get_application_metrics
            ;;
        "database")
            get_database_metrics
            ;;
        "cache")
            get_cache_metrics
            ;;
        "business")
            get_business_metrics
            ;;
        "alerts")
            check_alerts
            ;;
        "health")
            health_summary
            ;;
        "report")
            generate_monitoring_report "$report_type"
            ;;
        "links")
            show_grafana_links
            ;;
        *)
            echo "使用方法: $0 {overview|system|application|database|cache|business|alerts|health|report|links} [report_type]"
            echo "  overview    - 显示完整监控概览"
            echo "  system      - 显示系统指标"
            echo "  application - 显示应用指标"
            echo "  database    - 显示数据库指标"
            echo "  cache       - 显示缓存指标"
            echo "  business    - 显示业务指标"
            echo "  alerts      - 显示告警状态"
            echo "  health      - 显示健康总结"
            echo "  report      - 生成监控报告 (daily|weekly|monthly)"
            echo "  links       - 显示Grafana仪表板链接"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"