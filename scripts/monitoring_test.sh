#!/bin/bash
# 监控系统测试脚本
# Monitoring System Test Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置参数
LOG_FILE="/var/log/monitoring-test.log"
TEST_TIMEOUT=30
PROMETHEUS_URL="http://localhost:9090"
GRAFANA_URL="http://localhost:3000"
ALERTMANAGER_URL="http://localhost:9093"

# 日志函数
log_info() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')] INFO:${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')] SUCCESS:${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" | tee -a "$LOG_FILE"
}

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
run_test() {
    local test_name="$1"
    local test_command="$2"

    ((TOTAL_TESTS++))
    log_info "执行测试: $test_name"

    if eval "$test_command" >/dev/null 2>&1; then
        log_success "✓ $test_name - 通过"
        ((PASSED_TESTS++))
        return 0
    else
        log_error "✗ $test_name - 失败"
        ((FAILED_TESTS++))
        return 1
    fi
}

# 测试HTTP端点可用性
test_http_endpoint() {
    local url="$1"
    local description="$2"

    run_test "$description" "curl -f -s --max-time $TEST_TIMEOUT '$url'"
}

# 测试Prometheus
test_prometheus() {
    log_info "测试Prometheus监控系统..."

    # 测试Prometheus主页面
    test_http_endpoint "$PROMETHEUS_URL" "Prometheus主页访问"

    # 测试Prometheus健康状态
    test_http_endpoint "$PROMETHEUS_URL/-/healthy" "Prometheus健康检查"

    # 测试Prometheus目标状态
    test_http_endpoint "$PROMETHEUS_URL/api/v1/targets" "Prometheus目标状态"

    # 测试Prometheus查询API
    test_http_endpoint "$PROMETHEUS_URL/api/v1/query?query=up" "Prometheus查询API"

    # 检查关键指标
    run_test "Prometheus指标收集" "curl -s '$PROMETHEUS_URL/api/v1/query?query=up' | grep -q '\"result\"'"

    log_success "Prometheus测试完成"
}

# 测试Grafana
test_grafana() {
    log_info "测试Grafana可视化系统..."

    # 测试Grafana主页
    test_http_endpoint "$GRAFANA_URL" "Grafana主页访问"

    # 测试GrafanaAPI健康状态
    test_http_endpoint "$GRAFANA_URL/api/health" "Grafana API健康检查"

    # 测试Grafana数据源
    run_test "Grafana数据源配置" "curl -s '$GRAFANA_URL/api/datasources' | grep -q '\"datasources\"'"

    # 测试Grafana仪表板
    run_test "Grafana仪表板加载" "curl -s '$GRAFANA_URL/api/search' | grep -q '\"dashboards\"'"

    log_success "Grafana测试完成"
}

# 测试AlertManager
test_alertmanager() {
    log_info "测试AlertManager告警系统..."

    # 测试AlertManager主页
    test_http_endpoint "$ALERTMANAGER_URL" "AlertManager主页访问"

    # 测试AlertManager API
    test_http_endpoint "$ALERTMANAGER_URL/api/v1/status" "AlertManager API状态"

    # 测试告警规则
    run_test "AlertManager告警规则" "curl -s '$ALERTMANAGER_URL/api/v1/rules' | grep -q '\"groups\"'"

    # 测试告警状态
    run_test "AlertManager告警状态" "curl -s '$ALERTMANAGER_URL/api/v1/alerts' | grep -q '\"data\"'"

    log_success "AlertManager测试完成"
}

# 测试应用指标
test_application_metrics() {
    log_info "测试应用指标收集..."

    # 测试应用健康状态
    run_test "应用健康状态" "curl -f -s 'http://localhost:8000/health'"

    # 测试应用指标端点
    test_http_endpoint "http://localhost:8000/metrics" "应用指标端点"

    # 检查关键应用指标
    run_test "应用HTTP指标" "curl -s 'http://localhost:8000/metrics' | grep -q 'http_requests_total'"
    run_test "应用响应时间指标" "curl -s 'http://localhost:8000/metrics' | grep -q 'http_request_duration_seconds'"

    log_success "应用指标测试完成"
}

