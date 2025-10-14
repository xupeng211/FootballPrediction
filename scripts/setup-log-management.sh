#!/bin/bash

# 日志管理系统配置脚本
# 配置ELK/Loki日志栈和日志管理工具

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
ENVIRONMENT=${ENVIRONMENT:-production}
LOG_RETENTION_DAYS=${LOG_RETENTION_DAYS:-30}
LOKI_URL=${LOKI_URL:-http://localhost:3100}
ELASTICSEARCH_URL=${ELASTICSEARCH_URL:-http://localhost:9200}
KIBANA_URL=${KIBANA_URL:-http://localhost:5601}

# 创建目录结构
create_log_directories() {
    log_step "创建日志目录结构..."

    # 应用日志目录
    sudo mkdir -p /var/log/football-prediction/{api,celery,nginx,postgres,redis,security,audit,performance,business}
    sudo mkdir -p /var/log/football-prediction/archive/{daily,weekly,monthly}

    # 日志管理脚本目录
    mkdir -p scripts/log-management
    mkdir -p config/logrotate
    mkdir -p config/fluentd
    mkdir -p config/filebeat

    # 设置权限
    sudo chown -R $USER:$USER /var/log/football-prediction
    sudo chmod 755 /var/log/football-prediction

    log_info "日志目录已创建"
}

# 配置logrotate
setup_logrotate() {
    log_step "配置logrotate..."

    cat > config/logrotate/football-prediction <<'EOF'
# Football Prediction 日志轮转配置

/var/log/football-prediction/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    dateext
    dateformat -%Y%m%d
    extension .log
    sharedscripts
    postrotate
        # 发送信号给应用重新打开日志文件
        if [ -f /var/run/football-prediction.pid ]; then
            kill -USR1 $(cat /var/run/football-prediction.pid)
        fi
        # 通知Nginx重新打开日志
        if [ -f /var/run/nginx.pid ]; then
            kill -USR1 $(cat /var/run/nginx.pid)
        fi
    endscript
}

/var/log/football-prediction/security.log {
    daily
    missingok
    rotate 365
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    dateext
    dateformat -%Y%m%d
}

/var/log/football-prediction/audit.log {
    daily
    missingok
    rotate 90
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    dateext
    dateformat -%Y%m%d
}

/var/log/football-prediction/performance.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    dateext
    dateformat -%Y%m%d
}

/var/log/football-prediction/access.log {
    hourly
    missingok
    rotate 168  # 7天
    compress
    delaycompress
    notifempty
    create 644 $USER $USER
    dateext
    dateformat -%Y%m%d%H
    size 100M
}

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
            kill -USR1 $(cat /var/run/nginx.pid)
        fi
    endscript
}
EOF

    # 复制到系统目录
    sudo cp config/logrotate/football-prediction /etc/logrotate.d/

    # 测试配置
    sudo logrotate -d /etc/logrotate.d/football-prediction

    log_info "logrotate已配置"
}

