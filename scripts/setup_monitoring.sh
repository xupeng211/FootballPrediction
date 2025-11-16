#!/bin/bash

# Monitoring Stack Setup Script for Football Prediction System
# Author: Claude Code
# Version: 1.0
# Purpose: Setup complete monitoring infrastructure

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.monitoring.yml"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "[$timestamp] [$level] $message"
}

log_info() { log "INFO" "$@"; }
log_success() { log -e "${GREEN}[SUCCESS]${NC} "$@"; }
log_warning() { log -e "${YELLOW}[WARNING]${NC} "$@"; }
log_error() { log -e "${RED}[ERROR]${NC} "$@"; }

# Show usage
show_usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Options:
    -h, --help              Show this help message
    --prometheus-only       Setup only Prometheus
    --grafana-only          Setup only Grafana
    --alertmanager-only     Setup only Alertmanager
    --elk-only             Setup only ELK stack
    --all                   Setup all monitoring components (default)
    --dry-run               Show what would be done without executing
    --clean                 Remove existing monitoring setup

Examples:
    $0                      # Setup all monitoring components
    $0 --prometheus-only   # Setup only Prometheus
    $0 --elk-only         # Setup ELK stack
    $0 --clean             # Remove monitoring setup

EOF
}

# Parse command line arguments
SETUP_ALL=true
SETUP_PROMETHEUS=false
SETUP_GRAFANA=false
SETUP_ALERTMANAGER=false
SETUP_ELK=false
DRY_RUN=false
CLEANUP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_usage
            exit 0
            ;;
        --prometheus-only)
            SETUP_ALL=false
            SETUP_PROMETHEUS=true
            shift
            ;;
        --grafana-only)
            SETUP_ALL=false
            SETUP_GRAFANA=true
            shift
            ;;
        --alertmanager-only)
            SETUP_ALL=false
            SETUP_ALERTMANAGER=true
            shift
            ;;
        --elk-only)
            SETUP_ALL=false
            SETUP_ELK=true
            shift
            ;;
        --all)
            SETUP_ALL=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --clean)
            CLEANUP=true
            shift
            ;;
        -*)
            log_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
        *)
            log_error "Unknown argument: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check Docker availability
check_docker() {
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi

    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed or not in PATH"
        exit 1
    fi

    log_success "Docker and Docker Compose are available"
}

# Create directories
create_directories() {
    log_info "Creating monitoring directories..."

    local dirs=(
        "monitoring/prometheus/data"
        "monitoring/grafana/data"
        "monitoring/grafana/provisioning/datasources"
        "monitoring/grafana/provisioning/dashboards"
        "monitoring/alertmanager/data"
        "logging/elasticsearch/data"
        "logging/logstash/data"
        "logging/kibana/data"
        "monitoring/alertmanager/templates"
        "backups/monitoring"
    )

    for dir in "${dirs[@]}"; do
        if [[ "$DRY_RUN" == "false" ]]; then
            mkdir -p "$PROJECT_DIR/$dir"
            chmod 755 "$PROJECT_DIR/$dir"
            log_info "Created: $dir"
        else
            log_info "Would create: $dir"
        fi
    done
}

