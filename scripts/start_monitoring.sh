#!/bin/bash
# 监控系统启动脚本
# Monitoring System Startup Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查Docker和Docker Compose
check_prerequisites() {
    log_info "检查先决条件..."

    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装或不在PATH中"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装或不在PATH中"
        exit 1
    fi

    log_success "先决条件检查通过"
}

# 创建必要的目录
create_directories() {
    log_info "创建监控目录结构..."

    mkdir -p monitoring/{prometheus/rules,grafana/{provisioning/{datasources,dashboards},dashboards},alertmanager/templates,loki,promtail}

    # 创建Prometheus规则目录中的其他规则文件
    if [ ! -f "monitoring/prometheus/rules/node_exporter.yml" ]; then
        cat > monitoring/prometheus/rules/node_exporter.yml << 'EOF'
groups:
  - name: node_exporter
    rules:
      - alert: HighCPUUsage
        expr: 100 - (avg by(instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100) > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "CPU使用率过高"
          description: "实例 {{ $labels.instance }} CPU使用率 {{ $value }}% 超过80%"
EOF
    fi

    if [ ! -f "monitoring/prometheus/rules/postgres_exporter.yml" ]; then
        cat > monitoring/prometheus/rules/postgres_exporter.yml << 'EOF'
groups:
  - name: postgres_exporter
    rules:
      - alert: PostgreSQLDown
        expr: pg_up == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "PostgreSQL数据库不可用"
          description: "PostgreSQL实例 {{ $labels.instance }} 不可用"
EOF
    fi

    log_success "目录结构创建完成"
}

# 创建配置文件
create_configs() {
    log_info "创建配置文件..."

    # 创建Loki配置
    if [ ! -f "monitoring/loki/loki.yml" ]; then
        cat > monitoring/loki/loki.yml << 'EOF'
auth_enabled: false

server:
  http_listen_port: 3100

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
    fi

    # 创建Promtail配置
    if [ ! -f "monitoring/promtail/promtail.yml" ]; then
        cat > monitoring/promtail/promtail.yml << 'EOF'
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push

scrape_configs:
  - job_name: containers
    static_configs:
      - targets:
          - localhost
        labels:
          job: containerlogs
          __path__: /var/lib/docker/containers/*/*log
    pipeline_stages:
      - json:
          expressions:
            output: log
            stream: stream
            attrs:
      - json:
          expressions:
            tag:
          source: attrs
      - regex:
          expression: (?P<container_name>(?:[^|]*))\|
          source: tag
      - timestamp:
          format: RFC3339Nano
          source: time
      - labels:
          stream:
          container_name:
      - output:
          source: output
EOF
    fi

    log_success "配置文件创建完成"
}

# 检查网络
check_network() {
    log_info "检查Docker网络..."

    if ! docker network ls | grep -q "football-network"; then
        log_warning "football-network 不存在，创建网络..."
        docker network create football-network
    fi

    log_success "网络检查完成"
}

# 启动监控服务
start_monitoring() {
    log_info "启动监控系统..."

    cd monitoring

    # 启动监控栈
    docker-compose -f docker-compose.monitoring.yml up -d

    log_success "监控系统启动完成"
}

# 等待服务就绪
wait_for_services() {
    log_info "等待服务就绪..."

    # 等待Prometheus
    log_info "等待 Prometheus 启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:9090/-/healthy > /dev/null; then
            log_success "Prometheus 已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done

    if [ $timeout -le 0 ]; then
        log_warning "Prometheus 启动超时"
    fi

    # 等待Grafana
    log_info "等待 Grafana 启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:3000/api/health > /dev/null; then
            log_success "Grafana 已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done

    if [ $timeout -le 0 ]; then
        log_warning "Grafana 启动超时"
    fi

    # 等待AlertManager
    log_info "等待 AlertManager 启动..."
    timeout=60
    while [ $timeout -gt 0 ]; do
        if curl -s http://localhost:9093/-/healthy > /dev/null; then
            log_success "AlertManager 已就绪"
            break
        fi
        sleep 2
        timeout=$((timeout-2))
    done

    if [ $timeout -le 0 ]; then
        log_warning "AlertManager 启动超时"
    fi
}

# 显示访问信息
show_access_info() {
    log_success "监控系统启动完成！"
    echo ""
    echo "访问地址："
    echo "  Prometheus: http://localhost:9090"
    echo "  Grafana:   http://localhost:3000 (admin/admin123)"
    echo "  AlertManager: http://localhost:9093"
    echo ""
    echo "其他服务："
    echo "  Node Exporter: http://localhost:9100/metrics"
    echo "  cAdvisor:     http://localhost:8080"
    echo ""
    echo "管理命令："
    echo "  查看状态: cd monitoring && docker-compose -f docker-compose.monitoring.yml ps"
    echo "  查看日志: cd monitoring && docker-compose -f docker-compose.monitoring.yml logs -f [service]"
    echo "  停止服务: cd monitoring && docker-compose -f docker-compose.monitoring.yml down"
    echo ""
}

# 主函数
main() {
    echo "========================================"
    echo "🚀 足球预测系统监控系统启动脚本"
    echo "========================================"
    echo ""

    check_prerequisites
    create_directories
    create_configs
    check_network
    start_monitoring
    wait_for_services
    show_access_info

    log_success "所有操作完成！"
}

# 处理信号
trap 'log_warning "脚本被中断"; exit 1' INT TERM

# 执行主函数
main "$@"