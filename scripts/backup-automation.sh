#!/bin/bash

# 数据库备份自动化脚本
# Football Prediction Project

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# 配置
BACKUP_DIR="backups/database"
CONFIG_DIR="config/backup"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-30}
S3_BUCKET=${BACKUP_S3_BUCKET:-}
DB_NAME=${DB_NAME:-football_prediction}

# 创建必要的目录
create_directories() {
    log_step "创建备份目录..."
    mkdir -p "$BACKUP_DIR"/{full,incremental,wal}
    mkdir -p "$CONFIG_DIR"
    mkdir -p logs/backup
}

# 创建备份配置文件
create_backup_config() {
    log_step "创建备份配置..."

    # PostgreSQL配置文件
    cat > "$CONFIG_DIR/.pgpass" <<EOF
localhost:5432:$DB_NAME:$DB_USER:$DB_PASSWORD
EOF
    chmod 600 "$CONFIG_DIR/.pgpass"

    # pg_hba.conf配置（允许备份）
    cat > "$CONFIG_DIR/pg_hba_backup.conf" <<EOF
# 备份用户访问配置
local   $DB_NAME   backup_user                               md5
host    $DB_NAME   backup_user   127.0.0.1/32                md5
host    $DB_NAME   backup_user   ::1/128                     md5
EOF

    # 归档配置
    cat > "$CONFIG_DIR/archive_command.sh" <<'EOF'
#!/bin/bash
# WAL归档命令

WAL_FILE=$1
ARCHIVE_DIR="/var/lib/postgresql/wal_archive"

# 创建归档目录
mkdir -p "$ARCHIVE_DIR"

# 压缩并归档WAL文件
gzip < "$WAL_FILE" > "$ARCHIVE_DIR/$(basename $WAL_FILE).gz"

# 如果配置了S3，也上传到S3
if [[ -n "${BACKUP_S3_BUCKET:-}" ]]; then
    aws s3 cp "$ARCHIVE_DIR/$(basename $WAL_FILE).gz" \
        "s3://$BACKUP_S3_BUCKET/postgresql-wal/$(basename $WAL_FILE).gz"
fi
EOF
    chmod +x "$CONFIG_DIR/archive_command.sh"

    # 备份脚本配置
    cat > "$CONFIG_DIR/backup_config.env" <<EOF
# 数据库备份配置
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="$DB_NAME"
export DB_USER="${DB_USER:-postgres}"
export DB_PASSWORD="${DB_PASSWORD:-}"

# 备份配置
export BACKUP_RETENTION_DAYS=$RETENTION_DAYS
export BACKUP_COMPRESS=${BACKUP_COMPRESS:-true}
export BACKUP_ENCRYPT=${BACKUP_ENCRYPT:-true}
export BACKUP_ENCRYPTION_KEY="${BACKUP_ENCRYPTION_KEY:-}"

# S3配置
export BACKUP_S3_BUCKET="$S3_BUCKET"
export AWS_REGION="${AWS_REGION:-us-east-1}"
export AWS_ACCESS_KEY_ID="${AWS_ACCESS_KEY_ID:-}"
export AWS_SECRET_ACCESS_KEY="${AWS_SECRET_ACCESS_KEY:-}"

# 通知配置
export BACKUP_NOTIFY_EMAIL="${BACKUP_NOTIFY_EMAIL:-}"
export BACKUP_NOTIFY_SLACK_WEBHOOK="${BACKUP_NOTIFY_SLACK_WEBHOOK:-}"
EOF

    log_info "备份配置已创建"
}

# 创建备份用户
create_backup_user() {
    log_step "创建备份用户..."

    psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" <<EOF || true
-- 创建备份用户
DO \$\$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'backup_user') THEN
        CREATE ROLE backup_user WITH LOGIN PASSWORD 'backup_user_123456';
    END IF;
END
\$\$;

-- 授予必要的权限
GRANT CONNECT ON DATABASE $DB_NAME TO backup_user;
GRANT USAGE ON SCHEMA public TO backup_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO backup_user;