# Generate Docker Compose file
generate_docker_compose() {
    local compose_file="$PROJECT_DIR/docker-compose.monitoring.yml"

    log_info "Generating Docker Compose configuration: $compose_file"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would generate: $compose_file"
        return
    fi

    cat > "$compose_file" << 'EOF'
version: '3.8'

services:
  # Prometheus
  prometheus:
    image: prom/prometheus:v2.45.0
    container_name: football-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitoring/prometheus/data:/prometheus
      - ./monitoring/alert-rules:/etc/prometheus/rules
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - alertmanager

  # Alertmanager
  alertmanager:
    image: prom/alertmanager:v0.25.0
    container_name: football-alertmanager
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml
      - ./monitoring/alertmanager/data:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
      - '--web.external-url=http://localhost:9093'
    networks:
      - monitoring
    restart: unless-stopped

  # Grafana
  grafana:
    image: grafana/grafana:10.0.0
    container_name: football-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
      - GF_USERS_ALLOW_SIGN_UP=false
      - GF_INSTALL_PLUGINS=grafana-clock-panel,grafana-simple-json-datasource
    volumes:
      - ./monitoring/grafana/data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - ./monitoring/grafana/dashboards:/var/lib/grafana/dashboards
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - prometheus

  # Node Exporter
  node-exporter:
    image: prom/node-exporter:v1.6.0
    container_name: football-node-exporter
    ports:
      - "9100:9100"
    command:
      - '--path.rootfs=/host'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /:/host:ro,rslave
    networks:
      - monitoring
    restart: unless-stopped

  # PostgreSQL Exporter
  postgres-exporter:
    image: prometheuscommunity/postgres-exporter:v0.12.0
    container_name: football-postgres-exporter
    ports:
      - "9187:9187"
    environment:
      - DATA_SOURCE_NAME=postgresql://postgres:password@postgres:5432/postgres?sslmode=disable
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - postgres

  # Redis Exporter
  redis-exporter:
    image: oliver006/redis_exporter:v1.45.0
    container_name: football-redis-exporter
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis://redis:6379
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - redis

  # Nginx Exporter
  nginx-exporter:
    image: nginx/nginx-prometheus-exporter:0.11.0
    container_name: football-nginx-exporter
    ports:
      - "9113:9113"
    command:
      - '--nginx.scrape-uri=http://nginx:8080/nginx_status'
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - nginx

  # Elasticsearch
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    container_name: football-elasticsearch
    environment:
      - discovery.type=single-node
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
      - xpack.security.enabled=false
      - xpack.security.enrollment.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - ./logging/elasticsearch/data:/usr/share/elasticsearch/data
    networks:
      - monitoring
    restart: unless-stopped

  # Logstash
  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    container_name: football-logstash
    ports:
      - "5044:5044"
    volumes:
      - ./logging/logstash/config:/usr/share/logstash/pipeline
      - ./logging/logstash/data:/usr/share/logstash/data
    environment:
      - "LS_JAVA_OPTS=-Xmx256m -Xms256m"
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - elasticsearch

  # Kibana
  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    container_name: football-kibana
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - elasticsearch

  # Filebeat
  filebeat:
    image: docker.elastic.co/beats/filebeat:8.8.0
    container_name: football-filebeat
    user: root
    volumes:
      - ./logging/filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/log:/var/log:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
    networks:
      - monitoring
    restart: unless-stopped
    depends_on:
      - logstash
      - elasticsearch

networks:
  monitoring:
    driver: bridge

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:
  elasticsearch_data:
  logstash_data:
  kibana_data:
EOF

    log_success "Docker Compose file generated: $compose_file"
}

# Generate Grafana datasources configuration
generate_grafana_datasources() {
    local datasources_dir="$PROJECT_DIR/monitoring/grafana/provisioning/datasources"
    local datasources_file="$datasources_dir/prometheus.yml"

    log_info "Generating Grafana datasources configuration..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would create: $datasources_file"
        return
    fi

    mkdir -p "$datasources_dir"

    cat > "$datasources_file" << 'EOF'
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
    jsonData:
      timeInterval: 15s
      queryTimeout: 60s
      httpMethod: POST
EOF

    log_success "Grafana datasources configuration created"
}

# Generate Grafana dashboard provisioning
generate_grafana_dashboards() {
    local dashboards_dir="$PROJECT_DIR/monitoring/grafana/provisioning/dashboards"
    local dashboards_file="$dashboards_dir/dashboard.yml"

    log_info "Generating Grafana dashboard provisioning..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would create: $dashboards_file"
        return
    fi

    mkdir -p "$dashboards_dir"

    cat > "$dashboards_file" << 'EOF'
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
      path: /var/lib/grafana/dashboards
EOF

    # Copy dashboard JSON files
    cp "$PROJECT_DIR/monitoring/grafana/dashboards/football-prediction-dashboard.json" \
       "$dashboards_dir/" 2>/dev/null || log_warning "Dashboard JSON file not found"

    log_success "Grafana dashboard provisioning created"
}

# Generate Logstash configuration
generate_logstash_config() {
    local config_dir="$PROJECT_DIR/logging/logstash/config"
    local pipeline_file="$config_dir/logstash.conf"

    log_info "Generating Logstash configuration..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would create: $pipeline_file"
        return
    fi

    mkdir -p "$config_dir"

    cat > "$pipeline_file" << 'EOF'
input {
  beats {
    port => 5044
  }
}

filter {
  # Parse application logs
  if [service] == "football-prediction" {
    grok {
      match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} \[%{LOGLEVEL:level}\] %{GREEDYDATA:message}" }
    }

    date {
      match => [ "timestamp", "yyyy-MM-dd HH:mm:ss", "ISO8601" ]
    }

    mutate {
      add_tag => ["application"]
    }
  }

  # Parse Nginx logs
  if [service] == "nginx" and [log_type] == "access" {
    mutate {
      convert => { "nginx_status" => "integer" }
      convert => { "body_bytes_sent" => "integer" }
      add_field => { "response_time" => "%{request_time}f" }
    }

    mutate {
      add_tag => ["nginx", "access"]
    }
  }

  # Parse error logs
  if [log_type] == "error" {
    grok {
      match => { "message" => "%{TIMESTAMP_ISO8601:timestamp} \[%{LOGLEVEL:level}\] %{GREEDYDATA:message}" }
    }

    date {
      match => [ "timestamp", "yyyy-MM-dd HH:mm:ss", "ISO8601" ]
    }

    mutate {
      add_tag => ["error"]
    }
  }

  # Add environment and service fields
  mutate {
    add_field => { "environment" => "%{[environment]}" }
    add_field => { "service" => "%{[service]}" }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "football-prediction-%{+YYYY.MM.dd}"
  }
}
EOF

    log_success "Logstash configuration created"
}

