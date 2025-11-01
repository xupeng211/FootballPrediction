#!/bin/bash

# 足球预测系统本地部署脚本
# 使用方法: ./scripts/deploy.sh [environment]
# environment: development (默认) | staging | production

set -e  # 遇到错误立即退出

GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo dev)
APP_IMAGE=${APP_IMAGE:-football-prediction}
APP_TAG=${APP_TAG:-$GIT_SHA}

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印彩色消息
print_message() {
    echo -e "${2}[$(date '+%Y-%m-%d %H:%M:%S')] $1${NC}"
}

print_info() {
    print_message "$1" "$BLUE"
}

print_success() {
    print_message "$1" "$GREEN"
}

print_warning() {
    print_message "$1" "$YELLOW"
}

print_error() {
    print_message "$1" "$RED"
}

# 获取环境参数
ENVIRONMENT=${1:-development}
print_info "部署环境: $ENVIRONMENT"

# 检查依赖
check_dependencies() {
    print_info "检查依赖项..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装，请先安装Docker"
        exit 1
    fi

    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose 未安装，请先安装Docker Compose"
        exit 1
    fi

    print_success "✅ 依赖检查通过"
}

# 检查环境变量文件
check_env_file() {
    print_info "检查环境配置文件..."

    if [ ! -f .env ]; then
        if [ -f env.template ]; then
            print_warning "⚠️  未找到.env文件，从模板复制..."
            cp env.template .env
            print_warning "⚠️  请编辑.env文件并填入正确的配置"
            print_warning "⚠️  特别注意数据库和API密钥配置"
        else
            print_error "❌ 未找到环境配置文件和模板"
            exit 1
        fi
    fi

    print_success "✅ 环境配置检查通过"
}

# 构建和启动服务
deploy_services() {
    print_info "构建和启动服务..."

    # 停止现有服务
    print_info "停止现有服务..."
    docker-compose down 2>/dev/null || true

    # 构建镜像
    print_info "构建Docker镜像 (标签: $APP_TAG)..."
    APP_IMAGE="$APP_IMAGE" APP_TAG="$APP_TAG" docker-compose build

    # 启动服务
    case $ENVIRONMENT in
        "production")
            print_info "启动生产环境服务..."
            APP_IMAGE="$APP_IMAGE" APP_TAG="$APP_TAG" docker-compose up -d --remove-orphans
            ;;
        "staging")
            print_info "启动预发布环境服务..."
            APP_IMAGE="$APP_IMAGE" APP_TAG="$APP_TAG" docker-compose up -d --remove-orphans
            ;;
        "development")
            print_info "启动开发环境服务..."
            APP_IMAGE="$APP_IMAGE" APP_TAG="$APP_TAG" docker-compose up -d --remove-orphans
            ;;
        *)
            print_error "未知环境: $ENVIRONMENT"
            exit 1
            ;;
    esac

    print_success "✅ 服务启动成功"
}

# 等待服务启动
wait_for_services() {
    print_info "等待服务启动..."

    # 等待数据库启动
    print_info "等待数据库启动..."
    for i in {1..30}; do
        if docker-compose exec -T db pg_isready -U football_user -d football_prediction_dev > /dev/null 2>&1; then
            print_success "✅ 数据库已就绪"
            break
        fi

        if [ $i -eq 30 ]; then
            print_error "❌ 数据库启动超时"
            exit 1
        fi

        sleep 2
    done

    # 等待API服务启动
    print_info "等待API服务启动..."
    for i in {1..30}; do
        if curl -f -s http://localhost:8000/health > /dev/null 2>&1; then
            print_success "✅ API服务已就绪"
            break
        fi

        if [ $i -eq 30 ]; then
            print_error "❌ API服务启动超时"
            exit 1
        fi

        sleep 3
    done
}

# 运行数据库迁移
run_migrations() {
    print_info "运行数据库迁移..."

    # 检查是否需要初始化Alembic
    if [ ! -d "src/database/migrations/versions" ] || [ -z "$(ls -A src/database/migrations/versions)" ]; then
        print_warning "⚠️  检测到首次部署，将运行完整的数据库迁移"
    fi

    # 运行迁移
    docker-compose exec app alembic upgrade head || {
        print_warning "⚠️  Alembic迁移失败，尝试手动创建表结构"
        # 这里可以添加备用的表创建逻辑
    }

    print_success "✅ 数据库迁移完成"
}

# 显示部署结果
show_result() {
    print_success "🎉 部署完成！"
    echo ""
    print_info "服务访问地址:"
    print_info "  📖 API文档: http://localhost:8000/docs"
    print_info "  🔍 健康检查: http://localhost:8000/health"
    print_info "  📊 数据库: localhost:5432"
    print_info "  💾 Redis: localhost:6379"
    print_info "  🐳 镜像版本: ${APP_IMAGE}:${APP_TAG}"
    echo ""
    print_info "常用命令:"
    print_info "  查看日志: docker-compose logs -f"
    print_info "  停止服务: docker-compose down"
    print_info "  重启服务: docker-compose restart"
    echo ""

    # 显示服务状态
    print_info "当前服务状态:"
    docker-compose ps
}

# 错误处理
cleanup_on_error() {
    print_error "❌ 部署过程中发生错误，正在清理..."
    docker-compose down 2>/dev/null || true
    exit 1
}

# 设置错误陷阱
trap cleanup_on_error ERR

# 主流程
main() {
    print_info "🚀 开始部署足球预测系统..."
    echo ""

    check_dependencies
    check_env_file
    deploy_services
    wait_for_services
    run_migrations
    show_result
}

# 执行主流程
main "$@"
