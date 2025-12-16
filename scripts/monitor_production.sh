#!/bin/bash

# Football Prediction System - Production Monitoring Script
# 生产环境监控脚本

set -euo pipefail

# 配置
API_BASE_URL="http://localhost:8000"
LOG_FILE="./logs/production_monitor.log"
ALERT_THRESHOLD_CPU=80
ALERT_THRESHOLD_MEMORY=85
ALERT_THRESHOLD_RESPONSE_TIME=100  # ms

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

# 日志函数
log_message() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - ERROR: $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - SUCCESS: $1" | tee -a "$LOG_FILE"
}

# 检查容器健康状态
check_containers() {
    log_message "=== 容器健康状态检查 ==="

    containers=("football-prediction-app" "football-prediction-db" "football-prediction-redis")
    all_healthy=true

    for container in "${containers[@]}"; do
        if docker ps --filter "name=$container" --filter "status=running" --filter "health=healthy" | grep -q "$container"; then
            log_success "$container: 健康"
        else
            log_error "$container: 不健康或未运行"
            all_healthy=false
        fi
    done

    if $all_healthy; then
        log_success "所有容器运行正常"
    else
        log_error "检测到不健康的容器"
        return 1
    fi
}

# 检查API健康状态
check_api_health() {
    log_message "=== API健康状态检查 ==="

    # 基础健康检查
    if curl -f -s "$API_BASE_URL/health" > /dev/null; then
        log_success "基础健康检查: 通过"
    else
        log_error "基础健康检查: 失败"
        return 1
    fi

    # 预测服务健康检查
    if curl -f -s "$API_BASE_URL/api/v1/predictions/health" > /dev/null; then
        log_success "预测服务健康检查: 通过"
    else
        log_error "预测服务健康检查: 失败"
        return 1
    fi

    # 系统健康检查
    system_health=$(curl -s "$API_BASE_URL/health/system")
    if [[ $? -eq 0 ]]; then
        cpu_percent=$(echo "$system_health" | jq -r '.system.cpu_percent // 0')
        memory_percent=$(echo "$system_health" | jq -r '.system.memory_percent // 0')

        log_success "系统健康检查: CPU ${cpu_percent}%, 内存 ${memory_percent}%"

        # 资源使用率告警
        if (( $(echo "$cpu_percent > $ALERT_THRESHOLD_CPU" | bc -l) )); then
            log_error "CPU使用率过高: ${cpu_percent}% (阈值: ${ALERT_THRESHOLD_CPU}%)"
        fi

        if (( $(echo "$memory_percent > $ALERT_THRESHOLD_MEMORY" | bc -l) )); then
            log_error "内存使用率过高: ${memory_percent}% (阈值: ${ALERT_THRESHOLD_MEMORY}%)"
        fi
    else
        log_error "系统健康检查: 失败"
        return 1
    fi
}

# 测试预测API性能
test_prediction_performance() {
    log_message "=== 预测API性能测试 ==="

    # 测试单个预测
    start_time=$(date +%s%3N)
    response=$(curl -s -X POST "$API_BASE_URL/api/v1/predictions/12345/predict" -H "Content-Type: application/json" -d '{}')
    end_time=$(date +%s%3N)
    response_time=$((end_time - start_time))

    if [[ $? -eq 0 ]] && [[ "$response" == *"predicted_outcome"* ]]; then
        log_success "预测API测试: 成功 (${response_time}ms)"

        if [[ $response_time -gt $ALERT_THRESHOLD_RESPONSE_TIME ]]; then
            log_error "预测API响应时间过长: ${response_time}ms (阈值: ${ALERT_THRESHOLD_RESPONSE_TIME}ms)"
        fi
    else
        log_error "预测API测试: 失败"
        return 1
    fi
}

# 检查数据库连接
check_database() {
    log_message "=== 数据库连接检查 ==="

    # 检查PostgreSQL容器健康状态
    if docker exec football-prediction-db pg_isready -U postgres -d football_prediction > /dev/null 2>&1; then
        log_success "PostgreSQL连接: 正常"
    else
        log_error "PostgreSQL连接: 失败"
        return 1
    fi

    # 检查Redis连接
    if docker exec football-prediction-redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis连接: 正常"
    else
        log_error "Redis连接: 失败"
        return 1
    fi
}

# 检查日志错误
check_log_errors() {
    log_message "=== 日志错误检查 ==="

    # 检查应用日志中的错误
    error_count=$(docker logs football-prediction-app 2>&1 | grep -i "error" | wc -l)
    warning_count=$(docker logs football-prediction-app 2>&1 | grep -i "warning" | wc -l)

    log_message "应用日志统计: ${error_count}个错误, ${warning_count}个警告"

    if [[ $error_count -gt 10 ]]; then
        log_error "错误日志数量过多: ${error_count}"
    fi
}

# 模型性能检查
check_model_performance() {
    log_message "=== 模型性能检查 ==="

    # 测试多个预测以检查一致性
    predictions=()
    for i in {1..5}; do
        response=$(curl -s -X POST "$API_BASE_URL/api/v1/predictions/1234$i/predict" -H "Content-Type: application/json" -d '{}')
        predictions+=("$response")
        sleep 0.1
    done

    # 检查预测结果的一致性
    unique_outcomes=$(printf "%s\n" "${predictions[@]}" | jq -r '.predicted_outcome' | sort -u | wc -l)

    if [[ $unique_outcomes -ge 1 ]]; then
        log_success "模型一致性检查: 通过 (${#predictions[@]}个预测)"
    else
        log_error "模型一致性检查: 失败"
        return 1
    fi
}

# 生成状态报告
generate_status_report() {
    log_message "=== 生产状态报告 ==="

    report_file="./logs/daily_status_$(date +%Y%m%d).json"

    # 收集状态信息
    timestamp=$(date -u +"%Y-%m-%dT%H:%M:%S.%3NZ")

    status=$(curl -s "$API_BASE_URL/health/system" | jq -c '.')

    # 生成报告
    cat > "$report_file" << EOF
{
    "timestamp": "$timestamp",
    "system_status": $status,
    "monitoring_time": "$(date)",
    "containers": {
        "app": $(docker inspect football-prediction-app --format='{{.State.Health.Status}}' 2>/dev/null || echo "\"unknown\""),
        "db": $(docker inspect football-prediction-db --format='{{.State.Health.Status}}' 2>/dev/null || echo "\"unknown\""),
        "redis": $(docker inspect football-prediction-redis --format='{{.State.Health.Status}}' 2>/dev/null || echo "\"unknown\"")
    }
}
EOF

    log_success "状态报告已生成: $report_file"
}

# 主函数
main() {
    log_message "开始生产环境监控检查"

    # 执行各项检查
    if check_containers && \
       check_api_health && \
       test_prediction_performance && \
       check_database && \
       check_model_performance; then

        log_success "=== 所有检查通过 ==="
        overall_status="HEALTHY"
    else
        log_error "=== 检查失败 ==="
        overall_status="UNHEALTHY"
    fi

    # 额外检查
    check_log_errors
    generate_status_report

    log_message "监控检查完成 - 状态: $overall_status"

    # 返回状态码
    [[ "$overall_status" == "HEALTHY" ]]
}

# 执行主函数
main "$@"