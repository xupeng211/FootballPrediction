#!/bin/bash

# 生产环境启动脚本
# 用于部署Football Prediction应用到生产环境

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

# 检查必要的工具
check_requirements() {
    log_info "检查系统要求..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装"
        exit 1
    fi

    # 检查环境文件
    if [ ! -f ".env.production" ]; then
        log_error ".env.production 文件不存在，请先创建"
        exit 1
    fi

    log_success "系统要求检查通过"
}

# 检查SSL证书
check_ssl_certificates() {
    log_info "检查SSL证书..."

    SSL_DIR="./ssl"
    if [ ! -d "$SSL_DIR" ]; then
        log_warning "SSL目录不存在，创建中..."
        mkdir -p "$SSL_DIR"
    fi

    CERT_FILE="$SSL_DIR/cert.pem"
    KEY_FILE="$SSL_DIR/key.pem"

    if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
        log_warning "SSL证书不存在，请配置有效的SSL证书"
        log_info "证书路径："
        log_info "  - 证书文件：$CERT_FILE"
        log_info "  - 私钥文件：$KEY_FILE"
        exit 1
    fi

    log_success "SSL证书检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建必要的目录..."

    mkdir -p logs
    mkdir -p uploads
    mkdir -p backups
    mkdir -p monitoring/prometheus
    mkdir -p monitoring/grafana/provisioning
    mkdir -p monitoring/loki

    log_success "目录创建完成"
}

# 配置Nginx
configure_nginx() {
    log_info "配置Nginx..."

    NGINX_DIR="./nginx"
    if [ ! -d "$NGINX_DIR" ]; then
        mkdir -p "$NGINX_DIR/conf.d"
    fi

    # 复制Nginx配置模板
    if [ ! -f "$NGINX_DIR/nginx.conf" ]; then
        cp configs/nginx/nginx.conf.prod "$NGINX_DIR/nginx.conf"
    fi

    if [ ! -f "$NGINX_DIR/conf.d/default.conf" ]; then
        cp configs/nginx/default.conf.prod "$NGINX_DIR/conf.d/default.conf"
    fi

    log_success "Nginx配置完成"
}

# 配置监控
configure_monitoring() {
    log_info "配置监控系统..."

    # Prometheus配置
    if [ ! -f "monitoring/prometheus/prometheus.yml" ]; then
        cp configs/monitoring/prometheus.yml monitoring/prometheus/
    fi

    # Grafana配置
    if [ ! -f "monitoring/grafana/provisioning/datasources/datasource.yml" ]; then
        mkdir -p monitoring/grafana/provisioning/datasources
        cp configs/monitoring/grafana/datasource.yml monitoring/grafana/provisioning/datasources/
    fi

    # Loki配置
    if [ ! -f "monitoring/loki/loki-config.yaml" ]; then
        cp configs/monitoring/loki/loki-config.yaml monitoring/loki/
    fi

    log_success "监控系统配置完成"
}

# 数据库迁移
run_migrations() {
    log_info "运行数据库迁移..."

    # 等待数据库启动
    log_info "等待数据库启动..."
    sleep 10

    # 运行迁移
    docker-compose -f docker-compose.prod.yml exec app alembic upgrade head

    log_success "数据库迁移完成"
}

# 启动服务
start_services() {
    log_info "启动生产服务..."

    # 构建并启动所有服务
    docker-compose -f docker-compose.prod.yml up -d --build

    log_success "服务启动完成"
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 等待服务启动
    sleep 30

    # 检查应用健康状态
    if curl -f http://localhost:8000/api/health > /dev/null 2>&1; then
        log_success "应用健康检查通过"
    else
        log_error "应用健康检查失败"
        exit 1
    fi

    # 检查数据库连接
    if docker-compose -f docker-compose.prod.yml exec db pg_isready -U $DB_USER > /dev/null 2>&1; then
        log_success "数据库连接正常"
    else
        log_error "数据库连接失败"
        exit 1
    fi

    # 检查Redis连接
    if docker-compose -f docker-compose.prod.yml exec redis redis-cli ping > /dev/null 2>&1; then
        log_success "Redis连接正常"
    else
        log_error "Redis连接失败"
        exit 1
    fi

    log_success "所有健康检查通过"
}

# 显示服务状态
show_status() {
    log_info "服务状态："
    docker-compose -f docker-compose.prod.yml ps

    echo ""
    log_info "访问地址："
    echo "  - 应用地址：https://yourdomain.com"
    echo "  - API文档：https://yourdomain.com/docs"
    echo "  - Grafana：https://yourdomain.com:3000"
    echo "  - Prometheus：https://yourdomain.com:9090"
}

# 主函数
main() {
    log_info "开始部署Football Prediction应用到生产环境..."

    # 检查要求
    check_requirements

    # 创建目录
    create_directories

    # 检查SSL证书
    check_ssl_certificates

    # 配置Nginx
    configure_nginx

    # 配置监控
    configure_monitoring

    # 启动服务
    start_services

    # 运行迁移
    run_migrations

    # 健康检查
    health_check

    # 显示状态
    show_status

    log_success "生产环境部署完成！"
}

# 处理命令行参数
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        log_info "停止生产服务..."
        docker-compose -f docker-compose.prod.yml down
        log_success "服务已停止"
        ;;
    restart)
        log_info "重启生产服务..."
        docker-compose -f docker-compose.prod.yml restart
        log_success "服务已重启"
        ;;
    logs)
        docker-compose -f docker-compose.prod.yml logs -f
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法: $0 {start|stop|restart|logs|status}"
        exit 1
        ;;
esac
