#!/bin/bash
# FootballPrediction 快速回滚脚本
# 用于紧急情况下快速回滚到上一版本

set -euo pipefail

# 配置
BACKUP_DIR="/backups/football-prediction"
DEPLOYMENT_DIR="/opt/football-prediction"
HEALTH_CHECK_URL="http://localhost:8000/health"
LOG_FILE="/var/log/football-prediction-rollback.log"
COMPOSE_FILE="docker-compose.yml"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

# 记录到日志文件
write_log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 检查是否为root用户
check_permissions() {
    if [[ $EUID -eq 0 ]]; then
        error "请不要以root用户运行此脚本"
        exit 1
    fi
}

# 确认回滚操作
confirm_rollback() {
    echo
    warn "警告：即将执行系统回滚操作！"
    warn "这将导致当前版本被替换为上一版本。"
    echo
    read -p "确认执行回滚？(yes/no): " -r
    if [[ ! $REPLY =~ ^yes$ ]]; then
        log "回滚操作已取消"
        exit 0
    fi
}

# 获取当前版本
get_current_version() {
    if [[ -f "$DEPLOYMENT_DIR/VERSION" ]]; then
        cat "$DEPLOYMENT_DIR/VERSION"
    else
        echo "unknown"
    fi
}

# 获取备份版本列表
list_backups() {
    log "可用的备份版本："
    ls -1 "$BACKUP_DIR" | grep -E "backup-[0-9]{8}-[0-9]{6}" | sort -r | head -5
    echo
}

# 健康检查
health_check() {
    local retries=30
    local wait=5

    log "执行健康检查..."

    for ((i=1; i<=retries; i++)); do
        if curl -sf "$HEALTH_CHECK_URL" >/dev/null 2>&1; then
            log "✓ 服务健康检查通过 (尝试 $i/$retries)"
            return 0
        fi

        if [[ $i -eq $retries ]]; then
            error "✗ 健康检查失败，服务可能未正常启动"
            return 1
        fi

        log "等待服务启动... ($i/$retries)"
        sleep $wait
    done
}

# 停止当前服务
stop_services() {
    log "停止当前服务..."

    cd "$DEPLOYMENT_DIR"

    # 使用docker-compose停止服务
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose down
        log "✓ Docker服务已停止"
    else
        # 直接停止进程
        pkill -f "uvicorn.*main:app" || true
        log "✓ 应用进程已停止"
    fi
}

# 回滚数据库
rollback_database() {
    local backup_file="$1"

    if [[ -n "$backup_file" && -f "$backup_file" ]]; then
        log "回滚数据库..."

        # 获取数据库连接信息
        source .env 2>/dev/null || true

        # 恢复数据库
        if command -v pg_restore >/dev/null 2>&1; then
            pg_restore -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" --clean --if-exists "$backup_file"
            log "✓ 数据库回滚完成"
        else
            warn "pg_restore未找到，跳过数据库回滚"
        fi
    else
        log "跳过数据库回滚（未指定备份文件）"
    fi
}

# 回滚应用
rollback_application() {
    local backup_dir="$1"

    log "回滚应用代码..."

    # 备份当前版本
    if [[ -d "$DEPLOYMENT_DIR" ]]; then
        cp -r "$DEPLOYMENT_DIR" "$BACKUP_DIR/rollback-backup-$(date +%Y%m%d_%H%M%S)"
    fi

    # 恢复备份版本
    if [[ -d "$backup_dir" ]]; then
        rm -rf "$DEPLOYMENT_DIR"
        cp -r "$backup_dir" "$DEPLOYMENT_DIR"

        # 更新版本文件
        if [[ -f "$backup_dir/VERSION" ]]; then
            cp "$backup_dir/VERSION" "$DEPLOYMENT_DIR/VERSION"
        fi

        log "✓ 应用代码回滚完成"
    else
        error "备份目录不存在: $backup_dir"
        return 1
    fi
}

