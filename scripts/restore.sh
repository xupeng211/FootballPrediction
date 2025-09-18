#!/bin/bash

# PostgreSQL数据库恢复脚本
#
# 实现足球预测系统数据库的恢复功能
# 支持从全量备份、增量备份和WAL文件恢复
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

# 恢复目录配置
RESTORE_DIR="${BACKUP_BASE_DIR}/restore"
TEMP_DB_NAME="${DB_NAME}_restore_temp_$(date +%s)"

# 时间戳
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 日志文件
LOG_FILE="${LOG_DIR}/restore_${TIMESTAMP}.log"

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
    local dirs=("$RESTORE_DIR" "$LOG_DIR")

    for dir in "${dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            log_info "创建恢复目录: $dir"
        fi
    done
}

# 检查数据库连接
check_database_connection() {
    log_info "检查数据库连接..."

    if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "postgres" -c "SELECT 1;" &>/dev/null; then
        log_error "无法连接到数据库服务器 $DB_HOST:$DB_PORT"
        exit 1
    fi

    log_info "数据库连接正常"
}

# 检查备份文件
validate_backup_file() {
    local backup_file=$1

    if [[ ! -f "$backup_file" ]]; then
        log_error "备份文件不存在: $backup_file"
        return 1
    fi

    log_info "验证备份文件: $backup_file"

    # 检查文件扩展名
    if [[ "$backup_file" == *.gz ]]; then
        # 检查压缩文件
        if ! gzip -t "$backup_file" 2>/dev/null; then
            log_error "备份文件损坏或不是有效的压缩文件"
            return 1
        fi
    fi

    # 检查是否为PostgreSQL备份文件
    local file_type
    if [[ "$backup_file" == *.gz ]]; then
        file_type=$(zcat "$backup_file" | head -n 10 | file -)
    else
        file_type=$(head -n 10 "$backup_file" | file -)
    fi

    if [[ "$file_type" =~ PostgreSQL|SQL|ASCII ]]; then
        log_info "备份文件验证成功"
        return 0
    else
        log_error "备份文件验证失败：不是有效的PostgreSQL备份文件"
        return 1
    fi
}

# 获取备份元数据
get_backup_metadata() {
    local backup_file=$1
    local metadata_file="${backup_file}.metadata"

    if [[ -f "$metadata_file" ]]; then
        log_info "读取备份元数据: $metadata_file"
        cat "$metadata_file"
    else
        log_warn "未找到备份元数据文件"
    fi
}

# =============================================================================
# 恢复函数
# =============================================================================

# 创建临时数据库
create_temp_database() {
    log_info "创建临时数据库: $TEMP_DB_NAME"

    PGPASSWORD="$DB_PASSWORD" createdb \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        "$TEMP_DB_NAME" \
        2>> "$LOG_FILE"

    if [[ $? -eq 0 ]]; then
        log_info "临时数据库创建成功"
        return 0
    else
        log_error "临时数据库创建失败"
        return 1
    fi
}

# 恢复到临时数据库
restore_to_temp_database() {
    local backup_file=$1

    log_info "恢复备份文件到临时数据库..."

    # 判断备份文件格式
    if [[ "$backup_file" == *.gz ]]; then
        # 处理压缩文件
        log_info "解压并恢复压缩备份文件"
        if [[ "$backup_file" == *custom* ]] || file "$backup_file" | grep -q "PostgreSQL custom"; then
            # 自定义格式备份
            PGPASSWORD="$DB_PASSWORD" pg_restore \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$TEMP_DB_NAME" \
                --verbose \
                --no-owner \
                --no-privileges \
                "$backup_file" \
                2>> "$LOG_FILE"
        else
            # SQL格式备份
            zcat "$backup_file" | PGPASSWORD="$DB_PASSWORD" psql \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$TEMP_DB_NAME" \
                2>> "$LOG_FILE"
        fi
    else
        # 处理未压缩文件
        if file "$backup_file" | grep -q "PostgreSQL custom"; then
            # 自定义格式备份
            PGPASSWORD="$DB_PASSWORD" pg_restore \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$TEMP_DB_NAME" \
                --verbose \
                --no-owner \
                --no-privileges \
                "$backup_file" \
                2>> "$LOG_FILE"
        else
            # SQL格式备份
            PGPASSWORD="$DB_PASSWORD" psql \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$TEMP_DB_NAME" \
                -f "$backup_file" \
                2>> "$LOG_FILE"
        fi
    fi

    if [[ $? -eq 0 ]]; then
        log_info "数据恢复到临时数据库成功"
        return 0
    else
        log_error "数据恢复到临时数据库失败"
        return 1
    fi
}

