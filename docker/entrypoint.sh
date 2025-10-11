#!/bin/bash
# Docker容器入口脚本
# 负责初始化和启动应用

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
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
        alembic upgrade head
    elif [[ "${ENV}" == "test" ]]; then
        log_info "测试环境，跳过迁移"
    else
        log_info "开发环境，检查迁移状态..."
        alembic check || alembic upgrade head
    fi
}

# 初始化应用
init_app() {
    log_info "初始化应用..."

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

    # 检查数据库连接
    python -c "
import asyncio
from sqlalchemy import create_engine
import os

try:
    engine = create_engine(os.getenv('DATABASE_URL').replace('+asyncpg', ''))
    with engine.connect() as conn:
        conn.execute('SELECT 1')
    print('数据库连接正常')
except Exception as e:
    print(f'数据库连接失败: {e}')
    exit(1)
" || exit 1

    # 检查Redis连接（如果配置了）
    if [[ -n "${REDIS_URL}" ]]; then
        python -c "
import redis
import os

try:
    r = redis.from_url(os.getenv('REDIS_URL'))
    r.ping()
    print('Redis连接正常')
except Exception as e:
    print(f'Redis连接失败: {e}')
    exit(1)
" || exit 1
    fi

    log_info "健康检查通过"
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
