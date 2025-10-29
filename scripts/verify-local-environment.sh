#!/bin/bash

# =================================================================
# 足球预测系统 - 本地环境验证脚本
# =================================================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${PURPLE}[STEP]${NC} $1"
}

log_test() {
    echo -e "${CYAN}[TEST]${NC} $1"
}

# 验证结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 测试函数
run_test() {
    local test_name="$1"
    local test_command="$2"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    log_test "测试: $test_name"

    if eval "$test_command" >/dev/null 2>&1; then
        log_success "✓ 通过: $test_name"
        PASSED_TESTS=$((PASSED_TESTS + 1))
        return 0
    else
        log_error "✗ 失败: $test_name"
        FAILED_TESTS=$((FAILED_TESTS + 1))
        return 1
    fi
}

# 等待服务启动
wait_for_service() {
    local service_name="$1"
    local health_url="$2"
    local max_attempts=30
    local attempt=1

    log_info "等待 $service_name 服务启动..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f "$health_url" >/dev/null 2>&1; then
            log_success "$service_name 已就绪"
            return 0
        fi

        log_info "尝试 $attempt/$max_attempts - 等待 $service_name..."
        sleep 5
        attempt=$((attempt + 1))
    done

    log_error "$service_name 启动超时"
    return 1
}

# 1. 环境预检查
environment_precheck() {
    log_step "执行环境预检查..."

    # 检查 Docker
    run_test "Docker 服务运行" "docker info"

    # 检查 Docker Compose
    run_test "Docker Compose 可用" "docker-compose --version"

    # 检查端口占用
    run_test "端口 8080 可用" "! netstat -tuln | grep :8080"
    run_test "端口 5433 可用" "! netstat -tuln | grep :5433"
    run_test "端口 6380 可用" "! netstat -tuln | grep :6380"
    run_test "端口 9091 可用" "! netstat -tuln | grep :9091"
    run_test "端口 3002 可用" "! netstat -tuln | grep :3002"

    # 检查配置文件
    run_test "Docker Compose 配置文件存在" "test -f docker-compose.verify.yml"
    run_test "Nginx 配置文件存在" "test -f nginx/nginx.local.conf"
    run_test "SSL 证书文件存在" "test -f nginx/ssl/localhost.crt"
    run_test "SSL 私钥文件存在" "test -f nginx/ssl/localhost.key"
    run_test "Prometheus 配置存在" "test -f monitoring/prometheus.yml"
    run_test "Grafana 数据源配置存在" "test -f monitoring/grafana/datasources/prometheus.yml"

    echo
}

# 2. 启动验证环境
start_verification_environment() {
    log_step "启动验证环境..."

    # 清理旧容器
    log_info "清理旧容器..."
    docker-compose -f docker-compose.verify.yml down --remove-orphans 2>/dev/null || true

    # 启动服务
    log_info "启动验证服务栈..."
    docker-compose -f docker-compose.verify.yml up -d

    echo
}

# 3. 服务健康检查
service_health_checks() {
    log_step "执行服务健康检查..."

    # 等待服务启动
    sleep 30

    # 数据库健康检查
    run_test "PostgreSQL 数据库健康" "wait_for_service PostgreSQL http://localhost:5433"

    # Redis 健康检查
    run_test "Redis 缓存健康" "wait_for_service Redis http://localhost:6380"

    # Nginx 健康检查
    run_test "Nginx Web 服务健康" "wait_for_service Nginx http://localhost:8080"

    # Prometheus 健康检查
    run_test "Prometheus 监控健康" "wait_for_service Prometheus http://localhost:9091"

    # Grafana 健康检查
    run_test "Grafana 可视化健康" "wait_for_service Grafana http://localhost:3002"

    echo
}

