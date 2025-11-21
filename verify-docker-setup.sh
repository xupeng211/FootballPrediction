#!/bin/bash

# ===========================================
# Docker 配置验证脚本
# ===========================================

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# 检查文件是否存在
check_file() {
    local file=$1
    local description=$2

    if [ -f "$file" ]; then
        log_success "✓ $description 存在: $file"
        return 0
    else
        log_error "✗ $description 不存在: $file"
        return 1
    fi
}

# 检查文件内容
check_file_content() {
    local file=$1
    local pattern=$2
    local description=$3

    if grep -q "$pattern" "$file" 2>/dev/null; then
        log_success "✓ $description 配置正确"
        return 0
    else
        log_error "✗ $description 配置错误"
        return 1
    fi
}

# 检查权限
check_permissions() {
    local file=$1
    local expected_perm=$2
    local description=$3

    if [ "$(stat -c %a "$file" 2>/dev/null)" = "$expected_perm" ]; then
        log_success "✓ $description 权限正确: $expected_perm"
        return 0
    else
        log_warning "⚠ $description 权限异常 (期望: $expected_perm, 实际: $(stat -c %a "$file" 2>/dev/null || echo "N/A"))"
        return 1
    fi
}

# 主验证函数
main() {
    echo "=========================================="
    echo "🔍 Docker 配置验证"
    echo "=========================================="
    echo ""

    local error_count=0

    # 检查核心文件
    log_info "检查核心 Docker 文件..."

    if ! check_file "Dockerfile.simple" "后端 Dockerfile"; then
        ((error_count++))
    fi

    if ! check_file "frontend/Dockerfile" "前端 Dockerfile"; then
        ((error_count++))
    fi

    if ! check_file "frontend/nginx.conf" "Nginx 配置文件"; then
        ((error_count++))
    fi

    if ! check_file "docker-compose.simple.yml" "Docker Compose 文件"; then
        ((error_count++))
    fi

    if ! check_file ".env.docker" "环境变量文件"; then
        ((error_count++))
    fi

    # 检查脚本文件
    log_info "检查脚本文件..."

    if ! check_file "start-docker.sh" "启动脚本"; then
        ((error_count++))
    fi

    if ! check_file "stop-docker.sh" "停止脚本"; then
        ((error_count++))
    fi

    if ! check_file "DOCKER_README.md" "文档文件"; then
        ((error_count++))
    fi

    # 检查文件权限
    log_info "检查文件权限..."

    if ! check_permissions "start-docker.sh" "755" "启动脚本"; then
        ((error_count++))
    fi

    if ! check_permissions "stop-docker.sh" "755" "停止脚本"; then
        ((error_count++))
    fi

    # 检查关键配置内容
    log_info "检查关键配置内容..."

    if ! check_file_content "Dockerfile.simple" "FROM python:3.11-slim" "后端基础镜像"; then
        ((error_count++))
    fi

    if ! check_file_content "frontend/Dockerfile" "FROM node:18-alpine AS builder" "前端构建阶段"; then
        ((error_count++))
    fi

    if ! check_file_content "frontend/Dockerfile" "FROM nginx:alpine" "前端服务阶段"; then
        ((error_count++))
    fi

    if ! check_file_content "docker-compose.simple.yml" "services:" "服务配置"; then
        ((error_count++))
    fi

    if ! check_file_content "docker-compose.simple.yml" "football_prediction_db" "数据库服务"; then
        ((error_count++))
    fi

    # 检查端口配置
    log_info "检查端口配置..."

    local ports=("3000:80" "8000:8000" "5432:5432" "6379:6379")
    for port in "${ports[@]}"; do
        if grep -q "$port" "docker-compose.simple.yml"; then
            log_success "✓ 端口映射配置正确: $port"
        else
            log_error "✗ 端口映射缺失: $port"
            ((error_count++))
        fi
    done

    # 生成验证报告
    echo ""
    echo "=========================================="
    echo "📊 验证结果报告"
    echo "=========================================="

    if [ $error_count -eq 0 ]; then
        log_success "🎉 所有检查通过！Docker 配置完整且正确。"
        echo ""
        echo "下一步："
        echo "1. 确保您的系统已安装 Docker 和 Docker Compose"
        echo "2. 运行 ./start-docker.sh 启动系统"
        echo "3. 访问 http://localhost:3000 查看前端应用"
        echo "4. 访问 http://localhost:8000/docs 查看 API 文档"
    else
        log_error "❌ 发现 $error_count 个配置问题，请修复后重试。"
        echo ""
        echo "建议："
        echo "1. 检查上述错误信息"
        echo "2. 确保所有文件都已正确创建"
        echo "3. 检查文件内容和权限设置"
    fi

    echo ""
    echo "=========================================="

    return $error_count
}

# 执行验证
main "$@"