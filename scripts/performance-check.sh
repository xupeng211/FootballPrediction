#!/bin/bash

# 性能检查脚本
# Performance Check Script

set -euo pipefail

# 配置变量
BASE_URL="http://localhost"
API_URL="$BASE_URL/api/v1"
HEALTH_URL="$BASE_URL/health"
TIMEOUT=30
WARN_THRESHOLD=0.5
CRITICAL_THRESHOLD=2.0

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 检查URL响应时间
check_response_time() {
    local url="$1"
    local description="$2"

    info "检查 $description 响应时间..."

    local response_time
    response_time=$(curl -o /dev/null -s -w '%{time_total}' --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "999")

    if (( $(echo "$response_time >= $CRITICAL_THRESHOLD" | bc -l) )); then
        error "$description 响应时间过长: ${response_time}s (阈值: ${CRITICAL_THRESHOLD}s)"
        return 2
    elif (( $(echo "$response_time >= $WARN_THRESHOLD" | bc -l) )); then
        warn "$description 响应时间较慢: ${response_time}s (警告阈值: ${WARN_THRESHOLD}s)"
        return 1
    else
        log "$description 响应时间正常: ${response_time}s"
        return 0
    fi
}

# 检查HTTP状态码
check_http_status() {
    local url="$1"
    local description="$2"
    local expected_status="${3:-200}"

    info "检查 $description HTTP状态..."

    local status_code
    status_code=$(curl -o /dev/null -s -w '%{http_code}' --max-time "$TIMEOUT" "$url" 2>/dev/null || echo "000")

    if [[ "$status_code" -eq "$expected_status" ]]; then
        log "$description HTTP状态正常: $status_code"
        return 0
    else
        error "$description HTTP状态异常: $status_code (期望: $expected_status)"
        return 1
    fi
}