-- 确保未来的表也有权限
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO backup_user;
EOF

    if [[ $? -eq 0 ]]; then
        log_info "备份用户创建成功"
    else
        log_warn "备份用户可能已存在或创建失败"
    fi
}

# 配置PostgreSQL WAL归档
configure_wal_archiving() {
    log_step "配置WAL归档..."

    # 创建WAL归档目录
    sudo mkdir -p /var/lib/postgresql/wal_archive
    sudo chown postgres:postgres /var/lib/postgresql/wal_archive
    sudo chmod 700 /var/lib/postgresql/wal_archive

    # 更新postgresql.conf
    sudo cp /etc/postgresql/*/main/postgresql.conf "/etc/postgresql/*/main/postgresql.conf.backup-$(date +%Y%m%d)"

    # 添加WAL归档配置
    sudo tee -a /etc/postgresql/*/main/postgresql.conf > /dev/null <<EOF

# WAL归档配置
wal_level = replica
archive_mode = on
archive_command = '$PWD/config/backup/archive_command.sh %p'
archive_timeout = 3600
max_wal_senders = 3
wal_keep_segments = 64
EOF

    # 重启PostgreSQL服务
    sudo systemctl restart postgresql

    if [[ $? -eq 0 ]]; then
        log_info "WAL归档配置成功"
    else
        log_error "WAL归档配置失败"
        exit 1
    fi
}

# 创建systemd服务用于自动备份
create_backup_service() {
    log_step "创建自动备份服务..."

    # 创建systemd服务文件
    sudo tee /etc/systemd/system/postgresql-backup.service > /dev/null <<EOF
[Unit]
Description=PostgreSQL Database Backup
After=postgresql.service
Wants=postgresql.service

[Service]
Type=oneshot
User=$USER
Group=$USER
EnvironmentFile=$PWD/$CONFIG_DIR/backup_config.env
ExecStart=$PWD/scripts/backup-database.py backup --type full --compress --encrypt
StandardOutput=journal
StandardError=journal
EOF

    # 创建定时器文件
    sudo tee /etc/systemd/system/postgresql-backup.timer > /dev/null <<EOF
[Unit]
Description=Run PostgreSQL backup daily at 2 AM
Requires=postgresql-backup.service

[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 重新加载systemd并启用服务
    sudo systemctl daemon-reload
    sudo systemctl enable postgresql-backup.timer
    sudo systemctl start postgresql-backup.timer

    log_info "自动备份服务已创建并启用"
}

# 创建增量备份服务
create_incremental_backup_service() {
    log_step "创建增量备份服务..."

    # 创建systemd服务文件
    sudo tee /etc/systemd/system/postgresql-incremental-backup.service > /dev/null <<EOF
[Unit]
Description=PostgreSQL Incremental Backup
After=postgresql.service
Wants=postgresql.service

[Service]
Type=oneshot
User=$USER
Group=$USER
EnvironmentFile=$PWD/$CONFIG_DIR/backup_config.env
ExecStart=$PWD/scripts/backup-database.py backup --type incremental
StandardOutput=journal
StandardError=journal
EOF

    # 创建定时器文件（每6小时）
    sudo tee /etc/systemd/system/postgresql-incremental-backup.timer > /dev/null <<EOF
[Unit]
Description=Run PostgreSQL incremental backup every 6 hours
Requires=postgresql-incremental-backup.service

[Timer]
OnCalendar=*-*-* 00,06,12,18:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 重新加载systemd并启用服务
    sudo systemctl daemon-reload
    sudo systemctl enable postgresql-incremental-backup.timer
    sudo systemctl start postgreslog-incremental-backup.timer

    log_info "增量备份服务已创建并启用"
}

# 创建清理服务
create_cleanup_service() {
    log_step "创建备份清理服务..."

    # 创建清理脚本
    cat > "$CONFIG_DIR/cleanup_old_backups.sh" <<EOF
#!/bin/bash
# 清理旧备份脚本

source "$PWD/$CONFIG_DIR/backup_config.env"

# 清理本地备份
find "$BACKUP_DIR" -type f -mtime +\$RETENTION_DAYS -delete

# 清理WAL归档（保留7天）
find /var/lib/postgresql/wal_archive -type f -mtime +7 -delete

# 运行Python清理脚本
$PWD/scripts/backup-database.py cleanup

# 记录清理日志
echo "\$(date): 清理完成" >> logs/backup/cleanup.log
EOF
    chmod +x "$CONFIG_DIR/cleanup_old_backups.sh"

    # 创建systemd服务
    sudo tee /etc/systemd/system/postgresql-backup-cleanup.service > /dev/null <<EOF
[Unit]
Description=Clean up old PostgreSQL backups
After=postgresql-backup.service

[Service]
Type=oneshot
User=$USER
Group=$USER
ExecStart=$PWD/$CONFIG_DIR/cleanup_old_backups.sh
StandardOutput=journal
StandardError=journal
EOF

    # 创建定时器（每周执行）
    sudo tee /etc/systemd/system/postgresql-backup-cleanup.timer > /dev/null <<EOF
[Unit]
Description=Clean up old PostgreSQL backups weekly
Requires=postgresql-backup-cleanup.service

[Timer]
OnCalendar=Mon *-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    # 重新加载systemd并启用服务
    sudo systemctl daemon-reload
    sudo systemctl enable postgresql-backup-cleanup.timer
    sudo systemctl start postgresql-backup-cleanup.timer

    log_info "备份清理服务已创建并启用"
}

# 创建监控脚本
create_monitoring_script() {
    log_step "创建备份监控脚本..."

    cat > "$CONFIG_DIR/monitor_backups.sh" <<'EOF'
#!/bin/bash
# 备份监控脚本

source "$(dirname "$0")/backup_config.env"

# 检查最近24小时是否有备份
RECENT_BACKUP=$(find "$BACKUP_DIR" -name "*.sql*" -type f -mtime -1 | wc -l)

if [[ $RECENT_BACKUP -eq 0 ]]; then
    echo "WARNING: No backups found in the last 24 hours!"

    # 发送告警
    if [[ -n "${BACKUP_NOTIFY_EMAIL:-}" ]]; then
        echo "No backups found in the last 24 hours for database $DB_NAME" | \
            mail -s "Backup Alert - $DB_NAME" "$BACKUP_NOTIFY_EMAIL"
    fi

    if [[ -n "${BACKUP_NOTIFY_SLACK_WEBHOOK:-}" ]]; then
        curl -X POST -H 'Content-type: application/json' \
            --data "{\"text\":\"⚠️ No backups found in the last 24 hours for database: $DB_NAME\"}" \
            "$BACKUP_NOTIFY_SLACK_WEBHOOK"
    fi
else
    echo "OK: Found $RECENT_BACKUP backup(s) in the last 24 hours"
fi

# 检查备份大小
LATEST_BACKUP=$(find "$BACKUP_DIR" -name "*.sql*" -type f -mmin -1440 | head -1)
if [[ -n "$LATEST_BACKUP" ]]; then
    BACKUP_SIZE=$(du -h "$LATEST_BACKUP" | cut -f1)
    echo "Latest backup size: $BACKUP_SIZE"
fi

# 检查磁盘空间
DISK_USAGE=$(df -h "$BACKUP_DIR" | tail -1 | awk '{print $5}' | sed 's/%//')
if [[ $DISK_USAGE -gt 80 ]]; then
    echo "WARNING: Backup directory disk usage is ${DISK_USAGE}%"
fi
EOF
    chmod +x "$CONFIG_DIR/monitor_backups.sh"

    # 创建监控定时器
    sudo tee /etc/systemd/system/postgresql-backup-monitor.timer > /dev/null <<EOF
[Unit]
Description=Monitor PostgreSQL backups

[Timer]
OnCalendar=*-*-* 09:00:00
Persistent=true

[Install]
WantedBy=timers.target
EOF

    sudo tee /etc/systemd/system/postgresql-backup-monitor.service > /dev/null <<EOF
[Unit]
Description=Monitor PostgreSQL backups

[Service]
Type=oneshot
User=$USER
Group=$USER
ExecStart=$PWD/$CONFIG_DIR/monitor_backups.sh
StandardOutput=journal
StandardError=journal
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable postgresql-backup-monitor.timer
    sudo systemctl start postgresql-backup-monitor.timer

    log_info "备份监控已配置"
}

# 测试备份功能
test_backup() {
    log_step "测试备份功能..."

    # 运行测试备份
    python3 scripts/backup-database.py backup --type full --compress

    # 验证备份文件
    LATEST_BACKUP=$(find "$BACKUP_DIR" -name "full_*.sql*" -type f -mmin -5 | head -1)

    if [[ -n "$LATEST_BACKUP" ]]; then
        log_info "备份测试成功: $LATEST_BACKUP"

        # 验证备份
        python3 scripts/backup-database.py verify --file "$LATEST_BACKUP"
    else
        log_error "备份测试失败：未找到备份文件"
        exit 1
    fi
}

# 显示服务状态
show_status() {
    log_step "显示服务状态..."

    echo ""
    echo "备份服务状态："
    echo "=============="

    # 检查定时器
    for timer in postgresql-backup postgresql-incremental-backup postgresql-backup-cleanup postgresql-backup-monitor; do
        if systemctl is-enabled "$timer.timer" &>/dev/null; then
            echo "✓ $timer.timer 已启用"
            echo "  下次运行: $(systemctl list-timers "$timer.timer" | tail -1 | awk '{print $5" "$6" "$7}')"
        else
            echo "✗ $timer.timer 未启用"
        fi
    done

    echo ""
    echo "最近备份："
    echo "=========="

    # 显示最近5个备份
    find "$BACKUP_DIR" -name "*.sql*" -type f -printf "%T@ %p %s\n" | \
        sort -nr | head -5 | while read timestamp file size; do
        date_str=$(date -d "@${timestamp%.*}" '+%Y-%m-%d %H:%M:%S')
        size_str=$(numfmt --to=iec --suffix=B $size)
        echo "  $datestr  $size_str  $(basename "$file")"
    done

    echo ""
    echo "磁盘使用情况："
    echo "=============="
    du -sh "$BACKUP_DIR" 2>/dev/null || echo "备份目录不存在"

    if [[ -d /var/lib/postgresql/wal_archive ]]; then
        du -sh /var/lib/postgresql/wal_archive
    fi
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "Football Prediction - 备份自动化配置"
    echo "=========================================="
    echo ""

    # 检查是否为root用户（某些操作需要）
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi

    # 检查必要的工具
    for tool in psql python3 aws; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "缺少必要工具: $tool"
            exit 1
        fi
    done

    # 执行配置步骤
    create_directories
    create_backup_config
    create_backup_user

    # 配置WAL归档（需要sudo权限）
    if [[ "${1:-}" != "--no-wal" ]]; then
        log_warn "配置WAL归档需要sudo权限，如果提示请输入密码"
        configure_wal_archiving
    fi

    create_backup_service
    create_incremental_backup_service
    create_cleanup_service
    create_monitoring_script

    # 测试备份
    test_backup

    # 显示状态
    show_status

    echo ""
    echo "=========================================="
    echo "备份自动化配置完成！"
    echo "=========================================="
    echo ""
    echo "配置说明："
    echo "1. 全量备份：每天凌晨2点执行"
    echo "2. 增量备份：每6小时执行（00:00, 06:00, 12:00, 18:00）"
    echo "3. 清理任务：每周一凌晨3点执行"
    echo "4. 监控检查：每天上午9点执行"
    echo ""
    echo "管理命令："
    echo "  查看备份列表: python3 scripts/backup-database.py list"
    echo "  手动备份: python3 scripts/backup-database.py backup"
    echo "  恢复数据库: python3 scripts/backup-database.py restore --file <backup_file>"
    echo "  查看定时器: systemctl list-timers postgresql-*"
    echo "  查看日志: journalctl -u postgresql-backup"
    echo ""
}

# 处理命令行参数
case "${1:-}" in
    --test)
        test_backup
        ;;
    --status)
        show_status
        ;;
    --no-wal)
        main --no-wal
        ;;
    *)
        main
        ;;
esac
