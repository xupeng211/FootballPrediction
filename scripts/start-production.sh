#!/bin/bash
# ==================================================
# 足球预测系统生产环境启动脚本
#
# 功能：快速启动生产环境服务
# 使用方法：./scripts/start-production.sh
# ==================================================

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

# 获取项目根目录
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# 检查必要文件
check_prerequisites() {
    log_info "检查必要条件..."

    # 检查环境配置文件
    if [[ ! -f ".env.production" ]]; then
        log_error "生产环境配置文件不存在: .env.production"
        log_info "请先复制 .env.production.example 为 .env.production 并配置正确的值"
        exit 1
    fi

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    # 检查环境变量中的占位符
    PLACEHOLDERS=$(grep -n "HERE" .env.production | wc -l)
    if [[ $PLACEHOLDERS -gt 0 ]]; then
        log_error "环境配置文件中仍有 $PLACEHOLDERS 个占位符需要设置"
        grep -n "HERE" .env.production
        exit 1
    fi

    log_success "必要条件检查通过"
}

# 创建必要目录
create_directories() {
    log_info "创建必要目录..."

    mkdir -p logs/nginx
    mkdir -p logs/app
    mkdir -p backups
    mkdir -p data
    mkdir -p nginx/ssl

    log_success "目录创建完成"
}

# 创建SSL证书（自签名，仅用于测试）
create_ssl_certificates() {
    log_info "检查SSL证书..."

    if [[ ! -f "nginx/ssl/cert.pem" ]] || [[ ! -f "nginx/ssl/key.pem" ]]; then
        log_warning "SSL证书不存在，创建自签名证书（仅用于测试）"

        openssl req -x509 -newkey rsa:4096 -nodes -days 365 \
            -keyout nginx/ssl/key.pem \
            -out nginx/ssl/cert.pem \
            -subj "/C=CN/ST=Beijing/L=Beijing/O=Football Prediction/CN=localhost"

        log_success "自签名SSL证书已创建"
        log_warning "生产环境请使用正式的SSL证书"
    else
        log_success "SSL证书已存在"
    fi
}

# 启动服务
start_services() {
    log_info "启动生产环境服务..."

    # 使用生产环境配置启动
    docker-compose -f docker-compose.prod.yml up -d

    log_success "服务启动中..."
}

# 等待服务启动
wait_for_services() {
    log_info "等待服务启动完成..."

    # 等待数据库启动
    log_info "等待数据库启动..."
    timeout=60
    while [[ $timeout -gt 0 ]]; do
        if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U football_user &>/dev/null; then
            log_success "数据库已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done

    if [[ $timeout -le 0 ]]; then
        log_error "数据库启动超时"
        exit 1
    fi

    # 等待应用启动
    log_info "等待应用启动..."
    timeout=60
    while [[ $timeout -gt 0 ]]; do
        if curl -f http://localhost:8000/health &>/dev/null; then
            log_success "应用已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout - 2))
    done

    if [[ $timeout -le 0 ]]; then
        log_error "应用启动超时"
        exit 1
    fi
}

# 显示服务状态
show_status() {
    log_info "服务状态："
    docker-compose -f docker-compose.prod.yml ps

    echo -e "\n${GREEN}===========================================${NC}"
    echo -e "${GREEN}  生产环境启动成功！${NC}"
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${BLUE}访问地址：${NC}"
    echo -e "  应用服务: https://localhost"
    echo -e "  健康检查: https://localhost/health"
    echo -e "  API文档: https://localhost/docs"
    echo -e "${BLUE}监控地址：${NC}"
    echo -e "  Grafana: http://localhost:3000 (如果启用)"
    echo -e "  Prometheus: http://localhost:9090 (如果启用)"
    echo -e "${BLUE}常用命令：${NC}"
    echo -e "  查看日志: docker-compose -f docker-compose.prod.yml logs -f [service]"
    echo -e "  停止服务: docker-compose -f docker-compose.prod.yml down"
    echo -e "  重启服务: docker-compose -f docker-compose.prod.yml restart [service]"
    echo -e "  更新服务: docker-compose -f docker-compose.prod.yml pull && docker-compose -f docker-compose.prod.yml up -d"
}

# 主函数
main() {
    log_info "启动足球预测系统生产环境..."

    check_prerequisites
    create_directories
    create_ssl_certificates
    start_services
    wait_for_services
    show_status

    log_success "生产环境启动完成！"
}

# 错误处理
trap 'log_error "启动过程中发生错误，请检查日志"' ERR

# 运行主函数
main "$@"