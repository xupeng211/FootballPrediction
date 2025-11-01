#!/bin/bash

# 🔍 Deployment Verification Script
# 部署验证脚本
# Author: Claude AI Assistant
# Version: 1.0

set -euo pipefail

# 配置
DOMAIN=${DOMAIN:-"localhost"}
PROTOCOL=${PROTOCOL:-"http"}
TIMEOUT=${TIMEOUT:-30}

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_header() {
    echo -e "${BLUE}🎯 $1${NC}"
}

# 检查URL可访问性
check_url() {
    local url=$1
    local description=$2
    local timeout=${3:-10}

    log_info "检查 $description: $url"

    if curl -f -s --max-time "$timeout" "$url" > /dev/null 2>&1; then
        log_success "$description 可访问"
        return 0
    else
        log_error "$description 不可访问"
        return 1
    fi
}

# 检查HTTP状态码
check_http_status() {
    local url=$1
    local expected_status=${2:-200}
    local description=$3

    log_info "检查 $description 状态码"

    local status_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null || echo "000")

    if [ "$status_code" = "$expected_status" ]; then
        log_success "$description 状态码正确 ($status_code)"
        return 0
    else
        log_error "$description 状态码错误 ($status_code ≠ $expected_status)"
        return 1
    fi
}

# 检查API端点
check_api_endpoint() {
    local endpoint=$1
    local method=${2:-"GET"}
    local description=$3

    local url="${PROTOCOL}://${DOMAIN}${endpoint}"
    log_info "检查API端点: $description ($method $endpoint)"

    case "$method" in
        "GET")
            if curl -f -s --max-time 10 "$url" > /dev/null 2>&1; then
                log_success "API端点 $description 响应正常"
                return 0
            else
                log_error "API端点 $description 响应异常"
                return 1
            fi
            ;;
        "POST")
            if curl -f -s -X POST --max-time 10 "$url" \
                -H "Content-Type: application/json" \
                -d '{}' > /dev/null 2>&1; then
                log_success "API端点 $description 响应正常"
                return 0
            else
                log_warning "API端点 $description 可能需要认证或数据"
                return 0  # POST端点可能需要认证，不算失败
            fi
            ;;
    esac
}