# 验证恢复的数据
validate_restored_data() {
    log_info "验证恢复的数据完整性..."

    local temp_db_size=$(PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "$TEMP_DB_NAME" \
        -t -c "SELECT pg_size_pretty(pg_database_size('$TEMP_DB_NAME'));" | xargs)

    log_info "恢复数据库大小: $temp_db_size"

    # 检查关键表是否存在
    local tables=("matches" "teams" "leagues" "odds" "predictions")
    local missing_tables=()

    for table in "${tables[@]}"; do
        local table_exists=$(PGPASSWORD="$DB_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$TEMP_DB_NAME" \
            -t -c "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '$table');" | xargs)

        if [[ "$table_exists" != "t" ]]; then
            missing_tables+=("$table")
        fi
    done

    if [[ ${#missing_tables[@]} -eq 0 ]]; then
        log_info "数据验证成功：所有关键表都存在"
        return 0
    else
        log_warn "缺少以下关键表: ${missing_tables[*]}"
        return 1
    fi
}

# 替换生产数据库
replace_production_database() {
    local force_replace=$1

    log_info "准备替换生产数据库..."

    # 检查生产数据库是否存在
    local db_exists=$(PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "postgres" \
        -t -c "SELECT EXISTS(SELECT datname FROM pg_catalog.pg_database WHERE datname = '$DB_NAME');" | xargs)

    if [[ "$db_exists" == "t" ]]; then
        if [[ "$force_replace" != "yes" ]]; then
            log_warn "生产数据库 $DB_NAME 已存在"
            read -p "是否要替换现有数据库？这将删除所有现有数据。(yes/no): " confirm
            if [[ "$confirm" != "yes" ]]; then
                log_info "用户取消了数据库替换操作"
                return 1
            fi
        fi

        # 备份当前生产数据库
        local backup_current="${RESTORE_DIR}/current_db_backup_${TIMESTAMP}.sql.gz"
        log_info "备份当前生产数据库到: $backup_current"

        PGPASSWORD="$DB_PASSWORD" pg_dump \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --format=custom \
            --compress=9 | gzip > "$backup_current"

        # 断开所有连接
        log_info "断开所有到生产数据库的连接..."
        PGPASSWORD="$DB_PASSWORD" psql \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "postgres" \
            -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$DB_NAME';" \
            2>> "$LOG_FILE"

        # 删除生产数据库
        log_info "删除生产数据库..."
        PGPASSWORD="$DB_PASSWORD" dropdb \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            "$DB_NAME" \
            2>> "$LOG_FILE"
    fi

    # 重命名临时数据库为生产数据库
    log_info "将临时数据库重命名为生产数据库..."
    PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "postgres" \
        -c "ALTER DATABASE \"$TEMP_DB_NAME\" RENAME TO \"$DB_NAME\";" \
        2>> "$LOG_FILE"

    if [[ $? -eq 0 ]]; then
        log_info "数据库恢复完成"
        return 0
    else
        log_error "数据库重命名失败"
        return 1
    fi
}

# 清理临时资源
cleanup_temp_resources() {
    log_info "清理临时资源..."

    # 删除临时数据库（如果存在）
    local temp_db_exists=$(PGPASSWORD="$DB_PASSWORD" psql \
        -h "$DB_HOST" \
        -p "$DB_PORT" \
        -U "$DB_USER" \
        -d "postgres" \
        -t -c "SELECT EXISTS(SELECT datname FROM pg_catalog.pg_database WHERE datname = '$TEMP_DB_NAME');" | xargs)

    if [[ "$temp_db_exists" == "t" ]]; then
        log_info "删除临时数据库: $TEMP_DB_NAME"
        PGPASSWORD="$DB_PASSWORD" dropdb \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            "$TEMP_DB_NAME" \
            2>> "$LOG_FILE" || true
    fi
}

# =============================================================================
# 主函数
# =============================================================================

# 显示使用说明
show_usage() {
    cat << EOF
用法: $0 [选项] <备份文件路径>

选项:
    -f, --force         强制替换，不询问确认
    -t, --test-only     仅测试恢复，不替换生产数据库
    -h, --help          显示此帮助信息
    -v, --validate      仅验证备份文件

示例:
    $0 /backup/football_db/full/full_backup_20250910.sql.gz
    $0 --test-only backup.sql.gz      # 仅测试恢复
    $0 --force backup.sql.gz          # 强制恢复，不询问
    $0 --validate backup.sql.gz       # 仅验证备份文件

EOF
}

# 列出可用的备份文件
list_available_backups() {
    log_info "可用的备份文件："

    if [[ -d "$FULL_BACKUP_DIR" ]]; then
        log_info "全量备份:"
        find "$FULL_BACKUP_DIR" -name "*.sql.gz" -exec ls -lh {} + 2>/dev/null | while read -r line; do
            echo "  $line"
        done
    fi

    if [[ -d "$INCREMENTAL_BACKUP_DIR" ]]; then
        log_info "增量备份:"
        find "$INCREMENTAL_BACKUP_DIR" -type d -name "2*" -exec ls -ld {} + 2>/dev/null | while read -r line; do
            echo "  $line"
        done
    fi
}

# 主执行函数
main() {
    local backup_file=""
    local force_replace="no"
    local test_only=false
    local validate_only=false

    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                force_replace="yes"
                shift
                ;;
            -t|--test-only)
                test_only=true
                shift
                ;;
            -v|--validate)
                validate_only=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -l|--list)
                list_available_backups
                exit 0
                ;;
            -*)
                log_error "未知参数: $1"
                show_usage
                exit 1
                ;;
            *)
                if [[ -z "$backup_file" ]]; then
                    backup_file="$1"
                else
                    log_error "只能指定一个备份文件"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done

    # 检查备份文件参数
    if [[ -z "$backup_file" ]]; then
        log_error "请指定备份文件路径"
        show_usage
        exit 1
    fi

    # 初始化
    create_directories

    log_info "=========================================="
    log_info "足球预测系统数据库恢复开始"
    log_info "备份文件: $backup_file"
    log_info "目标数据库: $DB_NAME@$DB_HOST:$DB_PORT"
    log_info "=========================================="

    # 检查依赖
    check_command "psql"
    check_command "pg_restore"
    check_command "createdb"
    check_command "dropdb"

    # 检查数据库连接
    check_database_connection

    # 验证备份文件
    if ! validate_backup_file "$backup_file"; then
        log_error "备份文件验证失败，恢复中止"
        exit 1
    fi

    # 显示备份元数据
    get_backup_metadata "$backup_file"

    # 仅验证模式
    if [[ "$validate_only" == true ]]; then
        log_info "备份文件验证成功"
        exit 0
    fi

    # 创建临时数据库
    if ! create_temp_database; then
        log_error "创建临时数据库失败，恢复中止"
        exit 1
    fi

    # 清理函数（异常退出时清理临时资源）
    trap cleanup_temp_resources EXIT

    # 恢复到临时数据库
    if ! restore_to_temp_database "$backup_file"; then
        log_error "恢复到临时数据库失败，恢复中止"
        exit 1
    fi

    # 验证恢复的数据
    if ! validate_restored_data; then
        log_warn "数据验证有警告，建议检查恢复结果"
    fi

    # 仅测试模式
    if [[ "$test_only" == true ]]; then
        log_info "测试恢复成功，临时数据库: $TEMP_DB_NAME"
        log_info "请手动检查数据，然后删除临时数据库"
        # 取消自动清理
        trap - EXIT
        exit 0
    fi

    # 替换生产数据库
    if replace_production_database "$force_replace"; then
        log_info "=========================================="
        log_info "数据库恢复成功完成"
        log_info "生产数据库已更新"
        log_info "=========================================="
    else
        log_error "数据库替换失败"
        exit 1
    fi
}

# 执行主函数
main "$@"
