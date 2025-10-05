#!/bin/bash
# 安全配置验证脚本
# 用于验证 FootballPrediction 项目的安全配置

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

# 检查结果统计
total_checks=0
passed_checks=0
failed_checks=0

# 检查函数
check_result() {
    total_checks=$((total_checks + 1))
    if [ $? -eq 0 ]; then
        passed_checks=$((passed_checks + 1))
        log_success "$1"
    else
        failed_checks=$((failed_checks + 1))
        log_error "$1"
    fi
}

echo "🛡️  FootballPrediction 安全配置验证"
echo "========================================"

# 1. 检查环境文件
log_info "检查环境配置文件..."

if [ -f ".env" ]; then
    log_success "找到 .env 文件"

    # 检查文件权限
    file_perms=$(stat -c "%a" .env)
    if [ "$file_perms" = "600" ]; then
        log_success ".env 文件权限正确 (600)"
    else
        log_warning ".env 文件权限不安全 ($file_perms)，建议设置为 600"
        log_info "执行: chmod 600 .env"
    fi
else
    log_error "未找到 .env 文件"
    log_info "请从 env.secure.template 创建 .env 文件"
fi

# 2. 检查默认密码
log_info "检查默认密码和弱凭据..."

if grep -q "change_me" docker-compose.yml 2>/dev/null; then
    log_error "发现默认密码 'change_me'"
    failed_checks=$((failed_checks + 1))
else
    log_success "未发现默认密码 'change_me'"
    passed_checks=$((passed_checks + 1))
fi
total_checks=$((total_checks + 1))

if grep -q "minioadmin" docker-compose.yml 2>/dev/null; then
    log_error "发现默认 MinIO 凭据 'minioadmin'"
    failed_checks=$((failed_checks + 1))
else
    log_success "未发现默认 MinIO 凭据"
    passed_checks=$((passed_checks + 1))
fi
total_checks=$((total_checks + 1))

# 3. 检查密码复杂度
log_info "检查密码复杂度..."

