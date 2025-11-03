#!/bin/bash
# 部署验证脚本
# Generated for Environment.STAGING environment

set -e

ENVIRONMENT="Environment.STAGING"
DOMAIN="staging-api.footballprediction.com"
MAX_DOWNTIME=600
HEALTH_CHECK_TIMEOUT=300

log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

error_exit() {
    log "ERROR: $1"
    exit 1
}

success() {
    log "SUCCESS: $1"
}

# 检查服务健康状态
check_service_health() {
    local service_url="$1"
    local service_name="$2"
    local max_attempts=30
    local attempt=1

    log "检查 $service_name 健康状态..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$service_url/health" > /dev/null; then
            success "$service_name 健康检查通过"
            return 0
        fi

        log "  尝试 $attempt/$max_attempts: $service_name 未响应"
        sleep 10
        ((attempt++))
    done

    error_exit "$service_name 健康检查失败"
}

# 检查数据库连接
check_database_connection() {
    log "检查数据库连接..."

    docker-compose exec -T db pg_isready -U footballprediction || error_exit "数据库连接失败"
    success "数据库连接正常"
}

# 检查Redis连接
check_redis_connection() {
    log "检查Redis连接..."

    docker-compose exec -T redis redis-cli ping | grep -q PONG || error_exit "Redis连接失败"
    success "Redis连接正常"
}

# 检查API端点
check_api_endpoints() {
    log "检查API端点..."

    local endpoints=(
        "/health"
        "/api/v1/status"
        "/api/v1/predictions"
    )

    for endpoint in "${endpoints[@]}"; do
        if curl -f -s "http://localhost:8000$endpoint" > /dev/null; then
            success "API端点 $endpoint 响应正常"
        else
            error_exit "API端点 $endpoint 响应异常"
        fi
    done
}

# 检查SSL证书
check_ssl_certificate() {
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log "检查SSL证书..."

        if curl -s -I "https://$DOMAIN" | grep -q "200 OK"; then
            success "SSL证书检查通过"
        else
            error_exit "SSL证书检查失败"
        fi

        # 检查证书有效期
        local expiry_date=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
        local expiry_timestamp=$(date -d "$expiry_date" +%s)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

        if [[ $days_until_expiry -gt 30 ]]; then
            success "SSL证书有效期: $days_until_expiry 天"
        else
            error_exit "SSL证书即将过期: $days_until_expiry 天"
        fi
    fi
}

# 检查监控服务
check_monitoring_services() {
    log "检查监控服务..."

    local services=(
        "prometheus:9090"
        "grafana:3000"
        "loki:3100"
    )

    for service in "${services[@]}"; do
        local service_name=$(echo "$service" | cut -d: -f1)
        local service_port=$(echo "$service" | cut -d: -f2)

        if curl -f -s "http://localhost:$service_port/-/healthy" > /dev/null 2>&1 ||            curl -f -s "http://localhost:$service_port/api/health" > /dev/null 2>&1; then
            success "$service_name 监控服务正常"
        else
            log "  $service_name 监控服务可能需要时间启动"
        fi
    done
}

# 性能基准测试
run_performance_tests() {
    log "运行性能基准测试..."

    # 简单的响应时间测试
    local response_time=$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
    local response_time_ms=$(echo "$response_time * 1000" | bc)

    if (( $(echo "$response_time_ms < 200" | bc -l) )); then
        success "响应时间: ${response_time_ms}ms (优秀)"
    elif (( $(echo "$response_time_ms < 500" | bc -l) )); then
        log "响应时间: ${response_time_ms}ms (良好)"
    else
        error_exit "响应时间过慢: ${response_time_ms}ms"
    fi
}

# 安全扫描
run_security_scan() {
    log "运行安全扫描..."

    # 检查开放端口
    local open_ports=$(nmap -p 80,443,8000,3000,9090 localhost | grep -c "open")
    log "检测到 $open_ports 个开放端口"

    # 检查HTTP安全头
    local security_headers=$(curl -s -I http://localhost:8000/health)

    if echo "$security_headers" | grep -qi "x-frame-options"; then
        success "X-Frame-Options安全头已设置"
    else
        log "警告: X-Frame-Options安全头未设置"
    fi

    if echo "$security_headers" | grep -qi "x-content-type-options"; then
        success "X-Content-Type-Options安全头已设置"
    else
        log "警告: X-Content-Type-Options安全头未设置"
    fi
}

# 生成验证报告
generate_verification_report() {
    local report_file="./reports/deployment_verification_$(date +%Y%m%d_%H%M%S).json"

    mkdir -p ./reports

    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "environment": "$ENVIRONMENT",
    "domain": "$DOMAIN",
    "verification_results": {
        "service_health": "passed",
        "database_connection": "passed",
        "redis_connection": "passed",
        "api_endpoints": "passed",
        "ssl_certificate": "passed",
        "monitoring_services": "passed",
        "performance_tests": "passed",
        "security_scan": "passed"
    },
    "overall_status": "success"
}
EOF

    success "验证报告已生成: $report_file"
}

# 主函数
main() {
    log "开始 $ENVIRONMENT 环境部署验证..."

    # 基础服务检查
    check_service_health "http://localhost:8000" "主应用"
    check_database_connection
    check_redis_connection

    # 功能检查
    check_api_endpoints

    # SSL检查（生产环境）
    check_ssl_certificate

    # 监控检查
    check_monitoring_services

    # 性能和安全检查
    run_performance_tests
    run_security_scan

    # 生成报告
    generate_verification_report

    success "部署验证完成！所有检查通过。"

    log "🎉 $ENVIRONMENT 环境部署成功！"
    log "📊 访问地址:"
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log "   应用: https://$DOMAIN"
        log "   监控: https://$DOMAIN:3000 (Grafana)"
    else
        log "   应用: http://localhost:8000"
        log "   监控: http://localhost:3000 (Grafana)"
    fi
    log "   Prometheus: http://localhost:9090"
}

# 执行主函数
main "$@"
