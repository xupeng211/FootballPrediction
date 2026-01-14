#!/bin/bash
# V41.52: Docker 专用收割脚本
# ============================================
# 用途: 绕过 WSL2 网络转发 Bug，在 Docker 容器内执行收割
# 环境: 必须在 Docker 容器内运行，确保连接到真实数据库

set -e  # 遇到错误立即退出

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

# 检查 Docker 容器状态
check_docker() {
    log_info "检查 Docker 容器状态..."

    if ! docker-compose ps db | grep -q "Up"; then
        log_error "Docker 数据库容器未运行！"
        log_info "请先运行: make up"
        exit 1
    fi

    log_info "✅ Docker 容器运行正常"
}

# 验证数据库身份（Docker 内部）
verify_database() {
    log_info "验证数据库身份（Docker 内部检查）..."

    # 在 Docker 容器内执行检查
    TABLE_COUNT=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    " | tr -d ' ')

    if [ "$TABLE_COUNT" -lt 10 ]; then
        log_error "数据库表数量异常: $TABLE_COUNT (期望 >=10)"
        log_error "可能连接到了错误的数据库实例！"
        exit 1
    fi

    log_info "✅ 数据库验证通过 ($TABLE_COUNT 张表)"

    # 检查 matches 表记录数
    MATCHES_COUNT=$(docker-compose exec -T db psql -U football_user -d football_db -t -c "
        SELECT COUNT(*) FROM matches;
    " | tr -d ' ')

    log_info "✅ matches 表: $MATCHES_COUNT 场比赛"

    if [ "$MATCHES_COUNT" -lt 1000 ]; then
        log_warn "⚠️  比赛数量较少 ($MATCHES_COUNT)，请确认是否为测试数据库"
    fi
}

# 构建并运行 Docker 收割命令
run_harvest() {
    local LEAGUE="${1:-Ligue 1}"
    local SEASON="${2:-23/24}"

    log_info "=========================================="
    log_info "V41.52 Docker 收割模式"
    log_info "=========================================="
    log_info "联赛: $LEAGUE"
    log_info "赛季: $SEASON"
    log_info "环境: Docker 容器内部"
    log_info "=========================================="

    # 方式 1: 使用 docker-compose run（推荐）
    log_info "启动 Docker 收割容器..."

    docker-compose run --rm \
        -e BACKUP_SCHEDULE="" \
        -e DB_HOST=db \
        -e DB_PORT=5432 \
        -e DB_NAME=football_db \
        -e DB_USER=football_user \
        -e DB_PASSWORD=football_pass \
        -e PYTHONPATH=/app \
        -w /app \
        pipeline_worker \
        python main.py --action align-hashes --league "$LEAGUE" --season "$SEASON" --run-harvest
}

# 主函数
main() {
    log_info "🚀 V41.52 Docker 收割启动"
    echo ""

    # 检查 Docker 环境
    check_docker

    # 验证数据库身份
    verify_database
    echo ""

    # 运行收割
    run_harvest "$@"
}

# 执行主函数
main "$@"