# 重启服务
start_services() {
    log "启动服务..."

    cd "$DEPLOYMENT_DIR"

    # 使用docker-compose启动
    if [[ -f "$COMPOSE_FILE" ]]; then
        docker-compose up -d
        log "✓ Docker服务已启动"
    else
        # 直接启动应用
        source .env 2>/dev/null || true
        nohup uvicorn src.main:app --host 0.0.0.0 --port 8000 > app.log 2>&1 &
        log "✓ 应用进程已启动"
    fi
}

# 验证回滚
verify_rollback() {
    local current_version=$(get_current_version)

    log "验证回滚结果..."
    log "当前版本: $current_version"

    # 执行健康检查
    if health_check; then
        log "✓ 服务运行正常"

        # 执行烟雾测试
        log "执行烟雾测试..."
        if curl -sf "$HEALTH_CHECK_URL/api/v1/status" >/dev/null 2>&1; then
            log "✓ 烟雾测试通过"
            return 0
        else
            warn "⚠ 烟雾测试未完全通过，请检查API功能"
        fi
    else
        error "✗ 健康检查失败，回滚可能存在问题"
        return 1
    fi

    return 0
}

# 发送通知
send_notification() {
    local status="$1"
    local version=$(get_current_version)
    local message="FootballPrediction 系统回滚已完成\n状态: $status\n版本: $version\n时间: $(date)"

    # 发送Slack通知（如果配置了webhook）
    if [[ -n "${SLACK_WEBHOOK:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"$message\"}" \
            "$SLACK_WEBHOOK" || true
    fi

    # 发送邮件通知（如果配置了）
    if command -v mail >/dev/null 2>&1 && [[ -n "${NOTIFICATION_EMAIL:-}" ]]; then
        echo -e "$message" | mail -s "FootballPrediction 回滚通知" "$NOTIFICATION_EMAIL" || true
    fi

    log "通知已发送"
}

# 主函数
main() {
    local backup_version=""
    local database_backup=""

    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            --version)
                backup_version="$2"
                shift 2
                ;;
            --db-backup)
                database_backup="$2"
                shift 2
                ;;
            --help)
                echo "用法: $0 [--version VERSION] [--db-backup DATABASE_BACKUP]"
                echo
                echo "选项:"
                echo "  --version VERSION     回滚到指定版本备份"
                echo "  --db-backup FILE       恢复指定的数据库备份"
                echo "  --help                 显示此帮助信息"
                echo
                exit 0
                ;;
            *)
                error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    log "开始执行回滚流程..."
    write_log "=== 开始回滚 ==="

    # 检查权限
    check_permissions

    # 如果未指定版本，使用最新备份
    if [[ -z "$backup_version" ]]; then
        backup_version=$(ls -1 "$BACKUP_DIR" | grep -E "backup-[0-9]{8}-[0-9]{6}" | sort -r | head -1)
        if [[ -z "$backup_version" ]]; then
            error "未找到可用的备份版本"
            exit 1
        fi
    fi

    local backup_path="$BACKUP_DIR/$backup_version"

    # 显示信息
    log "当前版本: $(get_current_version)"
    log "目标版本: $backup_version"
    log "备份路径: $backup_path"

    # 列出可用备份
    list_backups

    # 确认回滚
    confirm_rollback

    # 执行回滚步骤
    write_log "停止服务"
    stop_services

    write_log "回滚应用"
    rollback_application "$backup_path"

    write_log "回滚数据库"
    rollback_database "$database_backup"

    write_log "启动服务"
    start_services

    # 验证回滚
    if verify_rollback; then
        write_log "回滚成功"
        log "✅ 系统回滚成功完成！"
        send_notification "成功"

        # 生成回滚报告
        echo "回滚完成时间: $(date)" > "$DEPLOYMENT_DIR/ROLLBACK_INFO"
        echo "回滚到版本: $backup_version" >> "$DEPLOYMENT_DIR/ROLLBACK_INFO"

        exit 0
    else
        write_log "回滚失败"
        error "❌ 系统回滚失败，请检查日志"
        send_notification "失败"
        exit 1
    fi
}

# 执行主函数
main "$@"
