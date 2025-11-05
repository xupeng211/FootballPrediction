#!/bin/bash

# =================================================================
# 生产环境部署脚本
# Production Deployment Script
# =================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置
PROJECT_NAME="football-prediction"
DOCKER_REGISTRY="your-registry.com"  # 如果使用私有镜像仓库
VERSION=${1:-latest}

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# 检查环境
check_environment() {
    log_info "检查部署环境..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose未安装"
        exit 1
    fi

    # 检查环境文件
    if [[ ! -f "docker/environments/.env.prod" ]]; then
        log_error "生产环境配置文件不存在: docker/environments/.env.prod"
        log_info "请复制 docker/environments/.env.prod.example 并配置"
        exit 1
    fi

    log_success "环境检查通过"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."

    # 构建应用镜像
    docker build \
        --target production \
        --tag ${PROJECT_NAME}:${VERSION} \
        --tag ${PROJECT_NAME}:latest \
        --build-arg APP_VERSION=${VERSION} \
        --build-arg BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ") \
        --build-arg GIT_COMMIT=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown") \
        --build-arg GIT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown") \
        .

    log_success "镜像构建完成"
}

# 推送镜像（可选）
push_images() {
    if [[ -n "${DOCKER_REGISTRY}" && "${DOCKER_REGISTRY}" != "your-registry.com" ]]; then
        log_info "推送镜像到仓库..."

        docker tag ${PROJECT_NAME}:${VERSION} ${DOCKER_REGISTRY}/${PROJECT_NAME}:${VERSION}
        docker tag ${PROJECT_NAME}:latest ${DOCKER_REGISTRY}/${PROJECT_NAME}:latest

        docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}:${VERSION}
        docker push ${DOCKER_REGISTRY}/${PROJECT_NAME}:latest

        log_success "镜像推送完成"
    else
        log_warn "跳过镜像推送（未配置仓库地址）"
    fi
}

# 部署服务
deploy_services() {
    log_info "部署服务..."

    # 加载环境变量
    source docker/environments/.env.prod

    # 使用生产配置部署
    docker-compose -f docker-compose.prod.yml down
    docker-compose -f docker-compose.prod.yml up -d

    log_success "服务部署完成"
}

# 等待服务启动
wait_for_services() {
    log_info "等待服务启动..."

    # 等待应用启动
    log_info "等待应用服务启动..."
    for i in {1..30}; do
        if curl -f http://localhost/health &>/dev/null; then
            log_success "应用服务已启动"
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_error "应用服务启动超时"
            exit 1
        fi
        sleep 2
    done

    # 等待数据库启动
    log_info "等待数据库服务启动..."
    for i in {1..30}; do
        if docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U ${POSTGRES_USER} &>/dev/null; then
            log_success "数据库服务已启动"
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_error "数据库服务启动超时"
            exit 1
        fi
        sleep 2
    done

    # 等待Redis启动
    log_info "等待Redis服务启动..."
    for i in {1..30}; do
        if docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping &>/dev/null; then
            log_success "Redis服务已启动"
            break
        fi
        if [[ $i -eq 30 ]]; then
            log_error "Redis服务启动超时"
            exit 1
        fi
        sleep 2
    done
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 检查服务状态
    if ! docker-compose -f docker-compose.prod.yml ps | grep -q "Up"; then
        log_error "部分服务未正常运行"
        docker-compose -f docker-compose.prod.yml ps
        exit 1
    fi

    # 检查应用健康
    if ! curl -f http://localhost/health &>/dev/null; then
        log_error "应用健康检查失败"
        exit 1
    fi

    # 检查数据库连接
    if ! docker-compose -f docker-compose.prod.yml exec -T db pg_isready -U ${POSTGRES_USER} &>/dev/null; then
        log_error "数据库健康检查失败"
        exit 1
    fi

    # 检查Redis连接
    if ! docker-compose -f docker-compose.prod.yml exec -T redis redis-cli ping &>/dev/null; then
        log_error "Redis健康检查失败"
        exit 1
    fi

    log_success "所有服务健康检查通过"
}

# 显示服务信息
show_service_info() {
    log_info "服务信息:"
    echo "----------------------------------------"
    echo "🌐 应用地址: http://localhost"
    echo "📊 Grafana监控: http://localhost:3000"
    echo "📈 Prometheus: http://localhost:9090"
    echo "📝 Loki日志: http://localhost:3100"
    echo "----------------------------------------"
    echo "📋 查看日志: docker-compose -f docker-compose.prod.yml logs -f"
    echo "🛑 停止服务: docker-compose -f docker-compose.prod.yml down"
    echo "----------------------------------------"
}

# 清理旧版本
cleanup() {
    log_info "清理旧版本..."

    # 清理未使用的镜像
    docker image prune -f

    # 清理未使用的卷（谨慎使用）
    # docker volume prune -f

    log_success "清理完成"
}

# 主函数
main() {
    log_info "========================================="
    log_info "足球预测系统生产环境部署开始"
    log_info "版本: ${VERSION}"
    log_info "时间: $(date)"
    log_info "========================================="

    check_environment
    build_images
    push_images
    deploy_services
    wait_for_services
    health_check
    show_service_info
    cleanup

    log_success "========================================="
    log_success "🎉 部署完成！"
    log_success "========================================="
}

# 错误处理
error_handler() {
    log_error "部署失败！"
    log_info "查看错误日志: docker-compose -f docker-compose.prod.yml logs"
    exit 1
}

trap error_handler ERR

# 执行主函数
main "$@"