# 4. 功能性测试
functional_tests() {
    log_step "执行功能性测试..."

    # HTTP 访问测试
    run_test "HTTP 服务可访问" "curl -f http://localhost:8080"

    # HTTPS 访问测试 (忽略自签名证书警告)
    run_test "HTTPS 服务可访问" "curl -k -f https://localhost:8443"

    # Prometheus API 测试
    run_test "Prometheus API 可访问" "curl -f http://localhost:9091/api/v1/targets"

    # Grafana API 测试
    run_test "Grafana API 可访问" "curl -f http://admin:verify123@localhost:3002/api/health"

    # 数据库连接测试
    run_test "数据库连接正常" "docker exec football-db-verify pg_isready -U postgres"

    # Redis 连接测试
    run_test "Redis 连接正常" "docker exec football-redis-verify redis-cli ping"

    echo
}

# 5. 配置验证测试
configuration_tests() {
    log_step "执行配置验证测试..."

    # 检查 Nginx 配置语法
    run_test "Nginx 配置语法正确" "docker exec football-web-verify nginx -t"

    # 检查 SSL 证书
    run_test "SSL 证书有效" "docker exec football-web-verify openssl x509 -in /etc/nginx/ssl/localhost.crt -noout -dates"

    # 检查 Prometheus 配置
    run_test "Prometheus 配置正确" "docker exec football-prometheus-verify promtool check config /etc/prometheus/prometheus.yml"

    # 检查服务间网络连通性
    run_test "Web 服务到数据库连通" "docker exec football-web-verify ping db"
    run_test "Web 服务到 Redis 连通" "docker exec football-web-verify ping redis"

    echo
}

# 6. 监控数据验证
monitoring_data_tests() {
    log_step "执行监控数据验证..."

    # 等待监控数据收集
    sleep 60

    # 检查 Prometheus 目标
    run_test "Prometheus 目标已发现" "curl -s http://localhost:9091/api/v1/targets | grep -q 'up'"

    # 检查 Grafana 数据源
    run_test "Grafana 数据源已配置" "curl -s -u admin:verify123 http://localhost:3002/api/datasources | grep -q 'Prometheus'"

    # 检查系统指标
    run_test "系统指标已收集" "curl -s 'http://localhost:9091/api/v1/query?query=up' | grep -q 'result'"

    echo
}

# 7. 性能基准测试
performance_tests() {
    log_step "执行性能基准测试..."

    # 响应时间测试
    run_test "HTTP 响应时间 < 1s" "curl -o /dev/null -s -w '%{time_total}' http://localhost:8080 | awk '{print \$1 < 1.0}'"

    # 内存使用检查
    run_test "容器内存使用合理" "docker stats --no-stream --format 'table {{.Container}}\t{{.MemUsage}}' football-db-verify football-redis-verify football-web-verify"

    # 磁盘使用检查
    run_test "磁盘使用正常" "df -h | grep -E '/$|/var'"

    echo
}

# 8. 安全性验证
security_tests() {
    log_step "执行安全性验证..."

    # 检查 HTTP 重定向
    run_test "HTTP 安全头配置" "curl -I http://localhost:8080 2>/dev/null | grep -i 'x-frame-options\\|x-content-type-options\\|x-xss-protection'"

    # 检查 HTTPS 配置
    run_test "HTTPS TLS 版本安全" "docker exec football-web-verify openssl s_client -connect localhost:443 -servername localhost 2>/dev/null | openssl x509 -noout -dates"

    # 检查默认密码已更改
    run_test "Grafana 默认密码已更改" "curl -s -u admin:admin http://localhost:3002/api/health | grep -q 'unauthorized'"

    echo
}

