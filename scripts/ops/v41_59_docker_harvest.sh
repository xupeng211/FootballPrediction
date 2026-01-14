#!/bin/bash
# V41.59: Docker 收割脚本 - 标准化版本
# ============================================
# 用途: 在本地环境运行收割，连接到 Docker 数据库
# 环境: WSL2/本地，通过端口映射连接 Docker 数据库
# 确保本地 PostgreSQL 服务已停止

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

# 验证数据库身份
verify_database() {
    log_info "验证数据库身份..."

    TABLE_COUNT=$(PGPASSWORD=football_pass psql -h 127.0.0.1 -p 5432 -U football_user -d football_db -t -c "
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
    " | tr -d ' ')

    if [ -z "$TABLE_COUNT" ]; then
        log_error "无法连接到数据库！"
        log_error "请确保 Docker 数据库已启动并映射到 127.0.0.1:5432"
        exit 1
    fi

    if [ "$TABLE_COUNT" -lt 10 ]; then
        log_error "数据库表数量异常: $TABLE_COUNT (期望 >=10)"
        log_error "可能连接到了错误的数据库实例！"
        log_error "请停止本地 PostgreSQL 服务: sudo service postgresql stop"
        exit 1
    fi

    log_info "✅ 数据库验证通过 ($TABLE_COUNT 张表)"

    # 检查 matches 表记录数
    MATCHES_COUNT=$(PGPASSWORD=football_pass psql -h 127.0.0.1 -p 5432 -U football_user -d football_db -t -c "
        SELECT COUNT(*) FROM matches;
    " | tr -d ' ')

    log_info "✅ matches 表: $MATCHES_COUNT 场比赛"

    if [ "$MATCHES_COUNT" -lt 1000 ]; then
        log_warn "⚠️  比赛数量较少 ($MATCHES_COUNT)，请确认是否为测试数据库"
    fi
}

# 检查端口占用
check_port() {
    log_info "检查端口占用..."

    if netstat -tulpn 2>/dev/null | grep -q ":5432.*postgres"; then
        log_warn "⚠️  检测到本地 PostgreSQL 服务占用 5432 端口"
        log_warn "建议: 停止本地 PostgreSQL 服务"
        log_warn "命令: sudo service postgresql stop"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "用户取消"
            exit 0
        fi
    fi
}

# 运行收割
run_harvest() {
    local LEAGUE="${1:-Ligue 1}"
    local SEASON="${2:-23/24}"

    log_info "=========================================="
    log_info "V41.59 Docker 收割模式（标准化）"
    log_info "=========================================="
    log_info "联赛: $LEAGUE"
    log_info "赛季: $SEASON"
    log_info "数据库: 127.0.0.1:5432 (Docker 映射)"
    log_info "=========================================="
    echo ""

    # 设置环境变量
    export PGHOST=127.0.0.1
    export PGPORT=5432
    export PGDATABASE=football_db
    export PGUSER=football_user
    export PGPASSWORD=football_pass

    # 运行收割
    python main.py --action align-hashes --league "$LEAGUE" --season "$SEASON" --run-harvest
}

# 主函数
main() {
    log_info "🚀 V41.59 Docker 收割启动（标准化版本）"
    echo ""

    # 检查 Docker 环境
    check_docker

    # 检查端口占用
    check_port

    # 验证数据库身份
    verify_database
    echo ""

    # 运行收割
    run_harvest "$@"
}

# 执行主函数
main "$@"