# 配置Fluentd（可选）
setup_fluentd() {
    log_step "配置Fluentd日志收集..."

    # 创建Fluentd配置
    cat > config/fluentd/fluent.conf <<EOF
<source>
  @type tail
  path /var/log/football-prediction/*.log
  pos_file /var/log/fluentd/football-prediction.log.pos
  tag football-prediction.*
  format json
  time_format %Y-%m-%dT%H:%M:%S
  time_key timestamp
  keep_time_key true
</source>

# 过滤敏感信息
<filter football-prediction.**>
  @type record_transformer
  <record>
    message \${record["message"].gsub(/password["\']?\s*[:=]\s*["\']?([^"\'}\s,]+)/, 'password:"***"')}
  </record>
</filter>

# 添加环境标签
<filter football-prediction.**>
  @type record_transformer
  <record>
    environment "#{ENV['ENVIRONMENT'] || 'production'}"
    service "football-prediction"
  </record>
</filter>

# 输出到Loki
<match football-prediction.**>
  @type loki
  url ${LOKI_URL}/loki/api/v1/push
  extract_kubernetes_labels false
  labels
    environment "#{ENV['ENVIRONMENT'] || 'production'}"
    service "football-prediction"
    \${tag_parts[1]}
  </labels>
  line_format json
  remove_keys level,timestamp
</match>

# 错误日志处理
<match football-prediction.error>
  @type copy
  <store>
    @type loki
    url ${LOKI_URL}/loki/api/v1/push
    labels
      environment "#{ENV['ENVIRONMENT'] || 'production'}"
      service "football-prediction"
      level error
    </labels>
  </store>
  <store>
    @type file
    path /var/log/fluentd/error
    append true
  </store>
</match>
EOF

    # 创建systemd服务
    sudo tee /etc/systemd/system/fluentd.service > /dev/null <<EOF
[Unit]
Description=Fluentd data collector
Documentation=https://docs.fluentd.org/
After=network.target

[Service]
Type=notify
User=fluentd
Group=fluentd
Environment=LD_PRELOAD=/opt/fluent/embedded/lib/libjemalloc.so
EnvironmentFile=-/etc/default/fluentd
EnvironmentFile=-/etc/sysconfig/fluentd
ExecStart=/opt/fluent/embedded/bin/fluentd --under-supervisor
ExecReload=/bin/kill -USR2 \$MAINPID
Restart=always
RestartSec=5s
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
EOF

    log_info "Fluentd配置已创建"
}

# 配置Filebeat（替代方案）
setup_filebeat() {
    log_step "配置Filebeat日志收集..."

    cat > config/filebeat/filebeat.yml <<EOF
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/football-prediction/*.log
  json.keys_under_root: true
  json.add_error_key: true
  processors:
    - decode_json_fields:
        fields: ["message"]
        target: ""
        overwrite_keys: true

- type: filestream
  id: nginx-access
  enabled: true
  paths:
    - /var/log/nginx/access.log
  fields:
    logtype: nginx_access
  fields_under_root: true

- type: filestream
  id: nginx-error
  enabled: true
  paths:
    - /var/log/nginx/error.log
  fields:
    logtype: nginx_error
  fields_under_root: true

processors:
  - add_host_metadata:
      when.not.contains.tags: forwarded
  - add_docker_metadata: ~
  - add_kubernetes_metadata: ~

output.elasticsearch:
  hosts: ["${ELASTICSEARCH_URL}"]
  username: elastic
  password: ${ELASTICSEARCH_PASSWORD:-changeme}
  index: "football-prediction-%{+yyyy.MM.dd}"
  template.pattern: "football-prediction-*"
  template.settings:
    index.number_of_shards: 1
    index.number_of_replicas: 1

output.logstash:
  hosts: ["localhost:5044"]

setup.kibana:
  host: "${KIBANA_URL}"

setup.template.enabled: true
setup.template.pattern: "football-prediction-*"

logging.level: info
logging.to_files: true
logging.files:
  path: /var/log/filebeat
  name: filebeat
  keepfiles: 7
  permissions: 0644
EOF

    log_info "Filebeat配置已创建"
}

# 创建日志分析脚本
create_log_analyzers() {
    log_step "创建日志分析脚本..."

    # 错误日志分析器
    cat > scripts/log-management/error_analyzer.py <<'EOF'
#!/usr/bin/env python3
"""
错误日志分析器
分析系统错误并生成报告
"""

import re
import json
from collections import defaultdict, Counter
from datetime import datetime, timedelta
import argparse

def analyze_errors(log_file, hours=24):
    """分析错误日志"""
    errors = []
    error_patterns = defaultdict(int)
    error_timeline = defaultdict(int)

    # 计算时间范围
    start_time = datetime.now() - timedelta(hours=hours)

    with open(log_file, 'r') as f:
        for line in f:
            try:
                # 解析JSON日志
                log_entry = json.loads(line)

                # 检查是否为错误日志
                if log_entry.get('level') == 'ERROR':
                    timestamp = datetime.fromisoformat(log_entry.get('timestamp', '').replace('Z', '+00:00'))
                    if timestamp > start_time:
                        errors.append(log_entry)

                        # 提取错误模式
                        message = log_entry.get('message', '')
                        pattern = extract_error_pattern(message)
                        error_patterns[pattern] += 1

                        # 统计时间线
                        hour_key = timestamp.strftime('%Y-%m-%d %H:00')
                        error_timeline[hour_key] += 1

            except (json.JSONDecodeError, ValueError):
                continue

    return errors, error_patterns, error_timeline

def extract_error_pattern(message):
    """提取错误模式"""
    # 常见错误模式
    patterns = [
        (r'Connection.*refused', 'Connection Refused'),
        (r'timeout', 'Timeout'),
        (r'Authentication.*failed', 'Authentication Failed'),
        (r'Permission.*denied', 'Permission Denied'),
        (r'File.*not.*found', 'File Not Found'),
        (r'database.*error', 'Database Error'),
        (r'sql.*error', 'SQL Error'),
        (r'validation.*error', 'Validation Error'),
        (r'serialization.*error', 'Serialization Error'),
        (r'memory.*error', 'Memory Error'),
    ]

    for pattern, label in patterns:
        if re.search(pattern, message, re.IGNORECASE):
            return label

    # 提取第一个词作为模式
    first_word = message.split()[0] if message else 'Unknown'
    return first_word

def generate_report(errors, patterns, timeline, output_file=None):
    """生成分析报告"""
    report = {
        'summary': {
            'total_errors': len(errors),
            'unique_patterns': len(patterns),
            'analysis_time': datetime.now().isoformat(),
            'time_range_hours': 24
        },
        'top_errors': dict(Counter(patterns).most_common(10)),
        'timeline': dict(timeline),
        'recommendations': []
    }

    # 生成建议
    if len(errors) > 100:
        report['recommendations'].append('错误数量过多，需要立即关注')

    most_common = Counter(patterns).most_common(1)[0]
    if most_common[1] > len(errors) * 0.5:
        report['recommendations'].append(f'主要错误类型: {most_common[0]} (占{most_common[1]/len(errors):.1%})')

    # 输出报告
    if output_file:
        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"报告已保存到: {output_file}")

    # 打印摘要
    print("\n=== 错误分析报告 ===")
    print(f"总错误数: {report['summary']['total_errors']}")
    print(f"唯一错误模式: {report['summary']['unique_patterns']}")
    print("\n前5大错误类型:")
    for error, count in Counter(patterns).most_common(5):
        print(f"  - {error}: {count}次")

    if report['recommendations']:
        print("\n建议:")
        for rec in report['recommendations']:
            print(f"  - {rec}")

    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='分析错误日志')
    parser.add_argument('--file', default='/var/log/football-prediction/error.log',
                       help='日志文件路径')
    parser.add_argument('--hours', type=int, default=24,
                       help='分析最近几小时的日志')
    parser.add_argument('--output', help='输出报告文件')

    args = parser.parse_args()

    errors, patterns, timeline = analyze_errors(args.file, args.hours)
    generate_report(errors, patterns, timeline, args.output)
EOF

    chmod +x scripts/log-management/error_analyzer.py

    # 日志聚合脚本
    cat > scripts/log-management/log_aggregator.py <<'EOF'
#!/usr/bin/env python3
"""
日志聚合器
将多个日志文件聚合并索引
"""

import os
import gzip
import json
import sqlite3
from datetime import datetime
import argparse

class LogAggregator:
    def __init__(self, db_path='logs.db'):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """初始化数据库"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            level TEXT,
            logger TEXT,
            message TEXT,
            service TEXT,
            environment TEXT,
            request_id TEXT,
            user_id TEXT,
            raw_data TEXT
        )
        ''')

        # 创建索引
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_timestamp ON logs(timestamp)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_level ON logs(level)
        ''')
        cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_logger ON logs(logger)
        ''')

        conn.commit()
        conn.close()

    def process_file(self, file_path):
        """处理单个日志文件"""
        print(f"处理文件: {file_path}")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 判断是否为压缩文件
        if file_path.endswith('.gz'):
            open_func = gzip.open
            mode = 'rt'
        else:
            open_func = open
            mode = 'r'

        count = 0
        try:
            with open_func(file_path, mode) as f:
                for line in f:
                    try:
                        if line.strip():
                            log_entry = json.loads(line)

                            # 插入数据库
                            cursor.execute('''
                            INSERT INTO logs (
                                timestamp, level, logger, message, service,
                                environment, request_id, user_id, raw_data
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                log_entry.get('timestamp'),
                                log_entry.get('level'),
                                log_entry.get('logger'),
                                log_entry.get('message'),
                                log_entry.get('service'),
                                log_entry.get('environment'),
                                log_entry.get('request_id'),
                                log_entry.get('user_id'),
                                line.strip()
                            ))

                            count += 1
                    except (json.JSONDecodeError, ValueError):
                        continue

            conn.commit()
            print(f"  处理了 {count} 条日志")

        except Exception as e:
            print(f"  错误: {e}")
        finally:
            conn.close()

    def aggregate_directory(self, directory, pattern='*.log*'):
        """聚合目录中的日志文件"""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.startswith(pattern) or pattern.startswith(file):
                    file_path = os.path.join(root, file)
                    self.process_file(file_path)

    def search(self, query, limit=100):
        """搜索日志"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
        SELECT * FROM logs
        WHERE message LIKE ? OR logger LIKE ?
        ORDER BY timestamp DESC
        LIMIT ?
        ''', (f'%{query}%', f'%{query}%', limit))

        results = cursor.fetchall()
        conn.close()

        return results

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='日志聚合器')
    parser.add_argument('--dir', default='/var/log/football-prediction',
                       help='日志目录')
    parser.add_argument('--pattern', default='*.log*',
                       help='文件模式')
    parser.add_argument('--search', help='搜索关键词')
    parser.add_argument('--limit', type=int, default=100,
                       help='搜索结果限制')

    args = parser.parse_args()

    aggregator = LogAggregator()

    if args.search:
        results = aggregator.search(args.search, args.limit)
        print(f"\n搜索 '{args.search}' 的结果:")
        for row in results[:10]:
            print(f"{row[1]} - {row[4]}: {row[5]}")
        print(f"\n共找到 {len(results)} 条记录")
    else:
        aggregator.aggregate_directory(args.dir, args.pattern)
        print("日志聚合完成")
EOF

    chmod +x scripts/log-management/log_aggregator.py

    # 日志清理脚本
    cat > scripts/log-management/cleanup_logs.sh <<'EOF'
#!/bin/bash
# 日志清理脚本

LOG_DIR="/var/log/football-prediction"
ARCHIVE_DIR="/var/log/football-prediction/archive"
RETENTION_DAYS=30

echo "开始清理日志..."

# 压缩超过1天的日志
find $LOG_DIR -name "*.log" -mtime +1 -exec gzip {} \;

# 移动压缩文件到归档目录
find $LOG_DIR -name "*.gz" -mtime +1 -exec mv {} $ARCHIVE_DIR/daily/ \;

# 删除超过保留期的日志
find $ARCHIVE_DIR/daily -name "*.gz" -mtime +$RETENTION_DAYS -delete

# 清理空目录
find $LOG_DIR -type d -empty -delete

# 计算磁盘空间
echo "磁盘使用情况:"
du -sh $LOG_DIR
du -sh $ARCHIVE_DIR

echo "日志清理完成"
EOF

    chmod +x scripts/log-management/cleanup_logs.sh

    log_info "日志分析脚本已创建"
}

# 配置日志告警
setup_log_alerts() {
    log_step "配置日志告警..."

    # 创建日志告警脚本
    cat > scripts/log-management/log_alerts.py <<'EOF'
#!/usr/bin/env python3
"""
日志告警监控
监控错误日志并触发告警
"""

import time
import requests
import json
from datetime import datetime, timedelta
import logging
import os

# 配置
SLACK_WEBHOOK = os.getenv('SLACK_WEBHOOK', '')
ERROR_THRESHOLD = 10  # 5分钟内超过10个错误
CRITICAL_THRESHOLD = 5  # 5分钟内超过5个关键错误

def check_error_logs():
    """检查错误日志"""
    error_count = 0
    critical_count = 0
    errors = []

    # 检查最近5分钟的错误日志
    with open('/var/log/football-prediction/error.log', 'r') as f:
        current_time = datetime.now()
        five_minutes_ago = current_time - timedelta(minutes=5)

        for line in f:
            try:
                log_entry = json.loads(line)
                timestamp = datetime.fromisoformat(log_entry['timestamp'].replace('Z', '+00:00'))

                if timestamp > five_minutes_ago:
                    error_count += 1
                    errors.append(log_entry)

                    # 检查关键错误
                    message = log_entry.get('message', '').lower()
                    if any(keyword in message for keyword in
                          ['database', 'authentication', 'security', 'memory']):
                        critical_count += 1

            except (json.JSONDecodeError, ValueError):
                continue

    return error_count, critical_count, errors

def send_alert(message, level='warning'):
    """发送告警"""
    print(f"[ALERT] {level.upper()}: {message}")

    # 发送到Slack
    if SLACK_WEBHOOK:
        color = 'danger' if level == 'critical' else 'warning'
        payload = {
            'text': message,
            'attachments': [{
                'color': color,
                'title': f'Football Prediction {level.upper()} Alert',
                'text': message,
                'ts': int(time.time())
            }]
        }

        try:
            response = requests.post(SLACK_WEBHOOK, json=payload)
            if response.status_code != 200:
                print(f"Failed to send Slack alert: {response.text}")
        except Exception as e:
            print(f"Error sending Slack alert: {e}")

def main():
    """主函数"""
    while True:
        try:
            error_count, critical_count, errors = check_error_logs()

            # 关键错误告警
            if critical_count >= CRITICAL_THRESHOLD:
                message = f"检测到 {critical_count} 个关键错误在最近5分钟内！"
                send_alert(message, 'critical')

            # 一般错误告警
            elif error_count >= ERROR_THRESHOLD:
                message = f"检测到 {error_count} 个错误在最近5分钟内"
                send_alert(message, 'warning')

            # 每5分钟检查一次
            time.sleep(300)

        except Exception as e:
            print(f"Error in log alerts: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
EOF

    chmod +x scripts/log-management/log_alerts.py

    # 创建systemd服务
    sudo tee /etc/systemd/system/log-alerts.service > /dev/null <<EOF
[Unit]
Description=Log Alerts Monitor
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="SLACK_WEBHOOK=$SLACK_WEBHOOK"
ExecStart=$(pwd)/scripts/log-management/log_alerts.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo systemctl daemon-reload
    sudo systemctl enable log-alerts

    log_info "日志告警已配置"
}

# 创建日志仪表板
create_log_dashboard() {
    log_step "创建日志仪表板..."

    # Grafana日志仪表板
    cat > monitoring/production/dashboards/log-analysis.json <<'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Log Analysis Dashboard",
    "tags": ["logs", "production"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(log_entries_total{level=\"error\"}[5m])",
            "legendFormat": "{{logger}}"
          }
        ],
        "yAxes": [
          {
            "label": "Errors/sec"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Log Volume",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(log_entries_total[5m])",
            "legendFormat": "{{level}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Top Error Sources",
        "type": "table",
        "targets": [
          {
            "expr": "topk(10, sum by (logger) (log_entries_total{level=\"error\"}))",
            "format": "table"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Log Volume by Service",
        "type": "piechart",
        "targets": [
          {
            "expr": "sum by (service) (log_entries_total)",
            "legendFormat": "{{service}}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
      },
      {
        "id": 5,
        "title": "Critical Errors",
        "type": "stat",
        "targets": [
          {
            "expr": "rate(log_entries_total{level=\"critical\"}[5m])",
            "legendFormat": "Critical Errors/sec"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
      }
    ],
    "time": {"from": "now-1h", "to": "now"},
    "refresh": "30s"
  }
}
EOF

    log_info "日志仪表板已创建"
}

# 测试日志系统
test_log_system() {
    log_step "测试日志系统..."

    # 写入测试日志
    echo '{"timestamp": "'$(date -Iseconds)'", "level": "INFO", "logger": "test", "message": "测试日志系统"}' >> /var/log/football-prediction/app.log

    # 检查日志文件
    if [ -f "/var/log/football-prediction/app.log" ]; then
        log_info "✓ 日志文件创建成功"
    else
        log_error "✗ 日志文件创建失败"
    fi

    # 测试logrotate
    if sudo logrotate -d /etc/logrotate.d/football-prediction >/dev/null 2>&1; then
        log_info "✓ logrotate配置正确"
    else
        log_error "✗ logrotate配置有误"
    fi

    log_info "日志系统测试完成"
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "配置日志管理系统"
    echo "=========================================="
    echo ""

    # 检查权限
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi

    # 执行配置步骤
    create_log_directories
    setup_logrotate
    setup_fluentd
    setup_filebeat
    create_log_analyzers
    setup_log_alerts
    create_log_dashboard
    test_log_system

    echo ""
    echo "=========================================="
    echo "日志管理系统配置完成！"
    echo "=========================================="
    echo ""
    echo "日志目录："
    echo "  • 应用日志: /var/log/football-prediction/"
    echo "  • 归档日志: /var/log/football-prediction/archive/"
    echo ""
    echo "管理工具："
    echo "  • 错误分析: ./scripts/log-management/error_analyzer.py"
    echo "  • 日志聚合: ./scripts/log-management/log_aggregator.py"
    echo "  • 日志清理: ./scripts/log-management/cleanup_logs.sh"
    echo "  • 告警监控: ./scripts/log-management/log_alerts.py"
    echo ""
    echo "配置文件："
    echo "  • Logrotate: /etc/logrotate.d/football-prediction"
    echo "  • Fluentd: config/fluentd/fluent.conf"
    echo "  • Filebeat: config/filebeat/filebeat.yml"
    echo ""
    echo "使用方法："
    echo "  • 分析错误日志: python scripts/log-management/error_analyzer.py --file /var/log/football-prediction/error.log"
    echo "  • 搜索日志: python scripts/log-management/log_aggregator.py --search 'database error'"
    echo "  • 启动告警: sudo systemctl start log-alerts"
}

# 执行主函数
main "$@"
