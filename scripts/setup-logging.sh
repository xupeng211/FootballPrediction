#!/bin/bash

# 日志系统初始化脚本
# Football Prediction Project

set -euo pipefail

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

# 创建日志目录
create_log_directories() {
    log_info "创建应用日志目录..."

    local log_dirs=(
        "/var/log/football-prediction"
        "/var/log/football-prediction/api"
        "/var/log/football-prediction/celery"
        "/var/log/football-prediction/ml"
        "/var/log/football-prediction/tasks"
        "/var/log/celery"
        "/var/log/nginx"
    )

    for dir in "${log_dirs[@]}"; do
        if [[ ! -d "$dir" ]]; then
            sudo mkdir -p "$dir"
            sudo chmod 755 "$dir"
            log_info "创建目录: $dir"
        else
            log_warn "目录已存在: $dir"
        fi
    done
}

# 创建日志轮转配置
setup_log_rotation() {
    log_info "配置日志轮转..."

    local logrotate_config="/etc/logrotate.d/football-prediction"

    sudo tee "$logrotate_config" > /dev/null <<EOF
# Football Prediction Application Logs
/var/log/football-prediction/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    postrotate
        # 发送信号给应用重新打开日志文件
        if [ -f /var/run/football-prediction.pid ]; then
            kill -USR1 \$(cat /var/run/football-prediction.pid)
        fi
    endscript
}

