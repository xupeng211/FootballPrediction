#!/bin/bash

# 监控系统设置脚本
# Monitoring Setup Script

set -e

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

# 生成Prometheus配置
generate_prometheus_config() {
    log_info "生成Prometheus配置..."

    mkdir -p docker/prometheus

    cat > docker/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093

scrape_configs:
  # 应用程序监控
  - job_name: 'football-prediction-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s

  # Prometheus自身监控
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Node Exporter (系统监控)
  - job_name: 'node-exporter'
    static_configs:
      - targets: ['node-exporter:9100']

  # Redis监控
  - job_name: 'redis-exporter'
    static_configs:
      - targets: ['redis-exporter:9121']

  # PostgreSQL监控
  - job_name: 'postgres-exporter'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Nginx监控
  - job_name: 'nginx-exporter'
    static_configs:
      - targets: ['nginx-exporter:9113']

  # Docker监控
  - job_name: 'cadvisor'
    static_configs:
      - targets: ['cadvisor:8080']
EOF

    log_success "Prometheus配置生成完成"
}

# 生成告警规则
generate_alert_rules() {
    log_info "生成Prometheus告警规则..."

    cat > docker/prometheus/alert_rules.yml << 'EOF'
groups:
  - name: football_prediction_alerts
    rules:
      # 应用程序可用性告警
      - alert: ApplicationDown
        expr: up{job="football-prediction-app"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Football Prediction应用程序已宕机"
          description: "{{ $labels.instance }} 应用程序已宕机超过1分钟"

      # 高错误率告警
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "应用程序错误率过高"
          description: "5xx错误率超过10%: {{ $value }}"

      # 高响应时间告警
      - alert: HighResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "应用程序响应时间过长"
          description: "95%分位响应时间超过2秒: {{ $value }}秒"

      # CPU使用率告警
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "CPU使用率过高"
          description: "{{ $labels.instance }} CPU使用率超过80%: {{ $value }}%"

      # 内存使用率告警
      - alert: HighMemoryUsage
        expr: (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "内存使用率过高"
          description: "{{ $labels.instance }} 内存使用率超过85%: {{ $value }}%"

      # 磁盘空间告警
      - alert: LowDiskSpace
        expr: (node_filesystem_avail_bytes{fstype!="tmpfs"} / node_filesystem_size_bytes{fstype!="tmpfs"}) * 100 < 10
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "磁盘空间不足"
          description: "{{ $labels.instance }} 磁盘剩余空间少于10%: {{ $value }}%"

      # Redis连接数告警
      - alert: RedisHighConnections
        expr: redis_connected_clients > 100
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Redis连接数过高"
          description: "Redis连接数: {{ $value }}"

      # 数据库连接告警
      - alert: DatabaseDown
        expr: up{job="postgres-exporter"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "数据库连接失败"
          description: "PostgreSQL数据库连接失败"

      # 数据库连接数告警
      - alert: DatabaseHighConnections
        expr: pg_stat_database_numbackends > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "数据库连接数过高"
          description: "PostgreSQL连接数: {{ $value }}"
EOF

    log_success "告警规则生成完成"
}

# 生成Grafana数据源配置
generate_grafana_datasources() {
    log_info "生成Grafana数据源配置..."

    mkdir -p docker/grafana/provisioning/datasources

    cat > docker/grafana/provisioning/datasources/prometheus.yml << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: true
EOF

    log_success "Grafana数据源配置生成完成"
}

# 生成Grafana仪表板配置
generate_grafana_dashboards() {
    log_info "生成Grafana仪表板配置..."

    mkdir -p docker/grafana/provisioning/dashboards

    cat > docker/grafana/provisioning/dashboards/dashboards.yml << 'EOF'
apiVersion: 1

providers:
  - name: 'default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
EOF

    # 创建应用监控仪表板
    mkdir -p docker/grafana/dashboards

    cat > docker/grafana/dashboards/football-prediction-overview.json << 'EOF'
{
  "dashboard": {
    "id": null,
    "title": "Football Prediction Overview",
    "tags": ["football-prediction"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "请求率",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 0,
          "y": 0
        }
      },
      {
        "id": 2,
        "title": "响应时间",
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
        "gridPos": {
          "h": 8,
          "w": 12,
          "x": 12,
          "y": 0
        }
      },
      {
        "id": 3,
        "title": "错误率",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m]) * 100",
            "legendFormat": "Error Rate %"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 6,
          "x": 0,
          "y": 8
        }
      },
      {
        "id": 4,
        "title": "活跃连接",
        "type": "singlestat",
        "targets": [
          {
            "expr": "http_requests_active",
            "legendFormat": "Active Connections"
          }
        ],
        "gridPos": {
          "h": 8,
          "w": 6,
          "x": 6,
          "y": 8
        }
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "5s"
  }
}
EOF

    log_success "Grafana仪表板配置生成完成"
}

