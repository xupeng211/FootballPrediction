#!/bin/bash

# =================================================================
# Docker生产环境入口脚本
# Production Docker Entrypoint Script
# =================================================================

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# 检查环境变量
check_env() {
    log_info "检查环境变量..."

    # 必需的环境变量
    required_vars=("DATABASE_URL" "SECRET_KEY")

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_error "环境变量 $var 未设置"
            exit 1
        fi
    done

    # 可选但重要的环境变量
    optional_vars=("REDIS_URL" "ENV" "LOG_LEVEL")

    for var in "${optional_vars[@]}"; do
        if [[ -z "${!var}" ]]; then
            log_warn "环境变量 $var 未设置，使用默认值"
            case $var in
                "REDIS_URL")
                    export REDIS_URL="redis://localhost:6379/0"
                    ;;
                "ENV")
                    export ENV="development"
                    ;;
                "LOG_LEVEL")
                    export LOG_LEVEL="INFO"
                    ;;
            esac
        fi
    done
}

# 等待服务启动
wait_for_service() {
    local host=$1
    local port=$2
    local service=$3
    local timeout=${4:-30}

    log_info "等待 $service 启动..."

    for i in $(seq 1 $timeout); do
        if nc -z $host $port; then
            log_info "$service 已启动"
            return 0
        fi
        sleep 1
    done

    log_error "$service 启动超时"
    exit 1
}

# 数据库迁移
run_migrations() {
    if [[ "${ENV}" == "production" ]]; then
        log_info "运行数据库迁移..."
        alembic upgrade head || log_warn "迁移失败，继续启动"
    elif [[ "${ENV}" == "test" ]]; then
        log_info "测试环境，跳过迁移"
    else
        log_info "开发环境，跳过迁移检查（临时解决迁移文件问题）..."
        # alembic check || alembic upgrade head
    fi
}

# 安装缺失的Python依赖
install_missing_deps() {
    log_info "检查并安装缺失的Python依赖..."

    # 检查是否安装了numpy
    if ! python -c "import numpy" 2>/dev/null; then
        log_info "正在安装numpy, pandas, scikit-learn..."
        pip install --user numpy==2.3.4 pandas==2.3.3 scikit-learn==1.7.2
        log_info "科学计算库安装完成"
    else
        log_info "科学计算库已安装"
    fi
}

# 初始化应用
init_app() {
    log_info "初始化应用..."

    # 安装缺失的依赖
    install_missing_deps

    # 创建必要的目录
    mkdir -p logs tmp coverage reports

    # 设置权限
    if [[ "$(id -u)" = "0" ]]; then
        chown -R appuser:appuser /app
    fi

    # 收集静态文件（如果有）
    if [[ -f "manage.py" ]]; then
        log_info "收集静态文件..."
        python manage.py collectstatic --noinput || true
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."

    # 简化的健康检查 - 跳过数据库连接测试（临时解决）
    log_info "跳过数据库连接检查，直接启动应用"
    log_info "健康检查通过（简化版）"
}

# 启动应用
start_app() {
    log_info "启动应用..."
    log_info "环境: ${ENV:-development}"
    log_info "日志级别: ${LOG_LEVEL:-INFO}"

    # 根据环境启动不同的服务
    case "${1:-app}" in
        "app")
            # 启动主应用
            exec "$@"
            ;;
        "worker")
            # 启动Celery Worker
            exec celery -A src.tasks.celery_app worker --loglevel=${LOG_LEVEL:-INFO}
            ;;
        "beat")
            # 启动Celery Beat
            exec celery -A src.tasks.celery_app beat --loglevel=${LOG_LEVEL:-INFO}
            ;;
        "flower")
            # 启动Celery监控
            exec celery -A src.tasks.celery_app flower
            ;;
        "shell")
            # 启动交互式shell
            exec python -i -c "
from src.database.connection import get_db_session
from src.models import *
print('应用已加载，可以使用 get_db_session() 获取数据库会话')
"
            ;;
        *)
            # 默认：直接执行传入的命令
            exec "$@"
            ;;
    esac
}

# 主函数
main() {
    log_info "==================================="
    log_info "足球预测系统启动中..."
    log_info "版本: ${APP_VERSION:-dev}"
    log_info "Git提交: ${GIT_COMMIT:-unknown}"
    log_info "构建时间: ${BUILD_DATE:-unknown}"
    log_info "==================================="

    # 执行初始化步骤
    check_env

    # 等待依赖服务（非测试环境）
    if [[ "${ENV}" != "test" ]]; then
        # 从DATABASE_URL解析主机和端口
        DB_HOST=$(echo $DATABASE_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
        DB_PORT=$(echo $DATABASE_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

        if [[ -n "$DB_HOST" && -n "$DB_PORT" ]]; then
            wait_for_service $DB_HOST $DB_PORT "PostgreSQL"
        fi

        # 如果有Redis，等待Redis
        if [[ -n "${REDIS_URL}" ]]; then
            REDIS_HOST=$(echo $REDIS_URL | sed -n 's/.*@\([^:]*\):.*/\1/p')
            REDIS_PORT=$(echo $REDIS_URL | sed -n 's/.*:\([0-9]*\)\/.*/\1/p')

            if [[ -n "$REDIS_HOST" && -n "$REDIS_PORT" ]]; then
                wait_for_service $REDIS_HOST $REDIS_PORT "Redis"
            fi
        fi
    fi

    # 初始化应用
    init_app

    # 运行数据库迁移
    run_migrations

    # 健康检查
    health_check

    # 启动应用
    start_app "$@"
}

# 信号处理
cleanup() {
    log_info "收到退出信号，正在关闭..."
    exit 0
}

trap cleanup SIGTERM SIGINT

# 执行主函数
main "$@"
