#!/bin/bash

# ===========================================
# 足球预测系统 Docker 一键启动脚本
# ===========================================

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

# 检查 Docker 和 Docker Compose
check_dependencies() {
    log_info "检查系统依赖..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或未运行，请先安装 Docker"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    log_success "系统依赖检查通过"
}

# 清理旧容器
cleanup_old_containers() {
    log_info "清理旧容器和镜像..."

    # 停止并删除旧容器
    docker-compose -f docker-compose.simple.yml down -v --remove-orphans 2>/dev/null || true

    # 删除旧镜像 (可选)
    # docker image prune -f

    log_success "清理完成"
}

# 构建和启动服务
start_services() {
    log_info "开始构建和启动服务..."

    # 使用简化的 docker-compose 文件启动服务
    docker-compose -f docker-compose.simple.yml up --build -d

    log_success "服务启动命令已执行"
}

# 等待服务健康检查
wait_for_services() {
    log_info "等待服务启动和健康检查..."

    # 等待数据库启动
    log_info "等待 PostgreSQL 数据库启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if docker exec football_prediction_db pg_isready -U postgres -d football_prediction >/dev/null 2>&1; then
            log_success "PostgreSQL 数据库已就绪"
            break
        fi
        sleep 2
        ((timeout-=2))
    done

    if [ $timeout -le 0 ]; then
        log_error "PostgreSQL 数据库启动超时"
        exit 1
    fi

    # 等待 Redis 启动
    log_info "等待 Redis 缓存启动..."
    timeout=30
    while [ $timeout -gt 0 ]; do
        if docker exec football_prediction_redis redis-cli ping >/dev/null 2>&1; then
            log_success "Redis 缓存已就绪"
            break
        fi
        sleep 2
        ((timeout-=2))
    done

    if [ $timeout -le 0 ]; then
        log_error "Redis 缓存启动超时"
        exit 1
    fi

    # 等待后端 API 启动
    log_info "等待后端 API 服务启动..."
    timeout=120
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:8000/health >/dev/null 2>&1; then
            log_success "后端 API 服务已就绪"
            break
        fi
        sleep 5
        ((timeout-=5))
    done

    if [ $timeout -le 0 ]; then
        log_error "后端 API 服务启动超时"
        exit 1
    fi

    # 等待前端启动
    log_info "等待前端服务启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:3000/health >/dev/null 2>&1; then
            log_success "前端服务已就绪"
            break
        fi
        sleep 3
        ((timeout-=3))
    done

    if [ $timeout -le 0 ]; then
        log_warning "前端服务健康检查超时，但可能仍在启动中"
    fi
}

# 显示服务状态
show_status() {
    log_info "显示服务状态..."
    echo ""
    echo "=========================================="
    echo "🚀 足球预测系统已成功启动！"
    echo "=========================================="
    echo ""
    echo "📊 服务访问地址："
    echo "   🌐 前端应用:  http://localhost:3000"
    echo "   🔧 后端API:   http://localhost:8000"
    echo "   📖 API文档:   http://localhost:8000/docs"
    echo "   ❤️  健康检查:  http://localhost:8000/health"
    echo ""
    echo "🔍 服务管理命令："
    echo "   查看日志: docker-compose -f docker-compose.simple.yml logs -f"
    echo "   停止服务: docker-compose -f docker-compose.simple.yml down"
    echo "   重启服务: docker-compose -f docker-compose.simple.yml restart"
    echo ""
    echo "🗄️  数据库连接："
    echo "   主机: localhost"
    echo "   端口: 5432"
    echo "   数据库: football_prediction"
    echo "   用户名: postgres"
    echo "   密码: football_prediction_2024"
    echo ""
}

# 错误处理
handle_error() {
    log_error "启动过程中发生错误，正在清理..."
    docker-compose -f docker-compose.simple.yml down -v
    exit 1
}

# 主函数
main() {
    echo "=========================================="
    echo "🏆 足球预测系统 Docker 一键启动脚本"
    echo "=========================================="
    echo ""

    # 设置错误处理
    trap handle_error ERR

    # 执行启动步骤
    check_dependencies
    cleanup_old_containers
    start_services
    wait_for_services
    show_status

    log_success "🎉 所有服务启动完成！"
}

# 执行主函数
main "$@"