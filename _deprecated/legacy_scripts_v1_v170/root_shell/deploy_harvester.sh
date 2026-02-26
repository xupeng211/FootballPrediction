#!/bin/bash
# ============================================
# V20.8 焦土收割机 - 标准化部署脚本 (最终版)
# ============================================
#
# 功能:
# 1. 数据库备份 (match_features_training)
# 2. docker-compose build（同步最新代码）
# 3. pytest tests/（跑通自动化测试）
# 4. docker-compose up -d harvester（正式后台运行）
#
# 作者: SRE Lead
# 日期: 2025-12-25
# 版本: V20.8 Final
# ============================================

set -e  # 遇到错误立即退出
set -u  # 使用未定义变量时报错

# ==================== 配置 ====================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_NAME="footballprediction"
BACKUP_DIR="./data/backups"
LOG_FILE="/tmp/harvester_deploy_$(date +%Y%m%d_%H%M%S).log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ==================== 函数 ====================

log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1" | tee -a "$LOG_FILE"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $1" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${CYAN}[i]${NC} $1" | tee -a "$LOG_FILE"
}

print_banner() {
    echo ""
    echo "=============================================="
    echo "  V20.8 焦土收割机 - 最终校准版"
    echo "=============================================="
    echo ""
}

check_prerequisites() {
    log "检查前置条件..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装"
        exit 1
    fi
    log_success "Docker 已安装"

    # 检查 docker-compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose 未安装"
        exit 1
    fi
    log_success "docker-compose 已安装"

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    log_success "Python3 已安装"

    log_success "前置条件检查完成"
}

step_0_backup_database() {
    log ""
    log "步骤 0/4: 数据库备份..."

    # 创建备份目录
    mkdir -p "$BACKUP_DIR"

    # 备份文件名
    BACKUP_FILE="$BACKUP_DIR/match_features_training_$(date +%Y%m%d_%H%M%S).sql"

    log_info "备份目标: match_features_training"
    log_info "备份文件: $BACKUP_FILE"

    # 使用 pg_dump 备份
    if docker-compose exec -T db pg_dump -U football_user football_db -t match_features_training > "$BACKUP_FILE" 2>/dev/null; then
        local backup_size=$(du -h "$BACKUP_FILE" | cut -f1)
        log_success "数据库备份成功 (大小: $backup_size)"
    else
        log_warning "数据库备份失败（可能数据库尚未初始化），继续部署..."
    fi
}

step_1_build_image() {
    log ""
    log "步骤 1/4: 构建 Docker 镜像..."

    if docker-compose build; then
        log_success "Docker 镜像构建成功"
    else
        log_error "Docker 镜像构建失败"
        exit 1
    fi
}

step_2_run_tests() {
    log ""
    log "步骤 2/4: 运行自动化测试..."

    # 运行测试
    if docker-compose run --rm app pytest tests/test_v20_8_atomic.py -v --tb=short; then
        log_success "自动化测试通过"
    else
        log_error "自动化测试失败"
        log_warning "是否继续部署？(y/n)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            log_error "部署已取消"
            exit 1
        fi
    fi
}

step_3_deploy_harvester() {
    log ""
    log "步骤 3/4: 部署 Harvester..."

    # 停止现有容器（如果有）
    log "停止现有容器..."
    docker-compose down -v 2>/dev/null || true

    # 启动服务
    log "启动服务..."
    if docker-compose up -d; then
        log_success "Harvester 已启动"

        # 显示运行状态
        log ""
        log "运行状态:"
        docker-compose ps

        # 显示日志
        log ""
        log "最近日志 (最近 20 行):"
        docker-compose logs --tail=20 harvester 2>/dev/null || docker-compose logs --tail=20 app

    else
        log_error "Harvester 启动失败"
        exit 1
    fi
}

step_4_pulse_check() {
    log ""
    log "步骤 4/4: 数据质量心跳检测..."

    # 等待服务启动
    log_info "等待服务启动..."
    sleep 5

    # 运行心跳检测
    if docker-compose exec -T db psql -U football_user -d football_db -f /app/src/ops/pulse_check.sql 2>/dev/null | tee -a "$LOG_FILE"; then
        log_success "心跳检测完成"
    else
        log_warning "心跳检测失败（可能数据库尚未就绪）"
    fi
}

print_final_report() {
    log ""
    log "=============================================="
    log "  部署完成报告"
    log "=============================================="
    log ""
    log "V20.8 焦土收割机已成功部署！"
    log ""
    log "📋 查看日志:"
    log "  docker-compose logs -f harvester"
    log ""
    log "🔍 进入容器:"
    log "  docker-compose exec harvester bash"
    log ""
    log "🛑 停止服务:"
    log "  docker-compose down"
    log ""
    log "💓 心跳检测:"
    log "  docker-compose exec db psql -U football_user -d football_db -f /app/src/ops/pulse_check.sql"
    log ""
    log "=============================================="
}

# ==================== 主流程 ====================

main() {
    print_banner

    log "部署开始..."
    log "日志文件: $LOG_FILE"

    check_prerequisites
    step_0_backup_database
    step_1_build_image
    step_2_run_tests
    step_3_deploy_harvester
    step_4_pulse_check
    print_final_report

    log_success "部署完成！"
}

# 执行主流程
main "$@"