check_password_strength() {
    local password="$1"
    local name="$2"

    if [ ${#password} -lt 20 ]; then
        log_warning "$name 密码长度较短 (${#password} 字符)"
        return 1
    fi

    if ! echo "$password" | grep -q '[a-z]'; then
        log_error "$name 密码缺少小写字母"
        return 1
    fi

    if ! echo "$password" | grep -q '[A-Z]'; then
        log_error "$name 密码缺少大写字母"
        return 1
    fi

    if ! echo "$password" | grep -q '[0-9]'; then
        log_error "$name 密码缺少数字"
        return 1
    fi

    if ! echo "$password" | grep -q '[!@#$%^&*()_+=\-]'; then
        log_error "$name 密码缺少特殊字符"
        return 1
    fi

    log_success "$name 密码强度符合要求"
    return 0
}

# 从环境文件检查密码（如果存在）
if [ -f ".env" ]; then
    source .env 2>/dev/null || true

    if [ -n "$DB_PASSWORD" ]; then
        check_password_strength "$DB_PASSWORD" "数据库"
        check_result "数据库密码强度检查"
    fi

    if [ -n "$REDIS_PASSWORD" ]; then
        check_password_strength "$REDIS_PASSWORD" "Redis"
        check_result "Redis密码强度检查"
    fi

    if [ -n "$MINIO_ROOT_PASSWORD" ]; then
        check_password_strength "$MINIO_ROOT_PASSWORD" "MinIO"
        check_result "MinIO密码强度检查"
    fi
fi

# 4. 检查网络安全配置
log_info "检查网络安全配置..."

# 检查 Redis 端口映射
if grep -q "6379:6379" docker-compose.yml; then
    log_error "Redis 端口对外暴露，存在安全风险"
    failed_checks=$((failed_checks + 1))
else
    log_success "Redis 端口未对外暴露"
    passed_checks=$((passed_checks + 1))
fi
total_checks=$((total_checks + 1))

# 检查数据库端口（生产环境不应对外暴露）
if [ "$ENVIRONMENT" = "production" ]; then
    if grep -q "5432:5432" docker-compose.yml; then
        log_warning "生产环境数据库端口对外暴露"
    else
        log_success "生产环境数据库端口未暴露"
    fi
fi

# 5. 检查 MinIO 安全配置
log_info "检查 MinIO 安全配置..."

# 检查公开桶策略
if grep -q "policy set public" docker-compose.yml; then
    log_error "发现公开桶策略配置"
    failed_checks=$((failed_checks + 1))
else
    log_success "未发现公开桶策略"
    passed_checks=$((passed_checks + 1))
fi
total_checks=$((total_checks + 1))

# 6. 检查 Docker 配置安全
log_info "检查 Docker 配置安全..."

# 检查特权模式
if grep -q "privileged.*true" docker-compose.yml; then
    log_error "发现特权模式配置，存在安全风险"
    failed_checks=$((failed_checks + 1))
else
    log_success "未发现特权模式配置"
    passed_checks=$((passed_checks + 1))
fi
total_checks=$((total_checks + 1))

# 检查主机网络模式
if grep -q "network_mode.*host" docker-compose.yml; then
    log_error "发现主机网络模式，存在安全风险"
    failed_checks=$((failed_checks + 1))
else
    log_success "未使用主机网络模式"
    passed_checks=$((passed_checks + 1))
fi
total_checks=$((total_checks + 1))

# 7. 检查敏感文件
log_info "检查敏感文件配置..."

# 检查 .gitignore
if [ -f ".gitignore" ]; then
    if grep -q "\.env" .gitignore; then
        log_success ".env 文件已在 .gitignore 中"
        passed_checks=$((passed_checks + 1))
    else
        log_error ".env 文件未在 .gitignore 中"
        failed_checks=$((failed_checks + 1))
    fi
else
    log_warning "未找到 .gitignore 文件"
fi
total_checks=$((total_checks + 1))

# 8. 运行时检查（如果服务正在运行）
log_info "检查运行时安全状态..."

if command -v docker-compose &> /dev/null; then
    # 检查服务状态
    if docker-compose ps | grep -q "Up"; then
        log_info "发现运行中的服务，执行运行时检查..."

        # 检查 Redis 认证
        if docker-compose exec -T redis redis-cli ping 2>/dev/null | grep -q "PONG"; then
            log_error "Redis 未启用密码认证"
            failed_checks=$((failed_checks + 1))
        else
            log_success "Redis 已启用密码认证"
            passed_checks=$((passed_checks + 1))
        fi
        total_checks=$((total_checks + 1))

        # 检查数据库连接
        if [ -n "$DB_PASSWORD" ]; then
            if docker-compose exec -T db pg_isready -U football_user &>/dev/null; then
                log_success "数据库连接正常"
                passed_checks=$((passed_checks + 1))
            else
                log_warning "数据库连接检查失败"
                failed_checks=$((failed_checks + 1))
            fi
            total_checks=$((total_checks + 1))
        fi
    else
        log_info "未发现运行中的服务，跳过运行时检查"
    fi
fi

# 9. 生成安全报告
echo ""
echo "========================================"
echo "🛡️  安全检查报告"
echo "========================================"
echo "总检查项: $total_checks"
echo -e "通过: ${GREEN}$passed_checks${NC}"
echo -e "失败: ${RED}$failed_checks${NC}"

if [ $failed_checks -eq 0 ]; then
    echo -e "${GREEN}✅ 所有安全检查通过！${NC}"
    exit 0
elif [ $failed_checks -le 2 ]; then
    echo -e "${YELLOW}⚠️  发现少量安全问题，建议修复${NC}"
    exit 1
else
    echo -e "${RED}❌ 发现多个严重安全问题，必须修复！${NC}"
    exit 2
fi

# 10. 提供修复建议
echo ""
echo "🔧 修复建议:"
echo "1. 运行密码生成器: python3 scripts/generate-passwords.py --format env --output .env"
echo "2. 设置文件权限: chmod 600 .env"
echo "3. 更新 .gitignore: echo '.env' >> .gitignore"
echo "4. 重新部署服务: docker-compose down && docker-compose up -d"
echo "5. 验证配置: bash scripts/security-verify.sh"