# 生成Loki配置
generate_loki_config() {
    log_info "生成Loki配置..."

    mkdir -p docker/loki

    cat > docker/loki/local-config.yaml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096

ingester:
  lifecycler:
    address: 127.0.0.1
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
  chunk_idle_period: 1h
  max_chunk_age: 1h
  chunk_target_size: 1048576
  chunk_retain_period: 30s
  max_transfer_retries: 0

schema_config:
  configs:
    - from: 2020-10-24
      store: boltdb-shipper
      object_store: filesystem
      schema: v11
      index:
        prefix: index_
        period: 24h

storage_config:
  boltdb_shipper:
    active_index_directory: /loki/boltdb-shipper-active
    cache_location: /loki/boltdb-shipper-cache
    shared_store: filesystem
  filesystem:
    directory: /loki/chunks

limits_config:
  enforce_metric_name: false
  reject_old_samples: true
  reject_old_samples_max_age: 168h

chunk_store_config:
  max_look_back_period: 0s

table_manager:
  retention_deletes_enabled: false
  retention_period: 0s
EOF

    log_success "Loki配置生成完成"
}

# 生成AlertManager配置
generate_alertmanager_config() {
    log_info "生成AlertManager配置..."

    mkdir -p docker/alertmanager

    cat > docker/alertmanager/alertmanager.yml << 'EOF'
global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@football-prediction.com'
  smtp_require_tls: false

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    email_configs:
      - to: 'admin@football-prediction.com'
        subject: '[Football Prediction] {{ .GroupLabels.alertname }} 告警'
        body: |
          {{ range .Alerts }}
          告警: {{ .Annotations.summary }}
          描述: {{ .Annotations.description }}
          时间: {{ .StartsAt }}
          {{ end }}

    # Slack配置（需要配置Webhook URL）
    # slack_configs:
    #   - api_url: 'YOUR_SLACK_WEBHOOK_URL'
    #     channel: '#alerts'
    #     title: 'Football Prediction Alert'
    #     text: '{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
EOF

    log_success "AlertManager配置生成完成"
}