# 测试Nginx监控
test_nginx_monitoring() {
    log_info "测试Nginx监控..."

    # 测试Nginx状态页面
    test_http_endpoint "http://localhost/nginx_status" "Nginx状态页面"

    # 测试Nginx指标（如果有nginx-exporter）
    test_http_endpoint "http://localhost:9113/metrics" "Nginx指标收集"

    # 检查Nginx连接状态
    run_test "Nginx连接状态" "curl -s 'http://localhost/nginx_status' | grep -q 'Active connections'"

    log_success "Nginx监控测试完成"
}

# 测试数据库监控
test_database_monitoring() {
    log_info "测试数据库监控..."

    # 测试PostgreSQL Exporter
    test_http_endpoint "http://localhost:9187/metrics" "PostgreSQL指标收集"

    # 检查PostgreSQL关键指标
    run_test "PostgreSQL连接指标" "curl -s 'http://localhost:9187/metrics' | grep -q 'pg_stat_database_numbackends'"
    run_test "PostgreSQL事务指标" "curl -s 'http://localhost:9187/metrics' | grep -q 'pg_stat_database_xact_commit'"

    log_success "数据库监控测试完成"
}

# 测试Redis监控
test_redis_monitoring() {
    log_info "测试Redis监控..."

    # 测试Redis Exporter
    test_http_endpoint "http://localhost:9121/metrics" "Redis指标收集"

    # 检查Redis关键指标
    run_test "Redis内存指标" "curl -s 'http://localhost:9121/metrics' | grep -q 'redis_memory_used_bytes'"
    run_test "Redis连接指标" "curl -s 'http://localhost:9121/metrics' | grep -q 'redis_connected_clients'"

    log_success "Redis监控测试完成"
}

# 测试告警规则
test_alert_rules() {
    log_info "测试告警规则..."

    # 检查Prometheus告警规则加载
    run_test "Prometheus告警规则加载" "curl -s '$PROMETHEUS_URL/api/v1/rules' | grep -q '\"rules\"'"

    # 检查告警规则评估
    run_test "告警规则评估" "curl -s '$PROMETHEUS_URL/api/v1/alerts' | grep -q '\"alerts\"'"

    # 测试关键告警规则
    local alert_types=("HighCPUUsage" "HighMemoryUsage" "ApplicationDown" "HighErrorRate")
    for alert in "${alert_types[@]}"; do
        run_test "告警规则 $alert" "curl -s '$PROMETHEUS_URL/api/v1/rules' | grep -q '$alert'"
    done

    log_success "告警规则测试完成"
}

# 测试日志聚合
test_log_aggregation() {
    log_info "测试日志聚合系统..."

    # 测试Loki（如果配置）
    test_http_endpoint "http://localhost:3100/ready" "Loki就绪状态"

    # 测试日志查询
    run_test "Loki日志查询" "curl -s 'http://localhost:3100/loki/api/v1/label' | grep -q '\"status\":\"success\"'"

    log_success "日志聚合测试完成"
}

# 性能基准测试
performance_benchmark() {
    log_info "执行性能基准测试..."

    # Prometheus查询性能
    local prometheus_query_time=$(curl -s -w '%{time_total}' -o /dev/null "$PROMETHEUS_URL/api/v1/query?query=up")
    if (( $(echo "$prometheus_query_time < 1.0" | bc -l) )); then
        log_success "Prometheus查询性能: ${prometheus_query_time}s (< 1.0s)"
        ((PASSED_TESTS++))
    else
        log_warning "Prometheus查询性能: ${prometheus_query_time}s (>= 1.0s)"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))

    # Grafana加载性能
    local grafana_load_time=$(curl -s -w '%{time_total}' -o /dev/null "$GRAFANA_URL/api/dashboards/home")
    if (( $(echo "$grafana_load_time < 2.0" | bc -l) )); then
        log_success "Grafana加载性能: ${grafana_load_time}s (< 2.0s)"
        ((PASSED_TESTS++))
    else
        log_warning "Grafana加载性能: ${grafana_load_time}s (>= 2.0s)"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))

    log_success "性能基准测试完成"
}