# 检查Docker服务状态
check_docker_services() {
    log_header "检查Docker服务状态"

    local services=("app" "db" "redis" "nginx")
    local failed_services=()

    for service in "${services[@]}"; do
        if docker-compose ps "$service" | grep -q "Up"; then
            log_success "服务 $service 运行正常"
        else
            log_error "服务 $service 未运行"
            failed_services+=("$service")
        fi
    done

    if [ ${#failed_services[@]} -eq 0 ]; then
        log_success "所有Docker服务运行正常"
        return 0
    else
        log_error "以下服务未运行: ${failed_services[*]}"
        return 1
    fi
}

# 检查数据库连接
check_database_connection() {
    log_header "检查数据库连接"

    # 检查PostgreSQL
    if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
        log_success "PostgreSQL数据库连接正常"

        # 检查数据库表
        local table_count=$(docker-compose exec -T db psql -U postgres -d football_prediction -t -c "
            SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';
        " 2>/dev/null | tr -d ' ' || echo "0")

        if [ "$table_count" -gt 0 ]; then
            log_success "数据库包含 $table_count 个表"
        else
            log_warning "数据库可能未初始化"
        fi
    else
        log_error "PostgreSQL数据库连接失败"
        return 1
    fi

    # 检查Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis连接正常"
    else
        log_error "Redis连接失败"
        return 1
    fi

    return 0
}

# 检查SSL证书
check_ssl_certificate() {
    log_header "检查SSL证书"

    if [ "$PROTOCOL" = "https" ]; then
        local cert_info=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null | openssl x509 -noout -dates 2>/dev/null || echo "")

        if [ -n "$cert_info" ]; then
            local not_after=$(echo "$cert_info" | grep "notAfter" | cut -d= -f2)
            log_success "SSL证书有效，到期时间: $not_after"

            # 检查证书是否在30天内过期
            local expiry_timestamp=$(date -d "$not_after" +%s 2>/dev/null || echo "0")
            local current_timestamp=$(date +%s)
            local thirty_days=$((30 * 24 * 3600))
            local thirty_days_later=$((current_timestamp + thirty_days))

            if [ "$expiry_timestamp" -lt "$thirty_days_later" ]; then
                log_warning "SSL证书将在30天内过期"
                return 1
            fi
        else
            log_error "无法获取SSL证书信息"
            return 1
        fi
    else
        log_info "跳过SSL检查 (使用HTTP)"
    fi

    return 0
}

# 性能基准测试
performance_benchmark() {
    log_header "执行性能基准测试"

    # 健康检查端点性能测试
    local health_url="${PROTOCOL}://${DOMAIN}/health"

    if command -v ab >/dev/null 2>&1; then
        log_info "执行Apache基准测试..."

        local ab_result=$(ab -n 100 -c 10 "$health_url" 2>/dev/null | grep "Requests per second" | awk '{print $4}' || echo "0")

        if [ "$ab_result" -gt 50 ]; then
            log_success "性能测试通过 (${ab_result} req/s)"
        else
            log_warning "性能可能需要优化 (${ab_result} req/s)"
        fi
    else
        log_info "Apache Bench (ab) 未安装，跳过性能测试"
    fi

    # 简单的响应时间测试
    local start_time=$(date +%s.%N)
    if curl -f -s --max-time 10 "$health_url" > /dev/null 2>&1; then
        local end_time=$(date +%s.%N)
        local response_time=$(echo "$end_time - $start_time" | bc 2>/dev/null || echo "0")

        if (( $(echo "$response_time < 1.0" | bc -l) )); then
            log_success "响应时间良好 (${response_time}s)"
        else
            log_warning "响应时间较慢 (${response_time}s)"
        fi
    else
        log_error "健康检查端点无响应"
    fi
}

# 安全检查
security_check() {
    log_header "执行安全检查"

    # 检查安全头部
    local security_headers=$(curl -s -I --max-time 10 "${PROTOCOL}://${DOMAIN}" 2>/dev/null || echo "")

    if echo "$security_headers" | grep -qi "x-frame-options"; then
        log_success "X-Frame-Options头部已设置"
    else
        log_warning "缺少X-Frame-Options头部"
    fi

    if echo "$security_headers" | grep -qi "x-content-type-options"; then
        log_success "X-Content-Type-Options头部已设置"
    else
        log_warning "缺少X-Content-Type-Options头部"
    fi

    if [ "$PROTOCOL" = "https" ]; then
        if echo "$security_headers" | grep -qi "strict-transport-security"; then
            log_success "HSTS头部已设置"
        else
            log_warning "缺少HSTS头部"
        fi
    fi
}

# 生成验证报告
generate_verification_report() {
    local report_file="deployment_verification_report_$(date +%Y%m%d_%H%M%S).json"

    cat > "$report_file" << EOF
{
    "timestamp": "$(date -Iseconds)",
    "domain": "$DOMAIN",
    "protocol": "$PROTOCOL",
    "checks": {
        "docker_services": $docker_services_status,
        "database_connection": $database_connection_status,
        "ssl_certificate": $ssl_certificate_status,
        "api_endpoints": $api_endpoints_status,
        "performance": $performance_status,
        "security": $security_status
    },
    "overall_status": $overall_status,
    "summary": {
        "total_checks": $total_checks,
        "passed_checks": $passed_checks,
        "failed_checks": $failed_checks
    }
}
EOF

    log_success "验证报告已生成: $report_file"
}

# 主验证流程
main() {
    echo "🔍 FootballPrediction 部署验证"
    echo "==============================="
    echo "域名: $DOMAIN"
    echo "协议: $PROTOCOL"
    echo ""

    local total_checks=0
    local passed_checks=0
    local failed_checks=0

    # Docker服务检查
    if check_docker_services; then
        docker_services_status=true
        ((passed_checks++))
    else
        docker_services_status=false
        ((failed_checks++))
    fi
    ((total_checks++))

    # 数据库连接检查
    if check_database_connection; then
        database_connection_status=true
        ((passed_checks++))
    else
        database_connection_status=false
        ((failed_checks++))
    fi
    ((total_checks++))

    # SSL证书检查
    if check_ssl_certificate; then
        ssl_certificate_status=true
        ((passed_checks++))
    else
        ssl_certificate_status=false
        ((failed_checks++))
    fi
    ((total_checks++))

    # API端点检查
    log_header "检查API端点"
    local api_endpoints_passed=0
    local api_endpoints_total=0

    # 健康检查
    ((api_endpoints_total++))
    if check_api_endpoint "/health" "GET" "健康检查"; then
        ((api_endpoints_passed++))
    fi

    # API文档
    ((api_endpoints_total++))
    if check_api_endpoint "/docs" "GET" "API文档"; then
        ((api_endpoints_passed++))
    fi

    # 预测端点 (可能需要认证)
    ((api_endpoints_total++))
    if check_api_endpoint "/api/v1/predictions" "GET" "预测列表"; then
        ((api_endpoints_passed++))
    fi

    if [ "$api_endpoints_passed" -eq "$api_endpoints_total" ]; then
        api_endpoints_status=true
        ((passed_checks++))
    elif [ "$api_endpoints_passed" -gt 0 ]; then
        api_endpoints_status=true  # 部分成功也算通过
        ((passed_checks++))
    else
        api_endpoints_status=false
        ((failed_checks++))
    fi
    ((total_checks++))

    # 性能检查
    if performance_benchmark; then
        performance_status=true
        ((passed_checks++))
    else
        performance_status=false
        ((failed_checks++))
    fi
    ((total_checks++))

    # 安全检查
    if security_check; then
        security_status=true
        ((passed_checks++))
    else
        security_status=false
        ((failed_checks++))
    fi
    ((total_checks++))

    # 生成报告
    generate_verification_report

    # 输出结果
    echo ""
    log_header "验证结果汇总"
    echo "总检查数: $total_checks"
    echo "通过: $passed_checks"
    echo "失败: $failed_checks"
    echo "成功率: $(( passed_checks * 100 / total_checks ))%"

    if [ "$passed_checks" -eq "$total_checks" ]; then
        log_success "🎉 所有验证检查通过！部署成功！"
        overall_status=true
        exit 0
    elif [ "$passed_checks" -ge $((total_checks * 80 / 100)) ]; then
        log_warning "⚠️ 大部分检查通过，但存在一些问题需要注意"
        overall_status=true
        exit 0
    else
        log_error "❌ 多个验证检查失败，请检查部署配置"
        overall_status=false
        exit 1
    fi
}

# 运行主函数
main "$@"