#!/bin/bash

# =============================================================================
# Football Prediction 备份脚本
# =============================================================================

set -euo pipefail

# 配置
DB_HOST="${DB_HOST:-postgres-prod}"
DB_NAME="${DB_NAME:-football_prod}"
DB_USER="${DB_USER:-postgres}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-7}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 创建备份目录
mkdir -p "$BACKUP_DIR"

# 生成备份文件名
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')
BACKUP_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.sql"

# 执行备份
log_info "开始备份数据库 $DB_NAME..."

# 使用 pg_dump 进行备份
if ! PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$DB_HOST" \
    -U "$DB_USER" \
    -d "$DB_NAME" \
    -F custom \
    -f "$BACKUP_FILE"; then
    log_error "数据库备份失败"
    exit 1
fi

# 压缩备份文件
log_info "压缩备份文件..."
gzip "$BACKUP_FILE"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

# 计算文件大小
BACKUP_SIZE=$(du -h "$BACKUP_FILE_GZ" | cut -f1)
log_info "备份完成: $BACKUP_FILE_GZ ($BACKUP_SIZE)"

# 清理旧备份
log_info "清理 $RETENTION_DAYS 天前的备份..."
find "$BACKUP_DIR" -name "backup_*.sql.gz" -mtime +$RETENTION_DAYS -delete

# 验证备份
log_info "验证备份文件..."
if gzip -t "$BACKUP_FILE_GZ"; then
    log_info "备份验证成功"
else
    log_error "备份验证失败"
    exit 1
fi

# 上传到云存储（如果配置了）
if [ -n "${AWS_ACCESS_KEY_ID:-}" ] && [ -n "${AWS_S3_BUCKET:-}" ]; then
    log_info "上传备份到 S3..."
    aws s3 cp "$BACKUP_FILE_GZ" "s3://${AWS_S3_BUCKET}/database-backups/"
    log_info "S3 上传完成"
fi

# 发送通知（如果配置了）
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    log_info "发送备份完成通知..."
    curl -X POST -H 'Content-type: application/json' \
        --data "{\"text\":\"✅ 数据库备份完成\\n文件: ${BACKUP_FILE_GZ}\\n大小: ${BACKUP_SIZE}\"}" \
        "$SLACK_WEBHOOK_URL"
fi

log_info "备份任务完成"