# 9. 生成验证报告
generate_verification_report() {
    log_step "生成验证报告..."

    local report_file="reports/verification-report-$(date +%Y%m%d-%H%M%S).md"
    mkdir -p reports

    cat > "$report_file" << EOF
# 足球预测系统 - 本地环境验证报告

**生成时间**: $(date)
**验证环境**: 本地开发环境
**测试统计**: $PASSED_TESTS/$TOTAL_TESTS 通过

## 📊 测试结果总览

### ✅ 通过的测试 ($PASSED_TESTS 个)

### ❌ 失败的测试 ($FAILED_TESTS 个)

## 🔍 详细测试结果

### 1. 环境预检查
### 2. 服务健康检查
### 3. 功能性测试
### 4. 配置验证测试
### 5. 监控数据验证
### 6. 性能基准测试
### 7. 安全性验证

## 🌐 服务访问地址

- **Nginx Web**: http://localhost:8080 / https://localhost:8443
- **Prometheus**: http://localhost:9091
- **Grafana**: http://localhost:3002 (admin/verify123)
- **PostgreSQL**: localhost:5433 (postgres/verify_password)
- **Redis**: localhost:6380 (无密码)

## 📋 容器状态

\`\`\`bash
docker-compose -f docker-compose.verify.yml ps
\`\`\`

## 📝 验证日志

查看详细日志:
\`\`\`bash
docker-compose -f docker-compose.verify.yml logs -f
\`\`\`

## 🚀 下一步

验证通过后，可以:
1. 启动完整的开发环境
2. 执行 API 功能测试
3. 进行负载测试
4. 准备生产部署

---
**验证脚本版本**: v1.0
**生成时间**: $(date)
EOF

    log_success "验证报告生成: $report_file"

    # 显示统计信息
    echo
    echo "=============================================="
    log_info "验证完成统计:"
    echo "  - 总测试数: $TOTAL_TESTS"
    echo "  - 通过数: $PASSED_TESTS"
    echo "  - 失败数: $FAILED_TESTS"

    if [ $FAILED_TESTS -eq 0 ]; then
        log_success "🎉 所有测试通过！本地环境验证成功！"
        echo
        echo "🌐 访问地址:"
        echo "  - Web 服务: http://localhost:8080"
        echo "  - HTTPS: https://localhost:8443"
        echo "  - Prometheus: http://localhost:9091"
        echo "  - Grafana: http://localhost:3002 (admin/verify123)"
    else
        log_warning "⚠️  发现 $FAILED_TESTS 个问题，请检查日志并修复"
        echo
        echo "📊 查看容器状态:"
        echo "  docker-compose -f docker-compose.verify.yml ps"
        echo "📋 查看日志:"
        echo "  docker-compose -f docker-compose.verify.yml logs"
    fi
    echo "=============================================="
}

# 清理环境
cleanup_environment() {
    if [ "$1" = "--cleanup" ]; then
        log_step "清理验证环境..."
        docker-compose -f docker-compose.verify.yml down --remove-orphans --volumes
        log_success "环境清理完成"
    fi
}

# 显示帮助信息
show_help() {
    echo "足球预测系统 - 本地环境验证脚本"
    echo
    echo "使用方法:"
    echo "  $0                    # 完整验证流程"
    echo "  $0 --test-only        # 仅执行测试，不启动服务"
    echo "  $0 --cleanup          # 验证后清理环境"
    echo "  $0 --help             # 显示帮助信息"
    echo
    echo "验证流程:"
    echo "  1. 环境预检查"
    echo "  2. 启动验证环境"
    echo "  3. 服务健康检查"
    echo "  4. 功能性测试"
    echo "  5. 配置验证测试"
    echo "  6. 监控数据验证"
    echo "  7. 性能基准测试"
    echo "  8. 安全性验证"
    echo "  9. 生成验证报告"
}

# 主函数
main() {
    local test_only=false
    local cleanup_after=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --test-only)
                test_only=true
                shift
                ;;
            --cleanup)
                cleanup_after=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done

    log_info "开始本地环境验证..."
    echo "=============================================="

    # 执行验证流程
    environment_precheck

    if [ "$test_only" = false ]; then
        start_verification_environment
        service_health_checks
        functional_tests
        configuration_tests
        monitoring_data_tests
        performance_tests
        security_tests
    fi

    generate_verification_report
    cleanup_environment --cleanup

    if [ "$cleanup_after" = false ]; then
        echo
        log_info "服务仍在运行，使用以下命令清理:"
        echo "  $0 --cleanup"
        echo
        log_info "或者手动清理:"
        echo "  docker-compose -f docker-compose.verify.yml down"
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi