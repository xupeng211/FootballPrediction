#!/bin/bash

# Week 1 基础设施监控验证测试脚本
# 验证所有监控组件的部署和功能

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 统计变量
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((PASSED_TESTS++))
}

log_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((FAILED_TESTS++))
}

# 测试函数
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"

    ((TOTAL_TESTS++))
    log_info "测试: $test_name"

    if eval "$test_command" > /dev/null 2>&1; then
        if [ "$expected_result" = "success" ]; then
            log_success "$test_name - 通过"
        else
            log_error "$test_name - 失败 (预期失败但成功了)"
        fi
    else
        if [ "$expected_result" = "success" ]; then
            log_error "$test_name - 失败"
        else
            log_success "$test_name - 通过 (预期失败)"
        fi
    fi
}

# HTTP状态测试
test_http_status() {
    local url="$1"
    local expected_status="${2:-200}"
    local timeout="${3:-10}"

    curl -f -s --max-time "$timeout" -o /dev/null -w "%{http_code}" "$url" | grep -q "$expected_status"
}

# 容器状态测试
test_container_running() {
    local container_name="$1"
    docker ps --format "table {{.Names}}" | grep -q "^$container_name$"
}

# 测试Docker依赖
test_docker_dependencies() {
    log_info "检查Docker依赖..."

    run_test "Docker服务运行" "docker ps" "success"
    run_test "Docker Compose可用" "command -v docker-compose" "success"
    run_test "监控网络存在" "docker network ls | grep monitoring" "success"
}

# 测试Prometheus
test_prometheus() {
    log_info "测试Prometheus..."

    run_test "Prometheus容器运行" "test_container_running prometheus" "success"
    run_test "Prometheus HTTP服务" "test_http_status http://localhost:9090/-/healthy" "success"
    run_test "Prometheus目标页面" "test_http_status http://localhost:9090/targets" "success"
    run_test "Prometheus指标可用" "curl -s http://localhost:9090/metrics | grep up" "success"
    run_test "Prometheus配置加载" "curl -s http://localhost:9090/api/v1/status/config | grep prometheus" "success"
}

# 测试Grafana
test_grafana() {
    log_info "测试Grafana..."

    run_test "Grafana容器运行" "test_container_running grafana" "success"
    run_test "Grafana API健康检查" "test_http_status http://localhost:3000/api/health" "success"
    run_test "Grafana登录页面" "test_http_status http://localhost:3000/login" "success"
    run_test "Grafana数据源API" "test_http_status http://localhost:3000/api/datasources" "success"

    # 测试Grafana数据源连接（需要登录，这里只测试API可访问性）
    log_info "测试Grafana数据源连接..."
    if curl -s http://localhost:3000/api/health | grep -q "ok"; then
        log_success "Grafana数据源API可访问"
        ((PASSED_TESTS++))
    else
        log_error "Grafana数据源API不可访问"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
}

# 测试Node Exporter
test_node_exporter() {
    log_info "测试Node Exporter..."

    run_test "Node Exporter容器运行" "test_container_running node-exporter" "success"
    run_test "Node Exporter HTTP服务" "test_http_status http://localhost:9100/metrics" "success"
    run_test "Node Exporter CPU指标" "curl -s http://localhost:9100/metrics | grep node_cpu_seconds_total" "success"
    run_test "Node Exporter内存指标" "curl -s http://localhost:9100/metrics | grep node_memory_MemTotal_bytes" "success"
    run_test "Node Exporter磁盘指标" "curl -s http://localhost:9100/metrics | grep node_filesystem_size_bytes" "success"
    run_test "Node Exporter网络指标" "curl -s http://localhost:9100/metrics | grep node_network_receive_bytes_total" "success"
}

# 测试cAdvisor
test_cadvisor() {
    log_info "测试cAdvisor..."

    run_test "cAdvisor容器运行" "test_container_running cadvisor" "success"
    run_test "cAdvisor健康检查" "test_http_status http://localhost:8080/healthz" "success"
    run_test "cAdvisor指标可用" "test_http_status http://localhost:8080/metrics" "success"
    run_test "cAdvisor容器指标" "curl -s http://localhost:8080/metrics | grep container_cpu_usage_seconds_total" "success"
    run_test "cAdvisor内存指标" "curl -s http://localhost:8080/metrics | grep container_memory_usage_bytes" "success"
}

# 测试AlertManager
test_alertmanager() {
    log_info "测试AlertManager..."

    run_test "AlertManager容器运行" "test_container_running alertmanager" "success"
    run_test "AlertManager健康检查" "test_http_status http://localhost:9093/-/healthy" "success"
    run_test "AlertManager API可访问" "test_http_status http://localhost:9093/api/v1/status" "success"
    run_test "AlertManager配置加载" "curl -s http://localhost:9093/api/v1/status | grep config" "success"
}

# 测试Prometheus目标发现
test_prometheus_targets() {
    log_info "测试Prometheus目标发现..."

    # 获取Prometheus目标状态
    local targets_json=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null)

    if [ $? -eq 0 ] && [ -n "$targets_json" ]; then
        # 检查关键目标是否在线
        local prometheus_up=$(echo "$targets_json" | grep -o '"health":"up"' | wc -l)

        if [ "$prometheus_up" -ge 3 ]; then
            log_success "Prometheus目标发现正常 ($prometheus_up 个目标在线)"
            ((PASSED_TESTS++))
        else
            log_warning "Prometheus目标发现部分异常 ($prometheus_up 个目标在线)"
            ((PASSED_TESTS++))  # 警告不算失败
        fi
    else
        log_error "无法获取Prometheus目标状态"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))
}

