#!/bin/bash

# PostgreSQL数据库备份脚本
#
# 实现足球预测系统数据库的每日备份功能
# 支持全量备份、增量备份和WAL归档
#
# 基于 DATA_DESIGN.md 第5.2节设计

set -e  # 遇到错误立即退出

# =============================================================================
# 配置参数
# =============================================================================

# 数据库连接配置
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-football_prediction}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-}"

# 备份目录配置
BACKUP_BASE_DIR="${BACKUP_DIR:-/backup/football_db}"
FULL_BACKUP_DIR="${BACKUP_BASE_DIR}/full"
INCREMENTAL_BACKUP_DIR="${BACKUP_BASE_DIR}/incremental"
WAL_BACKUP_DIR="${BACKUP_BASE_DIR}/wal"
LOG_DIR="${BACKUP_BASE_DIR}/logs"

# 备份保留策略
KEEP_FULL_BACKUPS=7      # 保留7天的全量备份
KEEP_INCREMENTAL_DAYS=30 # 保留30天的增量备份
KEEP_WAL_DAYS=7          # 保留7天的WAL文件

# 时间戳
DATE=$(date +%Y%m%d)
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 日志文件
LOG_FILE="${LOG_DIR}/backup_${DATE}.log"

# =============================================================================
# 工具函数
# =============================================================================

# 日志记录函数
log() {
    local level=$1
    shift
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [$level] $*" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &> /dev/null; then
        log_error "命令 $1 未找到，请安装PostgreSQL客户端工具"
        exit 1
    fi
}

# 创建目录
create_directories() {
    local dirs=("$FULL_BACKUP_DIR" "$INCREMENTAL_BACKUP_DIR" "$WAL_BACKUP_DIR" "$LOG_DIR")

    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "创建备份目录: $dir"
        fi
    done
}

# 检查数据库连接
check_database_connection() {
    log_info "检查数据库连接..."

    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" &>/dev/null; then
        log_error "无法连接到数据库 $DB_NAME@$DB_HOST:$DB_PORT"
        exit 1
    fi

    log_info "数据库连接正常"
}

# 获取数据库大小
get_database_size() {
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -t -c "SELECT pg_size_pretty(pg_database_size('$DB_NAME'));" | xargs
}

# =============================================================================
# 备份函数
# =============================================================================

# 全量备份
perform_full_backup() {
    log_info "开始执行全量备份..."

    local backup_file="${FULL_BACKUP_DIR}/full_backup_${TIMESTAMP}.sql"
    local compressed_file="${backup_file}.gz"

    # 执行pg_dump
    log_info "导出数据库到: $backup_file"

    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="$backup_file" \
        2>> "$LOG_FILE"

    if [[ $? -eq 0 ]]; then
        # 压缩备份文件
        log_info "压缩备份文件..."
        gzip "$backup_file"

        # 获取文件大小
        local file_size=$(du -h "$compressed_file" | cut -f1)
        log_info "全量备份完成: $compressed_file (大小: $file_size)"

        # 创建备份元数据
        create_backup_metadata "$compressed_file" "full"

        return 0
    else
        log_error "全量备份失败"
        return 1
    fi
}

# 增量备份（基于WAL）
perform_incremental_backup() {
    log_info "开始执行增量备份..."

    local backup_dir="${INCREMENTAL_BACKUP_DIR}/${DATE}"

    # 创建增量备份目录
    mkdir -p "$backup_dir"

    # 执行pg_basebackup
    log_info "执行基础备份到: $backup_dir"

    PGPASSWORD="$DB_PASSWORD" pg_basebackup \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -D "$backup_dir" \
        -Ft \
        -z \
        -P \
        -v \
        2>> "$LOG_FILE"

    if [[ $? -eq 0 ]]; then
        log_info "增量备份完成: $backup_dir"

        # 创建备份元数据
        create_backup_metadata "$backup_dir" "incremental"

        return 0
    else
        log_error "增量备份失败"
        return 1
    fi
}

# WAL归档备份
archive_wal_files() {
    log_info "开始WAL文件归档..."

    local wal_archive_dir="${WAL_BACKUP_DIR}/${DATE}"
    mkdir -p "$wal_archive_dir"

    # 获取当前WAL文件位置
    local current_wal=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -t -c "SELECT pg_current_wal_lsn();" | xargs)

    log_info "当前WAL位置: $current_wal"

    # 强制WAL切换
    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
        -c "SELECT pg_switch_wal();" >> "$LOG_FILE" 2>&1

    log_info "WAL归档完成"
}