# 检查系统资源
check_system_resources() {
    info "检查系统资源使用情况..."

    # CPU使用率
    local cpu_usage
    cpu_usage=$(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        warn "CPU使用率较高: ${cpu_usage}%"
    else
        log "CPU使用率正常: ${cpu_usage}%"
    fi

    # 内存使用率
    local mem_usage
    mem_usage=$(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')
    if (( $(echo "$mem_usage > 80" | bc -l) )); then
        warn "内存使用率较高: ${mem_usage}%"
    else
        log "内存使用率正常: ${mem_usage}%"
    fi

    # 磁盘使用率
    local disk_usage
    disk_usage=$(df -h / | awk 'NR==2 {print $5}' | sed 's/%//')
    if [[ $disk_usage -gt 85 ]]; then
        warn "磁盘使用率较高: ${disk_usage}%"
    else
        log "磁盘使用率正常: ${disk_usage}%"
    fi
}

# 检查Docker容器状态
check_docker_containers() {
    info "检查Docker容器状态..."

    local containers
    containers=$(docker-compose ps --services --filter "status=running")

    if [[ -z "$containers" ]]; then
        error "没有运行中的Docker容器"
        return 1
    fi

    local container_count
    container_count=$(echo "$containers" | wc -l)
    log "运行中的容器数量: $container_count"

    # 检查具体容器状态
    local service_names=("app" "db" "redis" "nginx" "prometheus" "grafana")
    for service in "${service_names[@]}"; do
        if docker-compose ps | grep -q "$service.*Up"; then
            log "容器 $service 运行正常"
        else
            warn "容器 $service 未运行或状态异常"
        fi
    done
}

# 检查数据库连接
check_database_connection() {
    info "检查数据库连接..."

    if docker-compose ps | grep -q "db.*Up"; then
        if docker-compose exec -T db pg_isready -U prod_user > /dev/null 2>&1; then
            log "数据库连接正常"
        else
            error "数据库连接失败"
            return 1
        fi
    else
        warn "数据库容器未运行"
    fi
}

# 检查Redis连接
check_redis_connection() {
    info "检查Redis连接..."

    if docker-compose ps | grep -q "redis.*Up"; then
        if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
            log "Redis连接正常"
        else
            error "Redis连接失败"
            return 1
        fi
    else
        warn "Redis容器未运行"
    fi
}

# 运行负载测试
run_load_test() {
    info "运行简单负载测试..."

    local test_requests=100
    local concurrent_users=10
    local failed_requests=0
    local total_time=0

    for ((i=1; i<=test_requests; i++)); do
        local start_time=$(date +%s.%N)
        if ! curl -s -f "$HEALTH_URL" > /dev/null; then
            ((failed_requests++))
        fi
        local end_time=$(date +%s.%N)
        local duration=$(echo "$end_time - $start_time" | bc)
        total_time=$(echo "$total_time + $duration" | bc)
    done

    local success_rate
    success_rate=$(echo "scale=2; ($test_requests - $failed_requests) * 100 / $test_requests" | bc)
    local avg_response_time
    avg_response_time=$(echo "scale=3; $total_time / $test_requests" | bc)

    if (( $(echo "$success_rate < 95" | bc -l) )); then
        warn "负载测试成功率较低: ${success_rate}%"
    else
        log "负载测试成功率正常: ${success_rate}%"
    fi

    if (( $(echo "$avg_response_time > 0.5" | bc -l) )); then
        warn "负载测试平均响应时间较慢: ${avg_response_time}s"
    else
        log "负载测试平均响应时间正常: ${avg_response_time}s"
    fi
}

# 生成性能报告
generate_performance_report() {
    local report_file="logs/performance-report-$(date +%Y%m%d-%H%M%S).md"

    mkdir -p logs

    cat > "$report_file" << EOF
# 性能检查报告

## 检查时间
$(date)

## 系统资源状态
- CPU使用率: $(top -bn1 | grep "Cpu(s)" | sed "s/.*, *\([0-9.]*\)%* id.*/\1/" | awk '{print 100 - $1}')%
- 内存使用率: $(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100.0}')%
- 磁盘使用率: $(df -h / | awk 'NR==2 {print $5}')

## 服务状态
- 应用服务: $(docker-compose ps | grep "app.*Up" > /dev/null && echo "正常" || echo "异常")
- 数据库服务: $(docker-compose ps | grep "db.*Up" > /dev/null && echo "正常" || echo "异常")
- Redis服务: $(docker-compose ps | grep "redis.*Up" > /dev/null && echo "正常" || echo "异常")
- Nginx服务: $(docker-compose ps | grep "nginx.*Up" > /dev/null && echo "正常" || echo "异常")

## 性能指标
- 健康检查响应时间: $(curl -o /dev/null -s -w '%{time_total}' "$HEALTH_URL")s
- API基础响应时间: $(curl -o /dev/null -s -w '%{time_total}' "$API_URL/predictions/1")s

## 建议
1. 持续监控系统资源使用情况
2. 定期运行性能测试
3. 根据负载情况调整资源配置
4. 关注响应时间变化趋势

---
生成时间: $(date)
EOF

    log "性能报告已生成: $report_file"
}

# 主函数
main() {
    local test_type="${1:-basic}"

    log "开始性能检查..."

    case "$test_type" in
        "basic")
            check_system_resources
            check_docker_containers
            check_response_time "$HEALTH_URL" "健康检查端点"
            check_http_status "$HEALTH_URL" "健康检查端点"
            check_response_time "$API_URL/predictions/1" "预测API端点"
            check_http_status "$API_URL/predictions/1" "预测API端点"
            ;;
        "full")
            check_system_resources
            check_docker_containers
            check_database_connection
            check_redis_connection
            check_response_time "$HEALTH_URL" "健康检查端点"
            check_http_status "$HEALTH_URL" "健康检查端点"
            check_response_time "$API_URL/predictions/1" "预测API端点"
            check_http_status "$API_URL/predictions/1" "预测API端点"
            run_load_test
            ;;
        "load")
            run_load_test
            ;;
        *)
            echo "使用方法: $0 {basic|full|load}"
            echo "  basic - 基础性能检查"
            echo "  full  - 完整性能检查"
            echo "  load  - 负载测试"
            exit 1
            ;;
    esac

    generate_performance_report
    log "性能检查完成"
}

# 执行主函数
main "$@"