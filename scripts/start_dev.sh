#!/bin/bash

# Football Prediction System - 开发环境启动脚本
#
# 使用方法:
#   ./scripts/start_dev.sh          # 启动开发服务器
#   ./scripts/start_dev.sh --db     # 同时启动数据库管理工具
#   ./scripts/start_dev.sh --redis  # 同时启动Redis管理工具

set -euo pipefail

# 配置
API_HOST="0.0.0.0"
API_PORT="8000"
DB_HOST="localhost"
DB_PORT="5432"
REDIS_HOST="localhost"
REDIS_PORT="6379"

# 颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# 检查环境
check_environment() {
    log_info "检查开发环境..."

    # 检查Python虚拟环境
    if [[ -z "${VIRTUAL_ENV:-}" ]]; then
        log_warning "未检测到虚拟环境，尝试激活..."
        if [[ -f ".venv/bin/activate" ]]; then
            source .venv/bin/activate
            log_success "虚拟环境已激活"
        else
            log_error "虚拟环境不存在，请运行: python -m venv .venv"
            exit 1
        fi
    fi

    # 检查依赖
    if ! python -c "import fastapi, uvicorn" 2>/dev/null; then
        log_error "缺少必要依赖，请运行: pip install -r requirements.txt"
        exit 1
    fi

    log_success "开发环境检查通过"
}

# 启动数据库服务
start_database() {
    log_info "启动数据库服务..."

    # 检查PostgreSQL是否运行
    if ! docker ps --filter "name=football-dev-db" --filter "status=running" | grep -q "football-dev-db"; then
        log_info "启动PostgreSQL容器..."
        docker run -d --name football-dev-db \
            -e POSTGRES_DB=football_prediction_dev \
            -e POSTGRES_USER=football_user \
            -e POSTGRES_PASSWORD=football_pass \
            -p 5432:5432 \
            postgres:15
        log_success "PostgreSQL已启动"
    else
        log_info "PostgreSQL已在运行"
    fi

    # 等待数据库就绪
    log_info "等待数据库就绪..."
    for i in {1..30}; do
        if docker exec football-dev-db pg_isready -U football_user -d football_prediction_dev >/dev/null 2>&1; then
            log_success "数据库就绪"
            break
        fi
        sleep 1
    done
}

# 启动Redis服务
start_redis() {
    log_info "启动Redis服务..."

    # 检查Redis是否运行
    if ! docker ps --filter "name=football-dev-redis" --filter "status=running" | grep -q "football-dev-redis"; then
        log_info "启动Redis容器..."
        docker run -d --name football-dev-redis \
            -p 6379:6379 \
            redis:7-alpine
        log_success "Redis已启动"
    else
        log_info "Redis已在运行"
    fi

    # 等待Redis就绪
    log_info "等待Redis就绪..."
    for i in {1..10}; do
        if docker exec football-dev-redis redis-cli ping >/dev/null 2>&1; then
            log_success "Redis就绪"
            break
        fi
        sleep 1
    done
}

# 启动开发服务器
start_dev_server() {
    log_info "启动开发服务器..."

    # 设置环境变量
    export ENVIRONMENT=development
    export DEBUG=true
    export PYTHONPATH=$(pwd)

    # 启动服务器
    log_success "开发服务器启动中..."
    log_info "📍 访问地址: http://localhost:${API_PORT}"
    log_info "📚 API文档: http://localhost:${API_PORT}/docs"
    log_info "🔍 健康检查: http://localhost:${API_PORT}/health"

    # 启动uvicorn服务器（带热重载）
    python -m uvicorn src.main:app \
        --host ${API_HOST} \
        --port ${API_PORT} \
        --reload \
        --reload-dir ./src \
        --log-level debug \
        --access-log
}

# 启动管理工具
start_management_tools() {
    local enable_db=${1:-false}
    local enable_redis=${2:-false}

    if [[ "$enable_db" == "true" ]]; then
        log_info "启动数据库管理工具..."
        if ! docker ps --filter "name=adminer" --filter "status=running" | grep -q "adminer"; then
            docker run -d --name adminer \
                -p 8080:8080 \
                --link football-dev-db:db \
                adminer
            log_success "Adminer数据库管理界面: http://localhost:8080"
        fi
    fi

    if [[ "$enable_redis" == "true" ]]; then
        log_info "启动Redis管理工具..."
        if ! docker ps --filter "name=redis-commander" --filter "status=running" | grep -q "redis-commander"; then
            docker run -d --name redis-commander \
                -e REDIS_HOSTS=local:football-dev-redis:6379 \
                -p 8081:8081 \
                --link football-dev-redis:redis \
                rediscommander/redis-commander:latest
            log_success "Redis Commander管理界面: http://localhost:8081"
        fi
    fi
}

# 显示开发环境信息
show_dev_info() {
    echo ""
    log_success "=== 开发环境已启动 ==="
    echo ""
    log_info "🌐 服务地址:"
    echo "   • API服务:     http://localhost:${API_PORT}"
    echo "   • API文档:     http://localhost:${API_PORT}/docs"
    echo "   • 健康检查:     http://localhost:${API_PORT}/health"
    echo ""
    log_info "🔧 开发工具:"
    echo "   • 热重载:      已启用 (保存文件自动重启)"
    echo "   • 日志级别:    DEBUG"
    echo "   • 环境模式:    development"
    echo ""
    log_info "📊 数据库连接:"
    echo "   • PostgreSQL:  ${DB_HOST}:${DB_PORT}"
    echo "   • Redis:       ${REDIS_HOST}:${REDIS_PORT}"
    echo ""
    log_info "💡 开发命令:"
    echo "   • 停止服务:     Ctrl+C"
    echo "   • 查看日志:     docker logs football-dev-db"
    echo "   • 进入容器:     docker exec -it football-dev-db bash"
    echo ""
}

# 主函数
main() {
    local enable_db=false
    local enable_redis=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --db)
                enable_db=true
                shift
                ;;
            --redis)
                enable_redis=true
                shift
                ;;
            --all)
                enable_db=true
                enable_redis=true
                shift
                ;;
            -h|--help)
                echo "用法: $0 [选项]"
                echo ""
                echo "选项:"
                echo "  --db      启动数据库管理工具 (Adminer)"
                echo "  --redis   启动Redis管理工具 (Redis Commander)"
                echo "  --all     启动所有管理工具"
                echo "  -h, --help 显示帮助信息"
                echo ""
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    # 执行启动流程
    check_environment
    start_database
    start_redis
    start_management_tools "$enable_db" "$enable_redis"
    show_dev_info

    # 启动开发服务器（这会阻塞终端）
    start_dev_server
}

# 脚本退出时清理
trap 'log_info "开发服务器已停止"' EXIT

# 执行主函数
main "$@"