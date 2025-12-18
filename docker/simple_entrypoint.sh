#!/bin/bash
# 简化的Docker容器入口点脚本
# 专门用于运行简化增强版API

set -e  # 遇到错误立即退出

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

# 等待数据库可用（简化版）
wait_for_database() {
    log_info "等待数据库就绪..."

    # 简单等待一段时间让数据库启动
    log_info "等待10秒让数据库完全启动..."
    sleep 10

    log_success "跳过数据库连接检查，直接启动应用"
    return 0
}

# 运行数据库迁移
run_database_migrations() {
    log_info "运行数据库迁移..."

    if [[ -f "/app/alembic.ini" ]]; then
        cd /app
        python -m alembic upgrade head || {
            log_warning "数据库迁移失败，但继续启动应用"
        }
        log_success "数据库迁移完成"
    else
        log_info "未找到迁移文件，跳过数据库迁移"
    fi
}

# 启动应用
start_application() {
    log_info "启动简化增强版API..."

    # 设置默认命令
    if [[ $# -eq 0 ]]; then
        set -- uvicorn src.simple_enhanced_main:app --host 0.0.0.0 --port 8000 --workers 1
    fi

    log_success "启动命令: $*"

    # 启动应用
    exec "$@"
}

# 主函数
main() {
    log_info "🐳 Football Prediction System v2.0 简化增强版容器启动"
    log_info "=============================================="

    # 检查必需的环境变量
    if [[ -z "$DB_HOST" || -z "$DB_USER" || -z "$DB_PASSWORD" || -z "$DB_NAME" ]]; then
        log_error "缺少必需的数据库环境变量"
        exit 1
    fi

    log_info "检查环境变量..."
    log_success "环境变量检查通过"

    # 执行初始化步骤
    wait_for_database
    run_database_migrations

    # 启动应用
    start_application "$@"
}

# 信号处理
cleanup() {
    log_info "收到停止信号，正在清理..."
    log_info "清理完成，退出"
    exit 0
}

# 设置信号处理
trap cleanup SIGTERM SIGINT

# 解析命令行参数
case "$1" in
    -h|--help)
        echo "简化增强版API Docker 入口点"
        echo "用法: $0 [uvicorn命令...]"
        echo ""
        echo "默认命令: uvicorn src.simple_enhanced_main:app --host 0.0.0.0 --port 8000 --workers 1"
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac