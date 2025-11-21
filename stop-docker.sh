#!/bin/bash

# ===========================================
# 足球预测系统 Docker 停止脚本
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

# 停止并清理服务
stop_services() {
    log_info "停止足球预测系统服务..."

    # 停止并删除容器、网络、匿名卷
    docker-compose -f docker-compose.simple.yml down -v --remove-orphans

    log_success "服务已停止"
}

# 清理镜像 (可选)
cleanup_images() {
    if [ "$1" = "--clean-images" ]; then
        log_info "清理相关镜像..."
        docker image prune -f
        log_success "镜像清理完成"
    fi
}

# 显示清理后的状态
show_cleanup_status() {
    log_info "清理完成！"
    echo ""
    echo "如需重新启动，请运行："
    echo "  ./start-docker.sh"
    echo ""
    echo "如需完全清理（包括数据卷），请运行："
    echo "  docker system prune -a --volumes"
    echo ""
}

# 主函数
main() {
    echo "=========================================="
    echo "🛑 足球预测系统 Docker 停止脚本"
    echo "=========================================="
    echo ""

    stop_services
    cleanup_images "$@"
    show_cleanup_status

    log_success "👋 足球预测系统已安全停止！"
}

# 执行主函数
main "$@"