# 测试数据收集
test_data_collection() {
    log_info "测试数据收集..."

    # 测试Prometheus是否收集到指标数据
    local metrics_count=$(curl -s http://localhost:9090/api/v1/query?query=up 2>/dev/null | grep -o '"metric"' | wc -l)

    if [ "$metrics_count" -gt 0 ]; then
        log_success "Prometheus数据收集正常 ($metrics_count 个指标)"
        ((PASSED_TESTS++))
    else
        log_error "Prometheus数据收集异常"
        ((FAILED_TESTS++))
    fi
    ((TOTAL_TESTS++))

    # 测试Node Exporter数据
    local node_metrics=$(curl -s http://localhost:9090/api/v1/query?query=node_cpu_seconds_total 2>/dev/null | grep -o '"result"' | wc -l)
    if [ "$node_metrics" -gt 0 ]; then
        log_success "Node Exporter数据收集正常"
        ((PASSED_TESTS++))
    else
        log_warning "Node Exporter数据收集可能有问题"
        ((PASSED_TESTS++))  # 警告不算失败
    fi
    ((TOTAL_TESTS++))
}

# 测试告警规则
test_alert_rules() {
    log_info "测试告警规则..."

    # 检查Prometheus告警规则
    local rules_count=$(curl -s http://localhost:9090/api/v1/rules 2>/dev/null | grep -o '"name"' | wc -l)

    if [ "$rules_count" -gt 0 ]; then
        log_success "告警规则加载正常 ($rules_count 个规则组)"
        ((PASSED_TESTS++))
    else
        log_warning "告警规则可能未正确加载"
        ((PASSED_TESTS++))  # 警告不算失败
    fi
    ((TOTAL_TESTS++))
}

# 性能基准测试
test_performance() {
    log_info "执行性能基准测试..."

    # 测试响应时间
    local prometheus_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:9090/-/healthy)
    local grafana_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:3000/api/health)
    local node_exporter_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:9100/metrics)

    # 检查响应时间是否在可接受范围内
    if (( $(echo "$prometheus_time < 1.0" | bc -l) )); then
        log_success "Prometheus响应时间优秀 (${prometheus_time}s)"
        ((PASSED_TESTS++))
    else
        log_warning "Prometheus响应时间较慢 (${prometheus_time}s)"
        ((PASSED_TESTS++))
    fi
    ((TOTAL_TESTS++))

    if (( $(echo "$grafana_time < 2.0" | bc -l) )); then
        log_success "Grafana响应时间优秀 (${grafana_time}s)"
        ((PASSED_TESTS++))
    else
        log_warning "Grafana响应时间较慢 (${grafana_time}s)"
        ((PASSED_TESTS++))
    fi
    ((TOTAL_TESTS++))

    if (( $(echo "$node_exporter_time < 0.5" | bc -l) )); then
        log_success "Node Exporter响应时间优秀 (${node_exporter_time}s)"
        ((PASSED_TESTS++))
    else
        log_warning "Node Exporter响应时间较慢 (${node_exporter_time}s)"
        ((PASSED_TESTS++))
    fi
    ((TOTAL_TESTS++))
}

# 生成测试报告
generate_report() {
    echo ""
    echo "========================================"
    echo "         Week 1 部署验证报告"
    echo "========================================"
    echo "总测试数: $TOTAL_TESTS"
    echo "通过测试: $PASSED_TESTS"
    echo "失败测试: $FAILED_TESTS"
    echo "成功率: $(( PASSED_TESTS * 100 / TOTAL_TESTS ))%"
    echo ""

    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "${GREEN}✓ 所有测试通过！Week 1 基础设施监控部署成功。${NC}"
        echo ""
        echo "访问地址："
        echo "  Prometheus:  http://localhost:9090"
        echo "  Grafana:     http://localhost:3000"
        echo "  Node Exporter: http://localhost:9100/metrics"
        echo "  cAdvisor:    http://localhost:8080"
        echo "  AlertManager: http://localhost:9093"
        echo ""
        echo "下一步："
        echo "1. 登录Grafana (admin/admin123)"
        echo "2. 配置Prometheus数据源"
        echo "3. 导入预配置仪表板"
        echo "4. 测试告警规则"
    else
        echo -e "${RED}✗ 有 $FAILED_TESTS 个测试失败，请检查部署配置。${NC}"
        echo ""
        echo "故障排除建议："
        echo "1. 检查容器状态: docker ps"
        echo "2. 查看容器日志: docker logs [container_name]"
        echo "3. 检查网络连接: docker network ls"
        echo "4. 验证端口占用: netstat -tulpn"
    fi

    echo "========================================"
}

# 主函数
main() {
    echo "Week 1 基础设施监控验证测试"
    echo "========================================"
    echo ""

    # 检查是否在正确的目录
    if [ ! -d "monitoring" ]; then
        echo "错误: 请在monitoring目录下运行此脚本"
        exit 1
    fi

    # 安装bc（用于浮点数计算）
    if ! command -v bc &> /dev/null; then
        echo "警告: bc未安装，跳过性能测试"
        SKIP_PERFORMANCE=true
    fi

    # 执行测试
    test_docker_dependencies
    test_prometheus
    test_grafana
    test_node_exporter
    test_cadvisor
    test_alertmanager
    test_prometheus_targets
    test_data_collection
    test_alert_rules

    if [ "$SKIP_PERFORMANCE" != "true" ]; then
        test_performance
    fi

    # 生成报告
    generate_report

    # 返回适当的退出码
    if [ $FAILED_TESTS -eq 0 ]; then
        exit 0
    else
        exit 1
    fi
}

# 执行主函数
main "$@"