# Celery Logs
/var/log/celery/*.log {
    daily
    missingok
    rotate 7
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
}

# Nginx Logs
/var/log/nginx/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 www-data www-data
    postrotate
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 \$(cat /var/run/nginx.pid)
        fi
    endscript
}
EOF

    log_info "日志轮转配置已更新: $logrotate_config"
}

# 创建应用日志配置
create_app_logging_config() {
    log_info "创建应用日志配置..."

    local config_dir="config/logging"
    mkdir -p "$config_dir"

    # 开发环境日志配置
    cat > "$config_dir/development.yaml" <<EOF
version: 1
disable_existing_loggers: false

formatters:
  default:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'

  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s'
    datefmt: '%Y-%m-%d %H:%M:%S'

  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "module": "%(module)s", "line": %(lineno)d, "message": "%(message)s"}'
    datefmt: '%Y-%m-%dT%H:%M:%S'

handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: detailed
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /var/log/football-prediction/app.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    encoding: utf-8

  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: json
    filename: /var/log/football-prediction/error.log
    maxBytes: 10485760  # 10MB
    backupCount: 5
    encoding: utf-8

loggers:
  src:
    level: DEBUG
    handlers: [console, file, error_file]
    propagate: false

  uvicorn:
    level: INFO
    handlers: [console, file]
    propagate: false

  sqlalchemy:
    level: WARNING
    handlers: [console, file]
    propagate: false

root:
  level: INFO
  handlers: [console, file]
EOF

    # 生产环境日志配置
    cat > "$config_dir/production.yaml" <<EOF
version: 1
disable_existing_loggers: false

formatters:
  json:
    format: '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "module": "%(module)s", "line": %(lineno)d, "trace_id": "%(trace_id)s", "message": "%(message)s"}'
    datefmt: '%Y-%m-%dT%H:%M:%S.%fZ'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: json
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /var/log/football-prediction/app.log
    maxBytes: 52428800  # 50MB
    backupCount: 10
    encoding: utf-8

  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: json
    filename: /var/log/football-prediction/error.log
    maxBytes: 52428800  # 50MB
    backupCount: 10
    encoding: utf-8

  audit_file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /var/log/football-prediction/audit.log
    maxBytes: 52428800  # 50MB
    backupCount: 20
    encoding: utf-8

loggers:
  src:
    level: INFO
    handlers: [console, file]
    propagate: false

  src.security:
    level: INFO
    handlers: [console, file, audit_file]
    propagate: false

  src.api:
    level: INFO
    handlers: [console, file]
    propagate: false

  uvicorn:
    level: INFO
    handlers: [console, file]
    propagate: false

  uvicorn.access:
    level: INFO
    handlers: [console, file]
    propagate: false

  sqlalchemy:
    level: WARNING
    handlers: [console, file]
    propagate: false

  celery:
    level: INFO
    handlers: [console, file]
    propagate: false

root:
  level: WARNING
  handlers: [console]
EOF

    log_info "日志配置文件已创建在: $config_dir"
}

# 创建systemd服务文件用于Promtail
create_promtail_service() {
    log_info "创建Promtail systemd服务..."

    local service_file="/etc/systemd/system/promtail.service"

    sudo tee "$service_file" > /dev/null <<EOF
[Unit]
Description=Promtail service
After=network.target

[Service]
Type=simple
User=$USER
Group=$USER
ExecStart=$(which docker) run --rm \\
    --name promtail \\
    -v $(pwd)/monitoring/loki/promtail-config.yml:/etc/promtail/config.yml \\
    -v /var/log:/var/log:readonly \\
    -v /var/lib/docker/containers:/var/lib/docker/containers:readonly \\
    -v promtail-positions:/tmp/promtail \\
    grafana/promtail:2.9.4 \\
    -config.file=/etc/promtail/config.yml
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable promtail
    log_info "Promtail服务已创建并启用"
}

# 创建日志查看脚本
create_log_scripts() {
    log_info "创建日志管理脚本..."

    mkdir -p scripts/logs

    # 实时查看应用日志
    cat > scripts/logs/view-app-logs.sh <<'EOF'
#!/bin/bash
# 查看应用日志

if [[ "$1" == "-f" ]]; then
    tail -f /var/log/football-prediction/app.log
else
    less /var/log/football-prediction/app.log
fi
EOF

    # 查看错误日志
    cat > scripts/logs/view-error-logs.sh <<'EOF'
#!/bin/bash
# 查看错误日志

if [[ "$1" == "-f" ]]; then
    tail -f /var/log/football-prediction/error.log
else
    less /var/log/football-prediction/error.log
fi
EOF

    # 查看审计日志
    cat > scripts/logs/view-audit-logs.sh <<'EOF'
#!/bin/bash
# 查看审计日志

if [[ "$1" == "-f" ]]; then
    tail -f /var/log/football-prediction/audit.log
else
    less /var/log/football-prediction/audit.log
fi
EOF

    # 搜索日志
    cat > scripts/logs/search-logs.sh <<'EOF'
#!/bin/bash
# 搜索日志
# Usage: ./search-logs.sh <pattern> <log_file>

PATTERN=${1:-}
LOG_FILE=${2:-/var/log/football-prediction/app.log}

if [[ -z "$PATTERN" ]]; then
    echo "Usage: $0 <pattern> [log_file]"
    exit 1
fi

grep -n "$PATTERN" "$LOG_FILE" | less
EOF

    # 统计日志错误
    cat > scripts/logs/count-errors.sh <<'EOF'
#!/bin/bash
# 统计错误日志

LOG_FILE="/var/log/football-prediction/error.log"
DAYS=${1:-1}

echo "最近 $DAYS 天的错误统计:"
echo "========================"

# 获取最近N天的错误
since_date=$(date -d "$DAYS days ago" '+%Y-%m-%d')
errors=$(grep "$since_date" "$LOG_FILE" | wc -l)

echo "错误总数: $errors"

if [[ $errors -gt 0 ]]; then
    echo -e "\n错误类型分布:"
    grep "$since_date" "$LOG_FILE" | grep -o '"level": "[^"]*"' | sort | uniq -c | sort -nr

    echo -e "\n错误模块分布:"
    grep "$since_date" "$LOG_FILE" | grep -o '"logger": "[^"]*"' | sort | uniq -c | sort -nr
fi
EOF

    # 设置脚本权限
    chmod +x scripts/logs/*.sh

    log_info "日志管理脚本已创建在: scripts/logs/"
}

# 主函数
main() {
    log_info "开始配置日志系统..."

    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi

    # 执行配置步骤
    create_log_directories
    setup_log_rotation
    create_app_logging_config
    create_promtail_service
    create_log_scripts

    log_info "日志系统配置完成！"
    log_info ""
    log_info "下一步操作："
    log_info "1. 启动日志栈: docker-compose -f docker-compose.loki.yml up -d"
    log_info "2. 启动Promtail: sudo systemctl start promtail"
    log_info "3. 访问Grafana: http://localhost:3000 (admin/admin123)"
    log_info "4. 在Grafana中探索日志: Explore -> 选择Loki数据源"
    log_info ""
    log_info "日志管理脚本："
    log_info "- 查看应用日志: ./scripts/logs/view-app-logs.sh"
    log_info "- 查看错误日志: ./scripts/logs/view-error-logs.sh"
    log_info "- 搜索日志: ./scripts/logs/search-logs.sh <pattern>"
    log_info "- 统计错误: ./scripts/logs/count-errors.sh [days]"
}

# 执行主函数
main "$@"