# 创建监控Docker Compose文件
create_monitoring_compose() {
    log_info "创建监控服务Docker Compose配置..."

    cat > docker-compose.monitoring.yml << 'EOF'
version: '3.8'

services:
  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    container_name: football-prediction-prometheus
    restart: unless-stopped
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    volumes:
      - ./docker/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./docker/prometheus/alert_rules.yml:/etc/prometheus/alert_rules.yml:ro
      - prometheus_data:/prometheus
    ports:
      - "9090:9090"
    networks:
      - app-network
    depends_on:
      - node-exporter
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  # AlertManager
  alertmanager:
    image: prom/alertmanager:latest
    container_name: football-prediction-alertmanager
    restart: unless-stopped
    volumes:
      - ./docker/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data:/alertmanager
    ports:
      - "9093:9093"
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.25'

  # Grafana
  grafana:
    image: grafana/grafana:latest
    container_name: football-prediction-grafana
    restart: unless-stopped
    environment:
      - GF_SECURITY_ADMIN_USER=${GRAFANA_USER:-admin}
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./docker/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./docker/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    ports:
      - "3000:3000"
    networks:
      - app-network
    depends_on:
      - prometheus
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

  # Node Exporter (系统监控)
  node-exporter:
    image: prom/node-exporter:latest
    container_name: football-prediction-node-exporter
    restart: unless-stopped
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    ports:
      - "9100:9100"
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 128M
          cpus: '0.1'

  # Redis Exporter
  redis-exporter:
    image: oliver006/redis_exporter:latest
    container_name: football-prediction-redis-exporter
    restart: unless-stopped
    environment:
      - REDIS_ADDR=redis://redis:6379
      - REDIS_PASSWORD=${REDIS_PASSWORD}
    ports:
      - "9121:9121"
    networks:
      - app-network
    depends_on:
      - redis
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'

  # Postgres Exporter
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:latest
    container_name: football-prediction-postgres-exporter
    restart: unless-stopped
    environment:
      - DATA_SOURCE_NAME=postgresql://postgres:${POSTGRES_PASSWORD}@db:5432/football_prediction?sslmode=disable
    ports:
      - "9187:9187"
    networks:
      - app-network
    depends_on:
      - db
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'

  # Nginx Exporter
  nginx-exporter:
    image: nginx/nginx-prometheus-exporter:latest
    container_name: football-prediction-nginx-exporter
    restart: unless-stopped
    command:
      - '-nginx.scrape-uri=http://nginx:80/metrics'
    ports:
      - "9113:9113"
    networks:
      - app-network
    depends_on:
      - nginx
    deploy:
      resources:
        limits:
          memory: 64M
          cpus: '0.1'

  # cAdvisor (容器监控)
  cadvisor:
    image: gcr.io/cadvisor/cadvisor:latest
    container_name: football-prediction-cadvisor
    restart: unless-stopped
    volumes:
      - /:/rootfs:ro
      - /var/run:/var/run:ro
      - /sys:/sys:ro
      - /var/lib/docker/:/var/lib/docker:ro
      - /dev/disk/:/dev/disk:ro
    ports:
      - "8080:8080"
    networks:
      - app-network
    privileged: true
    devices:
      - /dev/kmsg
    deploy:
      resources:
        limits:
          memory: 256M
          cpus: '0.5'

  # Loki (日志聚合)
  loki:
    image: grafana/loki:latest
    container_name: football-prediction-loki
    restart: unless-stopped
    command: -config.file=/etc/loki/local-config.yaml
    volumes:
      - ./docker/loki/local-config.yaml:/etc/loki/local-config.yaml:ro
      - loki_data:/loki
    ports:
      - "3100:3100"
    networks:
      - app-network
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'

volumes:
  prometheus_data:
    driver: local
  alertmanager_data:
    driver: local
  grafana_data:
    driver: local
  loki_data:
    driver: local

networks:
  app-network:
    external: true
EOF

    log_success "监控服务Docker Compose配置生成完成"
}

# 验证监控配置
verify_monitoring_setup() {
    log_info "验证监控配置..."

    local errors=0

    # 检查配置文件
    local config_files=(
        "docker/prometheus/prometheus.yml"
        "docker/prometheus/alert_rules.yml"
        "docker/grafana/provisioning/datasources/prometheus.yml"
        "docker/loki/local-config.yaml"
        "docker-compose.monitoring.yml"
    )

    for file in "${config_files[@]}"; do
        if [[ -f "$file" ]]; then
            log_success "监控配置文件存在: $file"
        else
            log_error "监控配置文件缺失: $file"
            ((errors++))
        fi
    done

    if [[ $errors -eq 0 ]]; then
        log_success "监控配置验证通过"
        return 0
    else
        log_error "监控配置验证失败，发现 $errors 个问题"
        return 1
    fi
}

# 显示监控设置信息
show_monitoring_info() {
    log_success "监控系统设置完成！"
    echo
    echo "监控服务访问地址："
    echo "Prometheus: http://localhost:9090"
    echo "Grafana: http://localhost:3000 (admin/admin123)"
    echo "AlertManager: http://localhost:9093"
    echo "Loki: http://localhost:3100"
    echo "cAdvisor: http://localhost:8080"
    echo
    echo "启动监控服务："
    echo "docker-compose -f docker-compose.monitoring.yml up -d"
    echo
    echo "停止监控服务："
    echo "docker-compose -f docker-compose.monitoring.yml down"
    echo
    echo "配置文件位置："
    echo "Prometheus配置: docker/prometheus/"
    echo "Grafana配置: docker/grafana/"
    echo "Loki配置: docker/loki/"
    echo "AlertManager配置: docker/alertmanager/"
}

# 主函数
main() {
    log_info "开始设置监控系统..."

    # 检查是否为主应用网络
    if ! docker network ls | grep -q app-network; then
        log_warning "主应用网络不存在，请先启动主应用"
    fi

    # 生成配置文件
    generate_prometheus_config
    generate_alert_rules
    generate_grafana_datasources
    generate_grafana_dashboards
    generate_loki_config
    generate_alertmanager_config

    # 创建Docker Compose文件
    create_monitoring_compose

    # 验证配置
    if verify_monitoring_setup; then
        show_monitoring_info
    else
        log_error "监控系统设置失败，请检查错误信息"
        exit 1
    fi
}

# 脚本入口
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi