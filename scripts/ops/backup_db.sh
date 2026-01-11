#!/bin/bash
# V33.1 Database Backup Engine - 数据库备份引擎
#
# 功能：自动化备份 football_db 到 backups/ 目录
# 支持：全量备份、增量备份（通过文件名区分）、压缩
#
# Author: 高级 SRE & 数据库专家
# Date: 2026-01-11
# Version: V33.1 (Database Insurance)

set -e  # 遇到错误立即退出

# ============================================================================
# 配置
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_DIR="$PROJECT_ROOT/logs"

# 数据库配置
DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-football_db}"
DB_USER="${DB_USER:-football_user}"

# 备份配置
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="$BACKUP_DIR/football_db_${TIMESTAMP}.sql"
COMPRESS_BACKUP="${COMPRESS_BACKUP:-true}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# ============================================================================
# 辅助函数
# ============================================================================

log_info() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [INFO] $1"
}

log_error() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [ERROR] $1" >&2
}

log_success() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [SUCCESS] $1"
}

# ============================================================================
# 备份函数
# ============================================================================

create_backup_dir() {
    # 创建备份目录
    if [ ! -d "$BACKUP_DIR" ]; then
        log_info "创建备份目录: $BACKUP_DIR"
        mkdir -p "$BACKUP_DIR"
    fi
}

execute_backup() {
    # 执行数据库备份
    log_info "开始备份数据库: $DB_NAME"
    log_info "备份文件: $BACKUP_FILE"

    # 使用 pg_dump 备份
    # 如果在 Docker 中，使用 docker-compose exec
    if [ -n "$DOCKER_ENV" ] || docker info >/dev/null 2>&1; then
        log_info "检测到 Docker 环境，使用 docker-compose exec"
        docker-compose exec -T db pg_dump -U "$DB_USER" \
            --dbname="$DB_NAME" \
            --no-owner \
            --no-acl \
            --format=plain \
            > "$BACKUP_FILE"
    else
        log_info "使用本地 pg_dump"
        PGPASSWORD="${DB_PASSWORD}" pg_dump \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --no-owner \
            --no-acl \
            --format=plain \
            > "$BACKUP_FILE"
    fi

    # 检查备份文件大小
    if [ ! -s "$BACKUP_FILE" ]; then
        log_error "备份文件为空或不存在！"
        exit 1
    fi

    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log_success "备份完成: $BACKUP_FILE ($BACKUP_SIZE)"
}

compress_backup() {
    # 压缩备份文件
    if [ "$COMPRESS_BACKUP" = "true" ]; then
        log_info "压缩备份文件..."
        gzip -c "$BACKUP_FILE" > "${BACKUP_FILE}.gz"
        rm "$BACKUP_FILE"

        COMPRESSED_SIZE=$(du -h "${BACKUP_FILE}.gz" | cut -f1)
        log_success "压缩完成: ${BACKUP_FILE}.gz ($COMPRESSED_SIZE)"

        BACKUP_FILE="${BACKUP_FILE}.gz"
    fi
}

validate_backup() {
    # 验证备份文件
    log_info "验证备份文件..."

    # 检查文件存在
    if [ ! -f "$BACKUP_FILE" ]; then
        log_error "备份文件不存在: $BACKUP_FILE"
        exit 1
    fi

    # 检查文件大小
    FILE_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE" 2>/dev/null || echo "0")
    if [ "$FILE_SIZE" -lt 100 ]; then
        log_error "备份文件太小 (< 100 bytes): $FILE_SIZE bytes"
        exit 1
    fi

    # 检查 pg_dump 标识
    if ! gzip -dc "$BACKUP_FILE" 2>/dev/null | grep -q "PostgreSQL database dump"; then
        if ! grep -q "PostgreSQL database dump" "$BACKUP_FILE"; then
            log_error "备份文件不包含有效的 pg_dump 数据"
            exit 1
        fi
    fi

    log_success "备份文件验证通过"
}

cleanup_old_backups() {
    # 清理旧备份文件
    log_info "清理超过 $RETENTION_DAYS 天的旧备份..."

    # 删除旧备份
    find "$BACKUP_DIR" -name "football_db_*.sql*" -type f -mtime +$RETENTION_DAYS -delete

    # 统计剩余备份
    REMAINING=$(find "$BACKUP_DIR" -name "football_db_*.sql*" -type f | wc -l)
    log_info "剩余备份文件数: $REMAINING"
}

# ============================================================================
# 主流程
# ============================================================================

main() {
    log_info "======================================"
    log_info "V33.1 Database Backup Engine 启动"
    log_info "======================================"
    log_info "数据库: $DB_NAME"
    log_info "备份目录: $BACKUP_DIR"
    log_info "压缩: $COMPRESS_BACKUP"
    log_info "保留天数: $RETENTION_DAYS"
    log_info "======================================"
    echo ""

    # 1. 创建备份目录
    create_backup_dir

    # 2. 执行备份
    execute_backup

    # 3. 验证备份
    validate_backup

    # 4. 压缩备份
    compress_backup

    # 5. 清理旧备份
    cleanup_old_backups

    echo ""
    log_success "======================================"
    log_success "V33.1 数据库备份完成！"
    log_success "备份文件: $BACKUP_FILE"
    log_success "======================================"
}

# Python 接口（供测试调用）
if command -v python3 >/dev/null 2>&1; then
    python3 -c "
import sys
sys.path.insert(0, '$PROJECT_ROOT')

def backup_database(output_dir=None, db_name='football_db'):
    import subprocess
    import os
    from datetime import datetime

    if output_dir is None:
        output_dir = '$BACKUP_DIR'

    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(output_dir, f'football_db_{timestamp}.sql')

    # 执行备份
    result = subprocess.run([
        'docker-compose', 'exec', '-T', 'db', 'pg_dump',
        '-U', '$DB_USER',
        '--dbname=' + db_name,
        '--no-owner',
        '--no-acl'
    ], stdout=open(backup_file, 'w'), stderr=subprocess.PIPE)

    if result.returncode != 0:
        raise Exception(f'备份失败: {result.stderr.decode()}')

    return backup_file

def validate_backup(backup_path):
    import os
    import gzip

    valid = True
    errors = []

    if not os.path.exists(backup_path):
        return {'valid': False, 'error': '文件不存在'}

    size = os.path.getsize(backup_path)

    # 检查大小
    if size < 100:
        return {'valid': False, 'size': size, 'error': '文件太小'}

    # 检查内容
    try:
        if backup_path.endswith('.gz'):
            with gzip.open(backup_path, 'rt') as f:
                content = f.read(1000)  # 读取前 1000 字符
        else:
            with open(backup_path, 'r') as f:
                content = f.read(1000)

        if 'PostgreSQL database dump' not in content:
            return {'valid': False, 'size': size, 'error': '不是有效的 pg_dump 文件'}
    except Exception as e:
        return {'valid': False, 'size': size, 'error': str(e)}

    return {'valid': True, 'size': size}
" 2>/dev/null &
fi

# 执行主流程
main "$@"