# 生成测试报告
generate_test_report() {
    local report_file="/var/log/monitoring-test-report-$(date +%Y%m%d_%H%M%S).txt"

    log_info "生成测试报告: $report_file"

    {
        echo "==================== 监控系统测试报告 ===================="
        echo "测试时间: $(date)"
        echo "主机名: $(hostname)"
        echo ""

        echo "==================== 测试结果统计 ===================="
        echo "总测试数: $TOTAL_TESTS"
        echo "通过测试: $PASSed_TESTS"
        echo "失败测试: $FAILED_TESTS"
        echo "成功率: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
        echo ""

        echo "==================== 系统信息 ===================="
        echo "操作系统: $(uname -a)"
        echo "系统负载: $(uptime)"
        echo "内存使用: $(free -h)"
        echo "磁盘使用: $(df -h /)"
        echo ""

        echo "==================== 服务状态 ===================="
        echo "Prometheus: $(systemctl is-active prometheus 2>/dev/null || echo '未知')"
        echo "Grafana: $(systemctl is-active grafana-server 2>/dev/null || echo '未知')"
        echo "AlertManager: $(systemctl is-active alertmanager 2>/dev/null || echo '未知')"
        echo "Nginx: $(systemctl is-active nginx 2>/dev/null || echo '未知')"
        echo ""

        echo "==================== 端口监听状态 ===================="
        netstat -tlnp | grep -E ':(80|443|3000|9090|9093|9100|9113|9187|9121)' | head -10
        echo ""

        echo "==================== Docker容器状态 ===================="
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -10
        echo ""

        echo "报告生成时间: $(date)"
    } > "$report_file"

    log_success "测试报告已生成: $report_file"
}

# 主测试流程
main_test_suite() {
    log_info "开始监控系统全面测试..."

    # 创建日志目录
    mkdir -p "$(dirname "$LOG_FILE")"

    # 基础连接测试
    test_prometheus
    test_grafana
    test_alertmanager

    # 应用监控测试
    test_application_metrics
    test_nginx_monitoring
    test_database_monitoring
    test_redis_monitoring

    # 告警系统测试
    test_alert_rules

    # 日志系统测试
    test_log_aggregation

    # 性能测试
    performance_benchmark

    # 生成报告
    generate_test_report

    # 输出测试总结
    echo ""
    echo "==================== 测试总结 ===================="
    log_success "监控系统测试完成"
    echo "总测试数: $TOTAL_TESTS"
    echo "通过测试: $PASSED_TESTS"
    echo "失败测试: $FAILED_TESTS"
    echo "成功率: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"

    if [ "$FAILED_TESTS" -eq 0 ]; then
        log_success "所有测试通过！监控系统运行正常。"
        return 0
    else
        log_warning "有 $FAILED_TESTS 个测试失败，请检查相关配置。"
        return 1
    fi
}

# 快速健康检查
quick_health_check() {
    log_info "执行快速健康检查..."

    local critical_services=("Prometheus:$PROMETHEUS_URL/-/healthy" "Grafana:$GRAFANA_URL/api/health" "Application:http://localhost:8000/health")

    for service in "${critical_services[@]}"; do
        local name=$(echo "$service" | cut -d: -f1)
        local url=$(echo "$service" | cut -d: -f2-)

        if curl -f -s --max-time 10 "$url" >/dev/null; then
            log_success "✓ $name - 健康"
        else
            log_error "✗ $name - 不可用"
        fi
    done
}

# 使用说明
show_usage() {
    echo "监控系统测试脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  full           执行完整测试套件（默认）"
    echo "  quick          执行快速健康检查"
    echo "  prometheus     仅测试Prometheus"
    echo "  grafana        仅测试Grafana"
    echo "  alertmanager   仅测试AlertManager"
    echo "  application    仅测试应用监控"
    echo "  report         仅生成测试报告"
    echo "  help           显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 full        # 完整测试"
    echo "  $0 quick       # 快速检查"
    echo "  $0 prometheus  # 仅测试Prometheus"
}

# 主函数
main() {
    case "${1:-full}" in
        "full")
            main_test_suite
            ;;
        "quick")
            quick_health_check
            ;;
        "prometheus")
            test_prometheus
            ;;
        "grafana")
            test_grafana
            ;;
        "alertmanager")
            test_alertmanager
            ;;
        "application")
            test_application_metrics
            ;;
        "report")
            generate_test_report
            ;;
        "help"|"-h"|"--help")
            show_usage
            ;;
        *)
            log_error "未知选项: $1"
            show_usage
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"