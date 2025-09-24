#!/bin/bash
# 数据库备份脚本 - FootballPrediction
# 作者: DevOps Team
# 描述: PostgreSQL 数据库自动备份和恢复

set -euo pipefail

# =============================================================================
# 配置参数
# =============================================================================

# 数据库连接配置
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-football_prediction}"
DB_USER="${DB_USER:-football_user}"
DB_PASSWORD="${DB_PASSWORD:-}"

# 备份配置
BACKUP_DIR="${BACKUP_DIR:-/backups/database}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"
BACKUP_PREFIX="football_prediction"

# S3 配置（可选）
S3_BUCKET="${S3_BUCKET:-}"
S3_PATH="${S3_PATH:-database-backups}"

# 日志配置
LOG_FILE="${LOG_FILE:-/var/log/db_backup.log}"

# =============================================================================
# 工具函数
# =============================================================================

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

error() {
    log "ERROR: $1" >&2
    exit 1
}

check_dependencies() {
    log "检查依赖..."

    command -v pg_dump >/dev/null 2>&1 || error "pg_dump not found"
    command -v psql >/dev/null 2>&1 || error "psql not found"

    if [[ -n "$S3_BUCKET" ]]; then
        command -v aws >/dev/null 2>&1 || error "aws cli not found"
    fi

    log "依赖检查完成"
}

test_connection() {
    log "测试数据库连接..."

    PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" >/dev/null 2>&1 || error "Database connection failed"

    log "数据库连接正常"
}

# =============================================================================
# 备份功能
# =============================================================================

create_backup() {
    local timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_file="${BACKUP_DIR}/${BACKUP_PREFIX}_${timestamp}.sql"
    local backup_file_gz="${backup_file}.gz"

    log "开始创建备份: $backup_file_gz"

    # 创建备份目录
    mkdir -p "$BACKUP_DIR"

    # 执行备份
    PGPASSWORD="$DB_PASSWORD" pg_dump \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$DB_NAME" \
        --verbose \
        --no-password \
        --format=custom \
        --compress=9 \
        --file="$backup_file" || error "Backup failed"

    # 压缩备份文件
    gzip "$backup_file" || error "Compression failed"

    # 验证备份文件
    if [[ ! -f "$backup_file_gz" ]]; then
        error "Backup file not created: $backup_file_gz"
    fi

    local file_size=$(du -h "$backup_file_gz" | cut -f1)
    log "备份完成: $backup_file_gz (大小: $file_size)"

    # 上传到S3（如果配置）
    if [[ -n "$S3_BUCKET" ]]; then
        upload_to_s3 "$backup_file_gz"
    fi

    echo "$backup_file_gz"
}

upload_to_s3() {
    local backup_file="$1"
    local s3_key="${S3_PATH}/$(basename "$backup_file")"

    log "上传备份到S3: s3://${S3_BUCKET}/${s3_key}"

    aws s3 cp "$backup_file" "s3://${S3_BUCKET}/${s3_key}" || error "S3 upload failed"

    log "S3上传完成"
}

# =============================================================================
# 清理功能
# =============================================================================

cleanup_old_backups() {
    log "清理 $RETENTION_DAYS 天前的备份..."

    find "$BACKUP_DIR" -name "${BACKUP_PREFIX}_*.sql.gz" -mtime +$RETENTION_DAYS -type f -delete

    if [[ -n "$S3_BUCKET" ]]; then
        local cutoff_date=$(date -d "${RETENTION_DAYS} days ago" '+%Y-%m-%d')
        log "清理S3中 $cutoff_date 之前的备份..."

        aws s3 ls "s3://${S3_BUCKET}/${S3_PATH}/" | while read -r line; do
            local file_date=$(echo "$line" | awk '{print $1}')
            local file_name=$(echo "$line" | awk '{print $4}')

            if [[ "$file_date" < "$cutoff_date" && "$file_name" == "${BACKUP_PREFIX}_"* ]]; then
                aws s3 rm "s3://${S3_BUCKET}/${S3_PATH}/${file_name}"
                log "已删除S3文件: $file_name"
            fi
        done
    fi

    log "清理完成"
}

# =============================================================================
# 恢复功能
# =============================================================================