# Start monitoring services
start_services() {
    log_info "Starting monitoring services..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would start services with: docker-compose -f $COMPOSE_FILE up -d"
        return
    fi

    local services_to_start=()

    if [[ "$SETUP_ALL" == "true" || "$SETUP_PROMETHEUS" == "true" ]]; then
        services_to_start+=("prometheus alertmanager")
    fi

    if [[ "$SETUP_ALL" == "true" || "$SETUP_GRAFANA" == "true" ]]; then
        services_to_start+=("grafana")
    fi

    if [[ "$SETUP_ALL" == "true" ]]; then
        services_to_start+=("node-exporter postgres-exporter redis-exporter nginx-exporter")
    fi

    if [[ "$SETUP_ALL" == "true" || "$SETUP_ELK" == "true" ]]; then
        services_to_start+=("elasticsearch logstash kibana filebeat")
    fi

    if [[ ${#services_to_start[@]} -gt 0 ]]; then
        log_info "Starting services: ${services_to_start[*]}"
        docker-compose -f "$COMPOSE_FILE" up -d "${services_to_start[@]}"

        log_success "Monitoring services started"
        log_info "Access URLs:"
        log_info "  Prometheus: http://localhost:9090"
        log_info "  Grafana: http://localhost:3000 (admin/admin123)"
        log_info "  Alertmanager: http://localhost:9093"
        log_info "  Kibana: http://localhost:5601"
    else
        log_warning "No services selected to start"
    fi
}

# Stop monitoring services
stop_services() {
    log_info "Stopping monitoring services..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would stop services with: docker-compose -f $COMPOSE_FILE down"
        return
    fi

    docker-compose -f "$COMPOSE_FILE" down
    log_success "Monitoring services stopped"
}

# Clean up monitoring setup
cleanup() {
    log_info "Cleaning up monitoring setup..."

    if [[ "$DRY_RUN" == "true" ]]; then
        log_info "Would remove monitoring directories and files"
        return
    fi

    # Stop services first
    stop_services

    # Remove Docker volumes
    docker volume rm football-prediction_prometheus_data 2>/dev/null || true
    docker volume rm football-prediction_grafana_data 2>/dev/null || true
    docker volume rm football-prediction_alertmanager_data 2>/dev/null || true
    docker volume rm football-prediction_elasticsearch_data 2>/dev/null || true
    docker volume rm football-prediction_logstash_data 2>/dev/null || true
    docker volume rm football-prediction_kibana_data 2>/dev/null || true

    # Remove directories
    rm -rf "$PROJECT_DIR/monitoring"
    rm -rf "$PROJECT_DIR/logging"
    rm -f "$PROJECT_DIR/docker-compose.monitoring.yml"

    log_success "Monitoring setup cleaned up"
}

# Show status
show_status() {
    log_info "Checking monitoring services status..."

    if docker-compose -f "$COMPOSE_FILE" ps --services 2>/dev/null >/dev/null; then
        docker-compose -f "$COMPOSE_FILE" ps
    else
        log_warning "Monitoring services not running or configuration not found"
    fi
}

# Main execution
main() {
    echo "=========================================="
    echo "📊 Football Prediction Monitoring Setup"
    echo "=========================================="

    if [[ "$CLEANUP" == "true" ]]; then
        cleanup
        exit 0
    fi

    # Check prerequisites
    check_docker

    # Create directories
    create_directories

    # Generate configurations
    generate_docker_compose
    generate_grafana_datasources
    generate_grafana_dashboards
    generate_logstash_config

    # Start services
    start_services

    echo ""
    echo "=========================================="
    echo "✅ Monitoring Setup Completed"
    echo "=========================================="
    echo ""
    echo "Access Information:"
    echo "  Prometheus: http://localhost:9090"
    echo "  Grafana: http://localhost:3000 (admin/admin123)"
    echo "  Alertmanager: http://localhost:9093"
    echo "  Kibana: http://localhost:5601"
    echo ""
    echo "Commands:"
    echo "  Start:   $0"
    echo "  Stop:    $0 --clean"
    echo "  Status:  $0 --status"
    echo "  Cleanup: $0 --clean"
}

# Run main function
main
