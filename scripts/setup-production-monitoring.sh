#!/bin/bash

# 生产环境监控配置脚本
# 配置完整的监控和告警系统

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
PROMETHEUS_URL=${PROMETHEUS_URL:-http://localhost:9090}
GRAFANA_URL=${GRAFANA_URL:-http://localhost:3000}
ALERTMANAGER_URL=${ALERTMANAGER_URL:-http://localhost:9093}
ENVIRONMENT=${ENVIRONMENT:-production}
SLACK_WEBHOOK=${SLACK_WEBHOOK:-}
EMAIL_SMTP=${EMAIL_SMTP:-smtp.gmail.com:587}
EMAIL_USER=${EMAIL_USER:-alerts@footballprediction.com}
EMAIL_PASSWORD=${EMAIL_PASSWORD:-}

# 创建配置目录
create_directories() {
    log_step "创建监控配置目录..."

    mkdir -p monitoring/production/{rules,dashboards,templates}
    mkdir -p config/alertmanager
    mkdir -p scripts/monitoring
    mkdir -p logs/monitoring
}

# 配置Prometheus生产规则
setup_prometheus_rules() {
    log_step "配置Prometheus生产规则..."

    # 复制告警规则
    cp monitoring/production/alerts.yml monitoring/prometheus/rules/

    # 创建服务发现配置
    cat > monitoring/prometheus/file_sd.yml <<EOF
- targets:
  - 'localhost:9090'
  labels:
    job: 'prometheus'
    environment: '$ENVIRONMENT'

- targets:
  - 'localhost:8000'
  labels:
    job: 'football-prediction'
    environment: '$ENVIRONMENT'

- targets:
  - 'localhost:5432'
  labels:
    job: 'postgres'
    environment: '$ENVIRONMENT'

- targets:
  - 'localhost:6379'
  labels:
    job: 'redis'
    environment: '$ENVIRONMENT'

- targets:
  - 'localhost:9100'
  labels:
    job: 'node-exporter'
    environment: '$ENVIRONMENT'

- targets:
  - 'localhost:9121'
  labels:
    job: 'redis-exporter'
    environment: '$ENVIRONMENT'

- targets:
  - 'localhost:9187'
  labels:
    job: 'postgres-exporter'
    environment: '$ENVIRONMENT'
EOF

    log_info "Prometheus规则已配置"
}

# 配置Alertmanager
setup_alertmanager() {
    log_step "配置Alertmanager..."

    cat > config/alertmanager/alertmanager.yml <<EOF
global:
  smtp_smarthost: '$EMAIL_SMTP'
  smtp_from: '$EMAIL_USER'
  smtp_auth_username: '$EMAIL_USER'
  smtp_auth_password: '$EMAIL_PASSWORD'

templates:
  - '/etc/alertmanager/templates/*.tmpl'

route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 12h
  receiver: 'default'
  routes:
    # Critical告警立即发送
    - match:
        severity: critical
      receiver: 'critical-alerts'
      continue: true
      group_wait: 0s
      repeat_interval: 5m

    # 安全告警立即发送
    - match:
        service: security
      receiver: 'security-alerts'
      continue: true
      group_wait: 0s
      repeat_interval: 5m

    # 业务告警工作时间发送
    - match:
        service: business
      receiver: 'business-alerts'
      active_time_intervals:
        - business-hours

    # 系统告警
    - match:
        service: system
      receiver: 'ops-alerts'

receivers:
  - name: 'default'
    email_configs:
      - to: '$EMAIL_USER'
        subject: '[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}'
        body: |
          {{ range .Alerts }}
          告警名称: {{ .Annotations.summary }}
          告警描述: {{ .Annotations.description }}
          严重级别: {{ .Labels.severity }}
          开始时间: {{ .StartsAt }}
          跳转链接: {{ .GeneratorURL }}
          {{ end }}

    # Slack通知（如果配置了）
    ${SLACK_WEBHOOK:+slack_configs:}
    ${SLACK_WEBHOOK:+  - api_url: '$SLACK_WEBHOOK'}
    ${SLACK_WEBHOOK:+    channel: '#alerts'}
    ${SLACK_WEBHOOK:+    title: 'Football Prediction Alert'}
    ${SLASH_WEBHOOK:+    text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'}

  - name: 'critical-alerts'
    email_configs:
      - to: 'oncall@footballprediction.com,$EMAIL_USER'
        subject: '🚨 [CRITICAL] {{ .GroupLabels.alertname }}'
        body: |
          🚨 CRITICAL ALERT 🚨

          {{ range .Alerts }}
          告警: {{ .Annotations.summary }}
          详情: {{ .Annotations.description }}
          实例: {{ .Labels.instance }}
          时间: {{ .StartsAt }}
          跳转: {{ .GeneratorURL }}
          {{ end }}

    ${SLACK_WEBHOOK:+slack_configs:}
    ${SLACK_WEBHOOK:+  - api_url: '$SLACK_WEBHOOK'}
    ${SLASH_WEBHOOK:+    channel: '#alerts-critical'}
    ${SLASH_WEBHOOK:+    title: '🚨 Critical Alert'}
    ${SLASH_WEBHOOK:+    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'}
    ${SLASH_WEBHOOK:+    color: 'danger'}

  - name: 'security-alerts'
    email_configs:
      - to: 'security@footballprediction.com'
        subject: '🔒 [SECURITY] {{ .GroupLabels.alertname }}'
        body: |
          🔒 SECURITY ALERT 🔒

          {{ range .Alerts }}
          安全事件: {{ .Annotations.summary }}
          详情: {{ .Annotations.description }}
          来源: {{ .Labels.instance }}
          时间: {{ .StartsAt }}
          {{ end }}

    ${SLACK_WEBHOOK:+slack_configs:}
    ${SLASH_WEBHOOK:+  - api_url: '$SLACK_WEBHOOK'}
    ${SLASH_WEBHOOK:+    channel: '#security-alerts'}
    ${SLASH_WEBHOOK:+    title: 'Security Alert'}
    ${SLASH_WEBHOOK:+    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'}
    ${SLASH_WEBHOOK:+    color: 'warning'}

  - name: 'ops-alerts'
    email_configs:
      - to: 'ops@footballprediction.com'
        subject: '[OPS] {{ .GroupLabels.alertname }}'

    ${SLACK_WEBHOOK:+slack_configs:}
    ${SLASH_WEBHOOK:+  - api_url: '$SLACK_WEBHOOK'}
    ${SLASH_WEBHOOK:+    channel: '#ops-alerts'}
    ${SLASH_WEBHOOK:+    title: 'Ops Alert'}
    ${SLASH_WEBHOOK:+    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'}
    ${SLASH_WEBHOOK:+    color: 'warning'}

  - name: 'business-alerts'
    email_configs:
      - to: 'product@footballprediction.com'
        subject: '[PRODUCT] {{ .GroupLabels.alertname }}'

    ${SLACK_WEBHOOK:+slack_configs:}
    ${SLASH_WEBHOOK:+  - api_url: '$SLACK_WEBHOOK'}
    ${SLASH_WEBHOOK:+    channel: '#product-alerts'}
    ${SLASH_WEBHOOK:+    title: 'Product Alert'}
    ${SLASH_WEBHOOK:+    text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'}
    ${SLASH_WEBHOOK:+    color: 'good'}

inhibit_rules:
  # 如果API服务完全宕机，抑制其他API相关告警
  - source_match:
      - alertname: ServiceDown
      service: api
    target_match:
      service: api
    equal: ['alertname']

time_intervals:
  - name: business-hours
    time_intervals:
      - times:
          - start_time: '09:00'
          end_time: '18:00'
        weekdays: ['monday:friday']
EOF

    log_info "Alertmanager已配置"
}

# 创建告警模板
create_alert_templates() {
    log_step "创建告警模板..."

    cat > config/alertmanager/templates/email.tmpl <<'EOF'
{{ define "email.default.subject" }}
[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}
{{ end }}

{{ define "email.default.body" }}
{{ range .Alerts }}
<strong>告警名称:</strong> {{ .Annotations.summary }}<br>
<strong>告警描述:</strong> {{ .Annotations.description }}<br>
<strong>严重级别:</strong> {{ .Labels.severity }}<br>
<strong>开始时间:</strong> {{ .StartsAt.Format "2006-01-02 15:04:05" }}<br>
<strong>实例:</strong> {{ .Labels.instance }}<br>
<strong>服务:</strong> {{ .Labels.service }}<br>
<br>
{{ end }}
{{ end }}

{{ define "email.critical.subject" }}
🚨 CRITICAL: {{ .GroupLabels.alertname }}
{{ end }}

{{ define "email.critical.body" }}
<h2 style="color: red;">🚨 CRITICAL ALERT 🚨</h2>
{{ range .Alerts }}
<p><strong>告警:</strong> {{ .Annotations.summary }}</p>
<p><strong>详情:</strong> {{ .Annotations.description }}</p>
<p><strong>实例:</strong> {{ .Labels.instance }}</p>
<p><strong>时间:</strong> {{ .StartsAt.Format "2006-01-02 15:04:05" }}</p>
<p><strong>跳转:</strong> <a href="{{ .GeneratorURL }}">查看详情</a></p>
<hr>
{{ end }}
{{ end }}
EOF

    log_info "告警模板已创建"
}

# 配置Node Exporter
setup_node_exporter() {
    log_step "配置Node Exporter..."

    # 创建systemd服务
    sudo tee /etc/systemd/system/node-exporter.service > /dev/null <<EOF
[Unit]
Description=Node Exporter
Wants=network-online.target
After=network-online.target

[Service]
User=node_exporter
Group=node_exporter
Type=simple
ExecStart=/usr/local/bin/node_exporter \
  --web.listen-address=0.0.0.0:9100 \
  --path.rootfs=/host \
  --path.procfs=/host/proc \
  --path.sysfs=/host/sys \
  --collector.filesystem \
  --collector.cpu \
  --collector.meminfo \
  --collector.diskstats \
  --collector.netdev \
  --collector.netstat \
  --collector.stat \
  --collector.systemd \
  --collector.textfile \
  --collector.textfile.directory=/var/lib/node_exporter

[Install]
WantedBy=multi-user.target
EOF

    # 创建用户
    sudo useradd --no-create-home --shell /bin/false node_exporter || true

    # 下载并安装
    NODE_EXPORTER_VERSION="1.6.1"
    cd /tmp
    wget https://github.com/prometheus/node_exporter/releases/download/v${NODE_EXPORTER_VERSION}/node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
    tar xvfz node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64.tar.gz
    sudo mv node_exporter-${NODE_EXPORTER_VERSION}.linux-amd64/node_exporter /usr/local/bin/

    # 设置权限
    sudo chown node_exporter:node_exporter /usr/local/bin/node_exporter

    # 启动服务
    sudo systemctl daemon-reload
    sudo systemctl enable node-exporter
    sudo systemctl start node-exporter

    log_info "Node Exporter已配置并启动"
}

# 配置进程监控
setup_process_monitoring() {
    log_step "配置进程监控..."

    # 创建进程监控脚本
    cat > scripts/monitoring/process_monitor.py <<'EOF'
#!/usr/bin/env python3
"""
进程监控脚本
监控关键进程并生成Prometheus指标
"""

import psutil
import time
from prometheus_client import start_http_server, Gauge, Counter
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义指标
PROCESS_COUNT = Gauge('process_count', 'Number of processes', ['process_name'])
PROCESS_CPU = Gauge('process_cpu_percent', 'Process CPU usage', ['process_name'])
PROCESS_MEMORY = Gauge('process_memory_bytes', 'Process memory usage', ['process_name'])
PROCESS_RESTARTS = Counter('process_restarts_total', 'Process restarts', ['process_name'])

# 要监控的进程
PROCESSES = {
    'uvicorn': ['uvicorn'],
    'postgres': ['postgres'],
    'redis': ['redis-server'],
    'nginx': ['nginx'],
    'celery': ['celery'],
}

def monitor_processes():
    """监控进程"""
    process_states = {}

    while True:
        try:
            for name, patterns in PROCESSES.items():
                found = False
                total_cpu = 0
                total_memory = 0
                count = 0

                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        cmdline = ' '.join(proc.info['cmdline'] or [])
                        if any(pattern in cmdline for pattern in patterns):
                            found = True
                            count += 1
                            total_cpu += proc.cpu_percent()
                            total_memory += proc.memory_info().rss
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass

                if found:
                    PROCESS_COUNT.labels(process_name=name).set(count)
                    PROCESS_CPU.labels(process_name=name).set(total_cpu)
                    PROCESS_MEMORY.labels(process_name=name).set(total_memory)

                    # 检查进程重启
                    if name not in process_states or process_states[name] != count:
                        PROCESS_RESTARTS.labels(process_name=name).inc()
                    process_states[name] = count
                else:
                    PROCESS_COUNT.labels(process_name=name).set(0)
                    PROCESS_CPU.labels(process_name=name).set(0)
                    PROCESS_MEMORY.labels(process_name=name).set(0)

            time.sleep(10)

        except Exception as e:
            logger.error(f"监控错误: {e}")
            time.sleep(10)

if __name__ == "__main__":
    # 启动HTTP服务器
    start_http_server(9101)

    # 开始监控
    logger.info("进程监控已启动，监听端口9101")
    monitor_processes()
EOF

    chmod +x scripts/monitoring/process_monitor.py

    # 创建systemd服务
    sudo tee /etc/systemd/system/process-monitor.service > /dev/null <<EOF
[Unit]
Description=Process Monitor
After=network.target

[Service]
Type=simple
User=monitoring
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/scripts/monitoring/process_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 创建用户
    sudo useradd --no-create-home --shell /bin/false monitoring || true

    # 启动服务
    sudo systemctl daemon-reload
    sudo systemctl enable process-monitor
    sudo systemctl start process-monitor

    log_info "进程监控已配置并启动"
}

# 配置日志监控
setup_log_monitoring() {
    log_step "配置日志监控..."

    # 创建日志监控脚本
    cat > scripts/monitoring/log_monitor.py <<'EOF'
#!/usr/bin/env python3
"""
日志监控脚本
监控日志文件并生成指标
"""

import re
import time
from prometheus_client import start_http_server, Counter, Histogram
import logging
from pathlib import Path
import tailer

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义指标
LOG_ERRORS = Counter('log_errors_total', 'Number of errors in logs', ['service'])
LOG_WARNINGS = Counter('log_warnings_total', 'Number of warnings in logs', ['service'])
LOG_REQUESTS = Counter('log_requests_total', 'Number of requests', ['service', 'method', 'status'])
LOG_DURATION = Histogram('log_request_duration_seconds', 'Request duration', ['service'])

# 日志文件路径
LOG_FILES = {
    'api': 'logs/api/app.log',
    'celery': 'logs/celery/celery.log',
    'nginx': '/var/log/nginx/access.log',
}

# 日志模式
PATTERNS = {
    'error': re.compile(r'ERROR'),
    'warning': re.compile(r'WARNING'),
    'request': re.compile(r'(\w+)\s+([A-Z]+)\s+(/\S+)\s+(\d+)\s+(\d+\.\d+)'),
}

def monitor_logs():
    """监控日志"""
    log_positions = {}

    while True:
        try:
            for service, log_file in LOG_FILES.items():
                path = Path(log_file)

                if not path.exists():
                    continue

                # 获取文件大小
                current_size = path.stat().st_size

                # 检查文件是否被轮转
                if service in log_positions and log_positions[service] > current_size:
                    # 文件被轮转，从头开始读
                    log_positions[service] = 0

                # 记录当前位置
                if service not in log_positions:
                    log_positions[service] = current_size

                # 读取新行
                with open(path, 'r') as f:
                    f.seek(log_positions[service])
                    lines = f.readlines()
                    log_positions[service] = f.tell()

                # 处理每行
                for line in lines:
                    # 错误日志
                    if PATTERNS['error'].search(line):
                        LOG_ERRORS.labels(service=service).inc()

                    # 警告日志
                    if PATTERNS['warning'].search(line):
                        LOG_WARNINGS.labels(service=service).inc()

                    # 请求日志
                    match = PATTERNS['request'].search(line)
                    if match:
                        method, status, path, _, duration = match.groups()
                        LOG_REQUESTS.labels(service=service, method=method, status=status).inc()
                        LOG_DURATION.labels(service=service).observe(float(duration))

            time.sleep(5)

        except Exception as e:
            logger.error(f"日志监控错误: {e}")
            time.sleep(5)

if __name__ == "__main__":
    # 启动HTTP服务器
    start_http_server(9102)

    # 开始监控
    logger.info("日志监控已启动，监听端口9102")
    monitor_logs()
EOF

    chmod +x scripts/monitoring/log_monitor.py

    # 创建systemd服务
    sudo tee /etc/systemd/system/log-monitor.service > /dev/null <<EOF
[Unit]
Description=Log Monitor
After=network.target

[Service]
Type=simple
User=monitoring
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/scripts/monitoring/log_monitor.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 启动服务
    sudo systemctl daemon-reload
    sudo systemctl enable log-monitor
    sudo systemctl start log-monitor

    log_info "日志监控已配置并启动"
}

# 配置健康检查
setup_health_checks() {
    log_step "配置健康检查..."

    # 创建健康检查脚本
    cat > scripts/monitoring/health_check.py <<'EOF'
#!/usr/bin/env python3
"""
健康检查脚本
检查所有服务健康状态并生成指标
"""

import asyncio
import aiohttp
import time
from prometheus_client import start_http_server, Gauge
import logging
from datetime import datetime

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 定义指标
HEALTH_STATUS = Gauge('service_health_status', 'Service health status', ['service', 'instance'])
HEALTH_CHECK_DURATION = Gauge('health_check_duration_seconds', 'Health check duration', ['service'])

# 服务端点
SERVICES = {
    'api': 'http://localhost:8000/api/health',
    'prometheus': 'http://localhost:9090/-/healthy',
    'grafana': 'http://localhost:3000/api/health',
    'alertmanager': 'http://localhost:9093/-/healthy',
    'redis': 'redis://localhost:6379',
}

async def check_http_service(session, name, url):
    """检查HTTP服务"""
    start_time = time.time()
    try:
        async with session.get(url, timeout=5) as response:
            status = 1 if response.status == 200 else 0
            HEALTH_STATUS.labels(service=name, instance='localhost').set(status)
    except Exception as e:
        logger.error(f"{name} 健康检查失败: {e}")
        HEALTH_STATUS.labels(service=name, instance='localhost').set(0)
    finally:
        HEALTH_CHECK_DURATION.labels(service=name).set(time.time() - start_time)

async def check_redis():
    """检查Redis"""
    import redis
    start_time = time.time()
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        HEALTH_STATUS.labels(service='redis', instance='localhost').set(1)
    except Exception as e:
        logger.error(f"Redis 健康检查失败: {e}")
        HEALTH_STATUS.labels(service='redis', instance='localhost').set(0)
    finally:
        HEALTH_CHECK_DURATION.labels(service='redis').set(time.time() - start_time)

async def monitor_health():
    """监控健康状态"""
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                # 检查HTTP服务
                tasks = []
                for name, url in SERVICES.items():
                    if url.startswith('http'):
                        tasks.append(check_http_service(session, name, url))

                # 检查Redis
                tasks.append(check_redis())

                await asyncio.gather(*tasks)

                # 每30秒检查一次
                await asyncio.sleep(30)

            except Exception as e:
                logger.error(f"健康检查错误: {e}")
                await asyncio.sleep(30)

if __name__ == "__main__":
    # 启动HTTP服务器
    start_http_server(9103)

    # 开始监控
    logger.info("健康监控已启动，监听端口9103")
    asyncio.run(monitor_health())
EOF

    chmod +x scripts/monitoring/health_check.py

    # 创建systemd服务
    sudo tee /etc/systemd/system/health-monitor.service > /dev/null <<EOF
[Unit]
Description=Health Monitor
After=network.target

[Service]
Type=simple
User=monitoring
WorkingDirectory=$(pwd)
ExecStart=$(pwd)/scripts/monitoring/health_check.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    # 启动服务
    sudo systemctl daemon-reload
    sudo systemctl enable health-monitor
    sudo systemctl start health-monitor

    log_info "健康监控已配置并启动"
}

# 测试告警
test_alerts() {
    log_step "测试告警系统..."

    # 创建测试脚本
    cat > scripts/monitoring/test_alerts.py <<'EOF'
#!/usr/bin/env python3
"""
测试告警系统
"""

import requests
import time

def test_prometheus_alerts():
    """测试Prometheus告警"""
    print("测试Prometheus告警规则...")

    # 查询当前告警
    response = requests.get('http://localhost:9090/api/v1/alerts')
    if response.status_code == 200:
        alerts = response.json()
        print(f"当前活跃告警数: {len(alerts['data']['alerts'])}")
    else:
        print("无法获取告警信息")

def test_alertmanager():
    """测试Alertmanager"""
    print("测试Alertmanager...")

    # 检查Alertmanager状态
    response = requests.get('http://localhost:9093/api/v1/status')
    if response.status_code == 200:
        print("✓ Alertmanager运行正常")
    else:
        print("✗ Alertmanager无法访问")

if __name__ == "__main__":
    test_prometheus_alerts()
    test_alertmanager()
EOF

    chmod +x scripts/monitoring/test_alerts.py

    # 运行测试
    python3 scripts/monitoring/test_alerts.py

    log_info "告警系统测试完成"
}

# 创建监控仪表板
create_monitoring_dashboard() {
    log_step "创建监控仪表板..."

    # 创建系统概览仪表板
    cat > monitoring/production/dashboards/system-overview.json <<'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Production System Overview",
    "tags": ["production", "system"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Service Status",
        "type": "stat",
        "targets": [
          {
            "expr": "up{job=~\"football-prediction|postgres|redis|nginx\"}",
            "legendFormat": "{{ job }}"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "green", "value": 1}
              ]
            }
          }
        },
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
      },
      {
        "id": 2,
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{ method }} {{ endpoint }}"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          },
          {
            "expr": "histogram_quantile(0.50, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "50th percentile"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
      },
      {
        "id": 4,
        "title": "Error Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
      }
    ],
    "time": {"from": "now-1h", "to": "now"},
    "refresh": "30s"
  }
}
EOF

    log_info "监控仪表板已创建"
}

# 主函数
main() {
    echo ""
    echo "=========================================="
    echo "配置生产环境监控系统"
    echo "=========================================="
    echo ""

    # 检查是否为root用户
    if [[ $EUID -eq 0 ]]; then
        log_error "请不要以root用户运行此脚本"
        exit 1
    fi

    # 检查必要工具
    for tool in wget tar systemctl; do
        if ! command -v "$tool" &> /dev/null; then
            log_error "缺少必要工具: $tool"
            exit 1
        fi
    done

    # 执行配置步骤
    create_directories
    setup_prometheus_rules
    setup_alertmanager
    create_alert_templates
    setup_node_exporter
    setup_process_monitoring
    setup_log_monitoring
    setup_health_checks
    create_monitoring_dashboard
    test_alerts

    echo ""
    echo "=========================================="
    echo "生产环境监控配置完成！"
    echo "=========================================="
    echo ""
    echo "访问地址："
    echo "  • Prometheus:   http://localhost:9090"
    echo "  • Grafana:      http://localhost:3000"
    echo "  • Alertmanager: http://localhost:9093"
    echo ""
    echo "监控指标："
    echo "  • Node Exporter: http://localhost:9100/metrics"
    echo "  • Process Monitor: http://localhost:9101/metrics"
    echo "  • Log Monitor:    http://localhost:9102/metrics"
    echo "  • Health Monitor: http://localhost:9103/metrics"
    echo ""
    echo "管理命令："
    echo "  • 查看告警: curl $ALERTMANAGER_URL/api/v1/alerts"
    echo "  • 查看规则: curl $PROMETHEUS_URL/api/v1/rules"
    echo ""
    echo "服务状态："
    sudo systemctl status node-exporter process-monitor log-monitor health-monitor
}

# 执行主函数
main "$@"