restore_backup() {
    local backup_file="$1"
    local target_db="${2:-${DB_NAME}_restored}"

    log "开始恢复备份: $backup_file 到 $target_db"

    # 检查备份文件
    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
    fi

    # 解压备份文件（如果需要）
    local restore_file="$backup_file"
    if [[ "$backup_file" == *.gz ]]; then
        restore_file="${backup_file%.gz}"
        gunzip -c "$backup_file" > "$restore_file" || error "Decompression failed"
    fi

    # 创建目标数据库
    PGPASSWORD="$DB_PASSWORD" createdb \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        "$target_db" || log "Database $target_db may already exist"

    # 恢复数据
    PGPASSWORD="$DB_PASSWORD" pg_restore \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$target_db" \
        --verbose \
        --no-password \
        --clean \
        --if-exists \
        "$restore_file" || error "Restore failed"

    # 清理临时文件
    if [[ "$backup_file" == *.gz && -f "$restore_file" ]]; then
        rm "$restore_file"
    fi

    log "恢复完成: $target_db"
}

# =============================================================================
# 验证功能
# =============================================================================

verify_backup() {
    local backup_file="$1"
    local temp_db="verify_$(date '+%s')"

    log "验证备份文件: $backup_file"

    # 尝试恢复到临时数据库
    restore_backup "$backup_file" "$temp_db"

    # 执行基本查询验证
    local table_count=$(PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$temp_db" -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")

    if [[ $table_count -eq 0 ]]; then
        error "Backup verification failed: no tables found"
    fi

    # 清理临时数据库
    PGPASSWORD="$DB_PASSWORD" dropdb \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        "$temp_db"

    log "备份验证成功: 找到 $table_count 个表"
}

# =============================================================================
# 主函数
# =============================================================================

usage() {
    cat << EOF
用法: $0 [选项] [命令]

命令:
    backup              创建数据库备份
    restore <file>      恢复指定备份文件
    verify <file>       验证备份文件完整性
    cleanup             清理过期备份文件
    list                列出可用备份文件

选项:
    -h, --help          显示帮助信息
    -v, --verbose       详细输出
    --dry-run           模拟运行（不执行实际操作）

环境变量:
    DB_HOST             数据库主机 (默认: localhost)
    DB_PORT             数据库端口 (默认: 5432)
    DB_NAME             数据库名称 (默认: football_prediction)
    DB_USER             数据库用户 (默认: football_user)
    DB_PASSWORD         数据库密码
    BACKUP_DIR          备份目录 (默认: /backups/database)
    RETENTION_DAYS      备份保留天数 (默认: 7)
    S3_BUCKET           S3存储桶名称 (可选)
    S3_PATH             S3存储路径 (默认: database-backups)

示例:
    # 创建备份
    $0 backup

    # 恢复到新数据库
    $0 restore /backups/database/football_prediction_20231201_120000.sql.gz

    # 验证备份
    $0 verify /backups/database/football_prediction_20231201_120000.sql.gz

    # 清理过期备份
    $0 cleanup

    # 定时备份 (crontab)
    0 2 * * * /usr/local/bin/db_backup.sh backup
EOF
}

list_backups() {
    log "本地备份文件:"
    if [[ -d "$BACKUP_DIR" ]]; then
        ls -lah "$BACKUP_DIR"/${BACKUP_PREFIX}_*.sql.gz 2>/dev/null || log "未找到本地备份文件"
    else
        log "备份目录不存在: $BACKUP_DIR"
    fi

    if [[ -n "$S3_BUCKET" ]]; then
        log "S3备份文件:"
        aws s3 ls "s3://${S3_BUCKET}/${S3_PATH}/" | grep "${BACKUP_PREFIX}_" || log "未找到S3备份文件"
    fi
}

main() {
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            --dry-run)
                DRY_RUN=1
                shift
                ;;
            backup)
                COMMAND="backup"
                shift
                ;;
            restore)
                COMMAND="restore"
                BACKUP_FILE="$2"
                shift 2
                ;;
            verify)
                COMMAND="verify"
                BACKUP_FILE="$2"
                shift 2
                ;;
            cleanup)
                COMMAND="cleanup"
                shift
                ;;
            list)
                COMMAND="list"
                shift
                ;;
            *)
                error "未知参数: $1"
                ;;
        esac
    done

    # 检查必需参数
    if [[ -z "${COMMAND:-}" ]]; then
        usage
        error "请指定命令"
    fi

    # 初始化
    check_dependencies

    if [[ "$COMMAND" != "list" ]]; then
        test_connection
    fi

    # 执行命令
    case "$COMMAND" in
        backup)
            backup_file=$(create_backup)
            verify_backup "$backup_file"
            cleanup_old_backups
            ;;
        restore)
            if [[ -z "${BACKUP_FILE:-}" ]]; then
                error "请指定备份文件"
            fi
            restore_backup "$BACKUP_FILE"
            ;;
        verify)
            if [[ -z "${BACKUP_FILE:-}" ]]; then
                error "请指定备份文件"
            fi
            verify_backup "$BACKUP_FILE"
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        list)
            list_backups
            ;;
    esac

    log "操作完成"
}

# 执行主函数
main "$@"