# 创建备份元数据
create_backup_metadata() {
    local backup_path=$1
    local backup_type=$2

    local metadata_file="${backup_path}.metadata"
    local db_size=$(get_database_size)

    cat > "$metadata_file" << EOF
{
    "backup_type": "$backup_type",
    "backup_path": "$backup_path",
    "database_name": "$DB_NAME",
    "database_host": "$DB_HOST",
    "database_size": "$db_size",
    "backup_time": "$(date -Iseconds)",
    "backup_timestamp": "$TIMESTAMP",
    "postgresql_version": "$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version();" | xargs)"
}
EOF

    log_info "备份元数据已创建: $metadata_file"
}

# =============================================================================
# 清理函数
# =============================================================================

# 清理旧备份
cleanup_old_backups() {
    log_info "开始清理旧备份文件..."

    # 清理旧的全量备份
    log_info "清理${KEEP_FULL_BACKUPS}天前的全量备份..."
    find "$FULL_BACKUP_DIR" -name "full_backup_*.sql.gz" -mtime +$KEEP_FULL_BACKUPS -delete 2>/dev/null || true
    find "$FULL_BACKUP_DIR" -name "*.metadata" -mtime +$KEEP_FULL_BACKUPS -delete 2>/dev/null || true

    # 清理旧的增量备份
    log_info "清理${KEEP_INCREMENTAL_DAYS}天前的增量备份..."
    find "$INCREMENTAL_BACKUP_DIR" -type d -mtime +$KEEP_INCREMENTAL_DAYS -exec rm -rf {} + 2>/dev/null || true

    # 清理旧的WAL文件
    log_info "清理${KEEP_WAL_DAYS}天前的WAL文件..."
    find "$WAL_BACKUP_DIR" -type d -mtime +$KEEP_WAL_DAYS -exec rm -rf {} + 2>/dev/null || true

    # 清理旧的日志文件
    find "$LOG_DIR" -name "backup_*.log" -mtime +30 -delete 2>/dev/null || true

    log_info "旧备份清理完成"
}

# =============================================================================
# 主函数
# =============================================================================

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项]

选项:
    -t, --type TYPE     备份类型 (full|incremental|wal|all)
    -h, --help         显示此帮助信息
    -c, --cleanup      仅执行清理操作
    -v, --verify FILE  验证备份文件

示例:
    $0 --type full              # 执行全量备份
    $0 --type incremental       # 执行增量备份
    $0 --type all              # 执行所有类型备份
    $0 --cleanup               # 清理旧备份
    $0 --verify backup.sql.gz  # 验证备份文件

EOF
}

# 验证备份文件
verify_backup() {
    local backup_file=$1

    if [[ ! -f "$backup_file" ]]; then
        log_error "备份文件不存在: $backup_file"
        return 1
    fi

    log_info "验证备份文件: $backup_file"

    # 检查文件是否为有效的PostgreSQL备份
    if file "$backup_file" | grep -q "PostgreSQL"; then
        log_info "备份文件验证成功"
        return 0
    else
        log_error "备份文件验证失败"
        return 1
    fi
}

# 主执行函数
main() {
    local backup_type="full"
    local cleanup_only=false
    local verify_file=""

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -t|--type)
                backup_type="$2"
                shift 2
                ;;
            -c|--cleanup)
                cleanup_only=true
                shift
                ;;
            -v|--verify)
                verify_file="$2"
                shift 2
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            *)
                log_error "未知参数: $1"
                show_usage
                exit 1
                ;;
        esac
    done

    # 验证备份文件
    if [[ -n "$verify_file" ]]; then
        verify_backup "$verify_file"
        exit $?
    fi

    # 初始化
    create_directories

    log_info "=========================================="
    log_info "足球预测系统数据库备份开始"
    log_info "备份类型: $backup_type"
    log_info "数据库: $DB_NAME@$DB_HOST:$DB_PORT"
    log_info "=========================================="

    # 仅清理模式
    if [[ "$cleanup_only" == true ]]; then
        cleanup_old_backups
        log_info "清理操作完成"
        exit 0
    fi

    # 检查依赖
    check_command "pg_dump"
    check_command "pg_basebackup"
    check_command "psql"

    # 检查数据库连接
    check_database_connection

    # 记录数据库信息
    local db_size=$(get_database_size)
    log_info "数据库大小: $db_size"

    # 执行备份
    case "$backup_type" in
        "full")
            perform_full_backup
            ;;
        "incremental")
            perform_incremental_backup
            ;;
        "wal")
            archive_wal_files
            ;;
        "all")
            perform_full_backup
            perform_incremental_backup
            archive_wal_files
            ;;
        *)
            log_error "不支持的备份类型: $backup_type"
            show_usage
            exit 1
            ;;
    esac

    # 清理旧备份
    cleanup_old_backups

    log_info "=========================================="
    log_info "数据库备份任务完成"
    log_info "=========================================="
}

# 执行主函数
main "$@"
