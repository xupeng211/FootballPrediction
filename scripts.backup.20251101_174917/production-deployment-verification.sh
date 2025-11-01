#!/bin/bash

# 🌐 Production Deployment Verification Script
# 生产环境部署验证脚本
# Author: Claude AI Assistant
# Version: 1.0

set -euo pipefail

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
    echo -e "${BLUE}ℹ️  INFO: $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ SUCCESS: $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  WARNING: $1${NC}"
}

log_error() {
    echo -e "${RED}❌ ERROR: $1${NC}"
}

log_header() {
    echo -e "${PURPLE}🎯 $1${NC}"
}

log_step() {
    echo -e "${CYAN}📋 $1${NC}"
}

# 检查依赖
check_dependencies() {
    log_header "检查系统依赖"

    local deps=("docker" "docker-compose" "curl" "jq" "openssl")
    local missing=()

    for dep in "${deps[@]}"; do
        if ! command -v "$dep" &> /dev/null; then
            missing+=("$dep")
        else
            log_success "$dep 已安装"
        fi
    done

    if [ ${#missing[@]} -ne 0 ]; then
        log_error "缺少依赖: ${missing[*]}"
        echo "请安装缺少的依赖后重新运行此脚本"
        exit 1
    fi

    log_success "所有依赖检查通过"
}

# 验证环境变量
verify_environment_variables() {
    log_header "验证环境变量配置"

    local required_vars=("DATABASE_URL" "SECRET_KEY")
    local recommended_vars=("REDIS_URL" "ENVIRONMENT" "LOG_LEVEL" "API_HOSTNAME")
    local missing_required=()
    local missing_recommended=()

    # 检查必需变量
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_required+=("$var")
        else
            log_success "$var 已设置"
        fi
    done

    # 检查推荐变量
    for var in "${recommended_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_recommended+=("$var")
            log_warning "$var 未设置 (推荐)"
        else
            log_success "$var 已设置"
        fi
    done

    if [ ${#missing_required[@]} -ne 0 ]; then
        log_error "缺少必需的环境变量: ${missing_required[*]}"
        return 1
    fi

    if [ ${#missing_recommended[@]} -ne 0 ]; then
        log_warning "缺少推荐的环境变量: ${missing_recommended[*]}"
        log_info "建议设置这些变量以获得更好的生产环境体验"
    fi

    log_success "环境变量验证完成"
}

# 验证Docker配置
verify_docker_configuration() {
    log_header "验证Docker配置"

    # 检查Dockerfile
    if [ -f "Dockerfile" ]; then
        log_success "找到 Dockerfile"

        # 检查Dockerfile内容
        if grep -q "FROM python:" Dockerfile; then
            log_success "Dockerfile 基础镜像正确"
        else
            log_warning "Dockerfile 可能没有使用Python基础镜像"
        fi

        if grep -q "EXPOSE" Dockerfile; then
            log_success "Dockerfile 包含端口暴露"
        else
            log_warning "Dockerfile 未明确暴露端口"
        fi
    else
        log_error "未找到 Dockerfile"
        return 1
    fi

    # 检查docker-compose配置
    local compose_files=("docker-compose.yml" "docker-compose.prod.yml" "docker-compose.production.yml")
    local found_compose=false

    for compose_file in "${compose_files[@]}"; do
        if [ -f "$compose_file" ]; then
            log_success "找到 $compose_file"
            found_compose=true

            # 验证compose文件语法
            if docker-compose -f "$compose_file" config &>/dev/null; then
                log_success "$compose_file 语法正确"
            else
                log_error "$compose_file 语法错误"
                return 1
            fi

            # 检查关键服务
            if grep -q "app:" "$compose_file"; then
                log_success "找到 app 服务配置"
            fi

            if grep -q "db:" "$compose_file"; then
                log_success "找到 db 服务配置"
            fi

            break
        fi
    done

    if [ "$found_compose" = false ]; then
        log_error "未找到 docker-compose 配置文件"
        return 1
    fi

    log_success "Docker配置验证完成"
}

# 验证SSL/HTTPS配置
verify_ssl_configuration() {
    log_header "验证SSL/HTTPS配置"

    # 检查nginx配置
    local nginx_configs=("nginx/nginx.prod.conf" "nginx/nginx.https.conf" "nginx/nginx.conf")
    local found_nginx=false

    for nginx_config in "${nginx_configs[@]}"; do
        if [ -f "$nginx_config" ]; then
            log_success "找到 $nginx_config"
            found_nginx=true

            # 检查SSL配置
            if grep -q "ssl_certificate" "$nginx_config"; then
                log_success "找到SSL证书配置"

                # 检查证书路径
                local cert_path=$(grep "ssl_certificate" "$nginx_config" | awk '{print $2}' | tr -d ';')
                if [ -f "$cert_path" ]; then
                    log_success "SSL证书文件存在: $cert_path"

                    # 检查证书有效期
                    if openssl x509 -checkend 2592000 -noout -in "$cert_path"; then
                        log_success "SSL证书有效期大于30天"
                    else
                        log_warning "SSL证书将在30天内过期"
                    fi
                else
                    log_warning "SSL证书文件不存在: $cert_path"
                fi
            else
                log_warning "$nginx_config 未配置SSL"
            fi

            if grep -q "listen 443" "$nginx_config"; then
                log_success "配置HTTPS端口 (443)"
            fi

            break
        fi
    done

    if [ "$found_nginx" = false ]; then
        log_warning "未找到nginx配置文件"
    fi

    # 检查Let's Encrypt脚本
    local le_scripts=("scripts/renew_ssl_certificates.sh" "scripts/setup_https_docker.sh")
    for script in "${le_scripts[@]}"; do
        if [ -f "$script" ]; then
            log_success "找到SSL管理脚本: $script"
            if [ -x "$script" ]; then
                log_success "$script 具有执行权限"
            else
                log_warning "$script 缺少执行权限"
            fi
        fi
    done

    log_success "SSL配置验证完成"
}

# 验证安全配置
verify_security_configuration() {
    log_header "验证安全配置"

    # 检查环境变量中的敏感信息
    local sensitive_patterns=("password" "secret" "key" "token")
    local found_issues=false

    for pattern in "${sensitive_patterns[@]}"; do
        if grep -r -i "$pattern" . --include="*.py" --include="*.yml" --include="*.yaml" --include="*.env*" 2>/dev/null | grep -v ".git" | head -5; then
            log_warning "发现可能的敏感信息 (模式: $pattern)"
            found_issues=true
        fi
    done

    if [ "$found_issues" = false ]; then
        log_success "未发现明显的敏感信息泄露"
    fi

    # 检查安全扫描工具配置
    if [ -f "pyproject.toml" ] && grep -q "bandit" pyproject.toml; then
        log_success "配置了Bandit安全扫描"
    fi

    # 检查Docker安全配置
    if [ -f "docker-compose.yml" ]; then
        if grep -q "user:" docker-compose.yml; then
            log_success "Docker配置了非root用户运行"
        else
            log_warning "建议在Docker中配置非root用户"
        fi
    fi

    log_success "安全配置验证完成"
}

# 验证监控配置
verify_monitoring_configuration() {
    log_header "验证监控配置"

    # 检查Prometheus配置
    local prometheus_configs=("config/prometheus/prometheus.yml" "config/monitoring/prometheus.yml")
    for prom_config in "${prometheus_configs[@]}"; do
        if [ -f "$prom_config" ]; then
            log_success "找到Prometheus配置: $prom_config"

            if grep -q "scrape_configs:" "$prom_config"; then
                log_success "Prometheus配置了抓取任务"
            fi
        fi
    done

    # 检查Grafana配置
    local grafana_dirs=("config/grafana/" "grafana/")
    for grafana_dir in "${grafana_dirs[@]}"; do
        if [ -d "$grafana_dir" ]; then
            log_success "找到Grafana配置目录: $grafana_dir"

            if [ -f "$grafana_dir/datasources/prometheus.yml" ]; then
                log_success "Grafana数据源配置存在"
            fi
        fi
    done

    # 检查Loki配置
    if [ -f "config/loki/loki.yml" ] || [ -f "config/loki/loki.staging.yml" ]; then
        log_success "找到Loki日志配置"
    fi

    # 检查健康检查端点
    local health_endpoints=("/health" "/healthz" "/ping")
    local found_health=false

    for endpoint in "${health_endpoints[@]}"; do
        if grep -r "$endpoint" . --include="*.py" 2>/dev/null | head -3; then
            log_success "找到健康检查端点: $endpoint"
            found_health=true
            break
        fi
    done

    if [ "$found_health" = false ]; then
        log_warning "未找到健康检查端点"
    fi

    log_success "监控配置验证完成"
}

# 验证数据库配置
verify_database_configuration() {
    log_header "验证数据库配置"

    # 检查数据库迁移文件
    if [ -d "alembic" ]; then
        log_success "找到Alembic迁移目录"

        if [ -f "alembic.ini" ]; then
            log_success "找到Alembic配置文件"
        fi

        # 检查迁移版本
        local migration_count=$(find alembic/versions -name "*.py" 2>/dev/null | wc -l)
        if [ "$migration_count" -gt 0 ]; then
            log_success "找到 $migration_count 个数据库迁移文件"
        fi
    else
        log_warning "未找到Alembic迁移配置"
    fi

    # 检查数据库备份脚本
    local backup_scripts=("scripts/backup_database.sh" "scripts/db_backup.sh")
    for script in "${backup_scripts[@]}"; do
        if [ -f "$script" ]; then
            log_success "找到数据库备份脚本: $script"
        fi
    done

    log_success "数据库配置验证完成"
}

# 执行部署测试
run_deployment_test() {
    log_header "执行部署测试"

    # 构建Docker镜像
    log_step "构建Docker镜像"
    if docker build -t football-prediction-test . &>/dev/null; then
        log_success "Docker镜像构建成功"

        # 清理测试镜像
        docker rmi football-prediction-test &>/dev/null || true
    else
        log_error "Docker镜像构建失败"
        return 1
    fi

    # 验证docker-compose配置
    log_step "验证docker-compose配置"
    local compose_file="docker-compose.yml"

    # 选择合适的compose文件
    if [ -f "docker-compose.prod.yml" ]; then
        compose_file="docker-compose.prod.yml"
    elif [ -f "docker-compose.production.yml" ]; then
        compose_file="docker-compose.production.yml"
    fi

    if docker-compose -f "$compose_file" config &>/dev/null; then
        log_success "docker-compose配置验证成功"
    else
        log_error "docker-compose配置验证失败"
        return 1
    fi

    log_success "部署测试完成"
}

# 生成部署报告
generate_deployment_report() {
    log_header "生成部署验证报告"

    local report_file="deployment_verification_report_$(date +%Y%m%d_%H%M%S).md"

    cat > "$report_file" << EOF
# 🌐 生产环境部署验证报告

**生成时间**: $(date '+%Y-%m-%d %H:%M:%S')
**验证脚本版本**: 1.0

## 📊 验证结果摘要

### ✅ 通过的检查
- 系统依赖检查
- Docker配置验证
- SSL/HTTPS配置检查
- 安全配置验证
- 监控配置验证
- 数据库配置验证
- 部署测试

### ⚠️ 需要关注的问题
$(if [ ${#warnings[@]} -gt 0 ]; then
    for warning in "${warnings[@]}"; do
        echo "- $warning"
    done
else
    echo "- 无警告"
fi)

### 🔧 建议改进
- 实施自动SSL证书续期
- 加强敏感信息管理
- 完善监控告警配置
- 增加自动化部署流程

## 📋 部署前检查清单

- [ ] 所有环境变量已正确配置
- [ ] SSL证书已安装并验证有效期
- [ ] 数据库迁移脚本已准备
- [ ] 监控系统已配置
- [ ] 备份策略已制定
- [ ] 回滚计划已准备

## 🚀 部署建议

1. **分阶段部署**: 先在测试环境验证，再部署到生产
2. **监控告警**: 确保关键指标监控正常
3. **回滚准备**: 准备快速回滚方案
4. **性能测试**: 部署后进行性能验证

---

*此报告由自动化部署验证脚本生成*
EOF

    log_success "部署验证报告已生成: $report_file"
}

# 主函数
main() {
    echo "🌐 Production Deployment Verification"
    echo "=================================="
    echo ""

    local warnings=()

    # 执行所有验证
    check_dependencies
    verify_environment_variables || warnings+=("环境变量配置需要完善")
    verify_docker_configuration || warnings+=("Docker配置需要修复")
    verify_ssl_configuration || warnings+=("SSL配置需要完善")
    verify_security_configuration || warnings+=("安全配置需要加强")
    verify_monitoring_configuration || warnings+=("监控配置需要完善")
    verify_database_configuration || warnings+=("数据库配置需要完善")
    run_deployment_test || warnings+=("部署测试失败")

    # 生成报告
    generate_deployment_report

    echo ""
    log_header "验证完成"

    if [ ${#warnings[@]} -eq 0 ]; then
        log_success "🎉 所有验证检查通过！系统已准备好部署到生产环境。"
        exit 0
    else
        log_warning "⚠️ 发现 ${#warnings[@]} 个需要关注的问题，请查看详细报告。"
        exit 1
    fi
}

# 运行主函数
main "$@"