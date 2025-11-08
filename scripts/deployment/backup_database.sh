#!/bin/bash

# 数据库备份脚本
# Database Backup Script

set -e

# 配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="football_prediction_backup_$TIMESTAMP.sql"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 加载环境变量
load_env() {
    if [[ -f "$PROJECT_DIR/.env.production" ]]; then
        source "$PROJECT_DIR/.env.production"
    else
        log_error "未找到 .env.production 文件"
        exit 1
    fi
}

# 检查前置条件
check_prerequisites() {
    log_info "检查备份前置条件..."

    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装"
        exit 1
    fi

    # 检查数据库容器是否运行
    if ! docker ps | grep -q football-prediction-db; then
        log_error "数据库容器未运行"
        exit 1
    fi

    # 创建备份目录
    mkdir -p "$BACKUP_DIR"

    log_success "前置条件检查通过"
}

# 执行数据库备份
backup_database() {
    log_info "开始备份数据库..."

    local backup_path="$BACKUP_DIR/$BACKUP_FILE"

    # 执行备份
    if docker exec football-prediction-db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$backup_path"; then
        log_success "数据库备份完成: $backup_path"

        # 压缩备份文件
        gzip "$backup_path"
        log_success "备份文件已压缩: ${backup_path}.gz"

        # 获取备份文件大小
        local file_size=$(du -h "${backup_path}.gz" | cut -f1)
        log_info "备份文件大小: $file_size"

    else
        log_error "数据库备份失败"
        exit 1
    fi
}

# 清理旧备份
cleanup_old_backups() {
    log_info "清理旧备份文件..."

    # 保留最近7天的备份
    find "$BACKUP_DIR" -name "football_prediction_backup_*.sql.gz" -type f -mtime +7 -delete

    # 保留最近4周的周备份
    find "$BACKUP_DIR" -name "weekly_backup_*.sql.gz" -type f -mtime +30 -delete

    log_success "旧备份清理完成"
}

# 创建周备份（每周日执行）
create_weekly_backup() {
    if [[ $(date +%u) -eq 7 ]]; then  # 周日
        local weekly_backup="weekly_backup_$TIMESTAMP.sql"
        local weekly_path="$BACKUP_DIR/$weekly_backup"

        log_info "创建周备份..."

        if docker exec football-prediction-db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" > "$weekly_path"; then
            gzip "$weekly_path"
            log_success "周备份完成: ${weekly_path}.gz"
        fi
    fi
}

# 验证备份文件
verify_backup() {
    local backup_file="$BACKUP_DIR/${BACKUP_FILE}.gz"

    log_info "验证备份文件..."

    # 检查文件是否存在
    if [[ ! -f "$backup_file" ]]; then
        log_error "备份文件不存在: $backup_file"
        return 1
    fi

    # 检查文件大小
    if [[ ! -s "$backup_file" ]]; then
        log_error "备份文件为空: $backup_file"
        return 1
    fi

    # 尝试解压测试（不实际解压到文件）
    if gzip -t "$backup_file" 2>/dev/null; then
        log_success "备份文件验证通过"
        return 0
    else
        log_error "备份文件损坏: $backup_file"
        return 1
    fi
}

# 上传到云存储（可选）
upload_to_cloud() {
    # 这里可以添加云存储上传逻辑
    # 例如 AWS S3, 阿里云OSS等
    log_info "云存储上传功能待实现"
}

# 发送备份通知
send_backup_notification() {
    local status=$1
    local backup_file=$2

    # 这里可以添加邮件、Slack等通知逻辑
    log_info "备份通知: $status - 文件: $backup_file"
}

# 主函数
main() {
    log_info "开始数据库备份..."

    # 解析命令行参数
    SKIP_CLEANUP=false
    WEEKLY_ONLY=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-cleanup)
                SKIP_CLEANUP=true
                shift
                ;;
            --weekly-only)
                WEEKLY_ONLY=true
                shift
                ;;
            *)
                log_error "未知参数: $1"
                exit 1
                ;;
        esac
    done

    # 加载环境变量
    load_env

    # 检查前置条件
    check_prerequisites

    # 执行备份
    if [[ "$WEEKLY_ONLY" != true ]]; then
        backup_database

        # 验证备份
        if verify_backup; then
            send_backup_notification "SUCCESS" "${BACKUP_FILE}.gz"
            upload_to_cloud "${BACKUP_FILE}.gz"
        else
            send_backup_notification "FAILED" "${BACKUP_FILE}.gz"
            exit 1
        fi
    fi

    # 创建周备份
    create_weekly_backup

    # 清理旧备份
    if [[ "$SKIP_CLEANUP" != true ]]; then
        cleanup_old_backups
    fi

    log_success "数据库备份流程完成！"
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi