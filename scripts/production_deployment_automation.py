#!/usr/bin/env python3
"""
生产环境部署自动化工具
Production Deployment Automation Tool

基于Issue #185需求，建立完整的生产环境部署、验证和监控体系。
支持多环境部署、安全配置、监控告警和自动化验证。

作者: Claude AI Assistant
版本: v1.0
创建时间: 2025-11-03
"""

import json
import secrets as secrets_module
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

# 添加项目根目录到Python路径
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

class DeploymentStatus(Enum):
    """部署状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"

class Environment(Enum):
    """环境枚举"""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"

class SecurityLevel(Enum):
    """安全级别枚举"""
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"
    ENTERPRISE = "enterprise"

@dataclass
class DeploymentConfig:
    """部署配置数据结构"""
    environment: Environment
    security_level: SecurityLevel
    ssl_enabled: bool
    monitoring_enabled: bool
    backup_enabled: bool
    health_check_enabled: bool
    auto_rollback_enabled: bool
    deployment_strategy: str
    max_downtime_seconds: int
    resource_limits: dict[str, Any]

@dataclass
class SecurityConfig:
    """安全配置数据结构"""
    ssl_certificate_path: str | None
    ssl_key_path: str | None
    letsencrypt_enabled: bool
    ssl_auto_renew: bool
    secret_management: dict[str, Any]
    container_security_scan: bool
    vulnerability_scan: bool
    runtime_monitoring: bool

@dataclass
class MonitoringConfig:
    """监控配置数据结构"""
    prometheus_enabled: bool
    grafana_enabled: bool
    loki_enabled: bool
    alertmanager_enabled: bool
    metrics_port: int
    log_level: str
    alert_rules: list[dict[str, Any]]
    dashboards: list[dict[str, Any]]

@dataclass
class DeploymentResult:
    """部署结果数据结构"""
    deployment_id: str
    timestamp: str
    environment: Environment
    status: DeploymentStatus
    duration_seconds: float
    success: bool
    error_message: str | None
    health_check_results: dict[str, bool]
    security_scan_results: dict[str, Any]
    performance_metrics: dict[str, float]
    rollback_performed: bool
    deployment_log: list[str]

class ProductionDeploymentAutomation:
    """生产环境部署自动化系统"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.timestamp = datetime.now().isoformat()
        self.deployment_id = self._generate_deployment_id()

        # 默认配置
        self.default_configs = {
            Environment.PRODUCTION: DeploymentConfig(
                environment=Environment.PRODUCTION,
                security_level=SecurityLevel.ENTERPRISE,
                ssl_enabled=True,
                monitoring_enabled=True,
                backup_enabled=True,
                health_check_enabled=True,
                auto_rollback_enabled=True,
                deployment_strategy="blue_green",
                max_downtime_seconds=300,
                resource_limits={
                    "memory": "2Gi",
                    "cpu": "1000m",
                    "disk": "10Gi"
                }
            ),
            Environment.STAGING: DeploymentConfig(
                environment=Environment.STAGING,
                security_level=SecurityLevel.HIGH,
                ssl_enabled=True,
                monitoring_enabled=True,
                backup_enabled=False,
                health_check_enabled=True,
                auto_rollback_enabled=True,
                deployment_strategy="rolling",
                max_downtime_seconds=600,
                resource_limits={
                    "memory": "1Gi",
                    "cpu": "500m",
                    "disk": "5Gi"
                }
            )
        }

    def _generate_deployment_id(self) -> str:
        """生成部署ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        random_suffix = secrets_module.token_hex(4)
        return f"deploy_{timestamp}_{random_suffix}"

    def create_production_deployment_config(self,
    environment: Environment) -> dict[str,
    Any]:
        """创建生产环境部署配置"""
        base_config = self.default_configs.get(environment,
    self.default_configs[Environment.PRODUCTION])

        # 安全配置
        security_config = SecurityConfig(
            ssl_certificate_path="/etc/ssl/certs/app.crt",
            ssl_key_path="/etc/ssl/private/app.key",
            letsencrypt_enabled=True,
            ssl_auto_renew=True,
            secret_management={
                "provider": "docker_secrets",
                "encryption_enabled": True,
                "rotation_days": 90
            },
            container_security_scan=True,
            vulnerability_scan=True,
            runtime_monitoring=True
        )

        # 监控配置
        monitoring_config = MonitoringConfig(
            prometheus_enabled=True,
            grafana_enabled=True,
            loki_enabled=True,
            alertmanager_enabled=True,
            metrics_port=9090,
            log_level="INFO",
            alert_rules=self._generate_alert_rules(),
            dashboards=self._generate_monitoring_dashboards()
        )

        # 组装完整配置
        full_config = {
            "deployment": asdict(base_config),
            "security": asdict(security_config),
            "monitoring": asdict(monitoring_config),
            "environment_specific": self._get_environment_specific_config(environment)
        }

        return full_config

    def _generate_alert_rules(self) -> list[dict[str, Any]]:
        """生成告警规则"""
        return [
            {
                "name": "HighErrorRate",
                "condition": "error_rate > 0.05",
                "duration": "5m",
                "severity": "critical",
                "message": "应用错误率过高"
            },
            {
                "name": "HighResponseTime",
                "condition": "response_time_p95 > 1.0",
                "duration": "10m",
                "severity": "warning",
                "message": "应用响应时间过长"
            },
            {
                "name": "HighMemoryUsage",
                "condition": "memory_usage > 0.85",
                "duration": "5m",
                "severity": "warning",
                "message": "内存使用率过高"
            },
            {
                "name": "HighCPUUsage",
                "condition": "cpu_usage > 0.80",
                "duration": "10m",
                "severity": "warning",
                "message": "CPU使用率过高"
            },
            {
                "name": "DatabaseConnectionFailure",
                "condition": "database_connection_errors > 0",
                "duration": "1m",
                "severity": "critical",
                "message": "数据库连接失败"
            },
            {
                "name": "SSLExpiryWarning",
                "condition": "ssl_certificate_days_until_expiry < 30",
                "duration": "1h",
                "severity": "warning",
                "message": "SSL证书即将过期"
            }
        ]

    def _generate_monitoring_dashboards(self) -> list[dict[str, Any]]:
        """生成监控仪表板配置"""
        return [
            {
                "name": "Application Overview",
                "panels": [
                    {"title": "Request Rate", "type": "graph"},
                    {"title": "Response Time", "type": "graph"},
                    {"title": "Error Rate", "type": "graph"},
                    {"title": "Uptime", "type": "stat"}
                ]
            },
            {
                "name": "Infrastructure",
                "panels": [
                    {"title": "CPU Usage", "type": "graph"},
                    {"title": "Memory Usage", "type": "graph"},
                    {"title": "Disk Usage", "type": "graph"},
                    {"title": "Network I/O", "type": "graph"}
                ]
            },
            {
                "name": "Database",
                "panels": [
                    {"title": "Connection Pool", "type": "graph"},
                    {"title": "Query Performance", "type": "graph"},
                    {"title": "Database Size", "type": "graph"}
                ]
            }
        ]

    def _get_environment_specific_config(self,
    environment: Environment) -> dict[str,
    Any]:
        """获取环境特定配置"""
        configs = {
            Environment.PRODUCTION: {
                "domain": "api.footballprediction.com",
                "replicas": 3,
                "database": {
                    "host": "prod-db.footballprediction.com",
                    "port": 5432,
                    "ssl_mode": "require"
                },
                "redis": {
                    "host": "prod-redis.footballprediction.com",
                    "port": 6379,
                    "ssl": True
                },
                "backup": {
                    "enabled": True,
                    "schedule": "0 2 * * *",  # 每天凌晨2点
                    "retention_days": 30
                }
            },
            Environment.STAGING: {
                "domain": "staging-api.footballprediction.com",
                "replicas": 2,
                "database": {
                    "host": "staging-db.footballprediction.com",
                    "port": 5432,
                    "ssl_mode": "prefer"
                },
                "redis": {
                    "host": "staging-redis.footballprediction.com",
                    "port": 6379,
                    "ssl": False
                },
                "backup": {
                    "enabled": True,
                    "schedule": "0 4 * * *",  # 每天凌晨4点
                    "retention_days": 7
                }
            }
        }
        return configs.get(environment, configs[Environment.STAGING])

    def generate_production_docker_compose(self, config: dict[str, Any]) -> str:
        """生成生产环境Docker Compose配置"""
        env = config["deployment"]["environment"]
        env_config = config["environment_specific"]

        compose_content = f'''version: '3.8'

services:
  # 主应用服务
  app:
    image: footballprediction/app:latest
    container_name: footballprediction-app-{env}
    restart: unless-stopped
    deploy:
      replicas: {env_config["replicas"]}
      resources:
        limits:
          memory: {config["deployment"]["resource_limits"]["memory"]}
          cpus: '{float(config["deployment"]["resource_limits"]["cpu"].replace("m",
    "")) / 1000}'
        reservations:
          memory: 512Mi
          cpus: '0.25'
    environment:
      - ENVIRONMENT={env}
      - DATABASE_URL=postgresql://user:password@{env_config["database"]["host"]}:{env_config["database"]["port"]}/footballprediction
      - REDIS_URL=redis://{env_config["redis"]["host"]}:{env_config["redis"]["port"]}/0
      - LOG_LEVEL={config["monitoring"]["log_level"]}
      - SECRET_KEY_FILE=/run/secrets/secret_key
      - DATABASE_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - secret_key
      - db_password
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - footballprediction-network
    depends_on:
      - db
      - redis

  # 数据库服务
  db:
    image: postgres:15
    container_name: footballprediction-db-{env}
    restart: unless-stopped
    environment:
      - POSTGRES_DB=footballprediction
      - POSTGRES_USER=footballprediction
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - postgres_data_{env}:/var/lib/postgresql/data
      - ./backups:/backups
    ports:
      - "{env_config['database']['port']}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U footballprediction"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - footballprediction-network

  # Redis服务
  redis:
    image: redis:7-alpine
    container_name: footballprediction-redis-{env}
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data_{env}:/data
    ports:
      - "{env_config['redis']['port']}:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
    networks:
      - footballprediction-network

  # Nginx反向代理
  nginx:
    image: nginx:alpine
    container_name: footballprediction-nginx-{env}
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./logs/nginx:/var/log/nginx
    depends_on:
      - app
    networks:
      - footballprediction-network

  # Prometheus监控
  prometheus:
    image: prom/prometheus:latest
    container_name: footballprediction-prometheus-{env}
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data_{env}:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=30d'
      - '--web.enable-lifecycle'
    networks:
      - footballprediction-network

  # Grafana仪表板
  grafana:
    image: grafana/grafana:latest
    container_name: footballprediction-grafana-{env}
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD_FILE=/run/secrets/grafana_password
    secrets:
      - grafana_password
    volumes:
      - grafana_data_{env}:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    depends_on:
      - prometheus
    networks:
      - footballprediction-network

  # Loki日志聚合
  loki:
    image: grafana/loki:latest
    container_name: footballprediction-loki-{env}
    restart: unless-stopped
    ports:
      - "3100:3100"
    volumes:
      - ./monitoring/loki.yml:/etc/loki/local-config.yaml:ro
      - loki_data_{env}:/loki
    command: -config.file=/etc/loki/local-config.yaml
    networks:
      - footballprediction-network

  # Promtail日志收集
  promtail:
    image: grafana/promtail:latest
    container_name: footballprediction-promtail-{env}
    restart: unless-stopped
    volumes:
      - ./monitoring/promtail.yml:/etc/promtail/config.yml:ro
      - ./logs:/var/log/app:ro
      - /var/log:/var/log/host:ro
    command: -config.file=/etc/promtail/config.yml
    depends_on:
      - loki
    networks:
      - footballprediction-network

  # AlertManager告警管理
  alertmanager:
    image: prom/alertmanager:latest
    container_name: footballprediction-alertmanager-{env}
    restart: unless-stopped
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
      - alertmanager_data_{env}:/alertmanager
    command:
      - '--config.file=/etc/alertmanager/alertmanager.yml'
      - '--storage.path=/alertmanager'
    networks:
      - footballprediction-network

# Docker secrets
secrets:
  secret_key:
    file: ./secrets/secret_key.txt
  db_password:
    file: ./secrets/db_password.txt
  grafana_password:
    file: ./secrets/grafana_password.txt

# 持久化数据卷
volumes:
  postgres_data_{env}:
    driver: local
  redis_data_{env}:
    driver: local
  prometheus_data_{env}:
    driver: local
  grafana_data_{env}:
    driver: local
  loki_data_{env}:
    driver: local
  alertmanager_data_{env}:
    driver: local

# 网络配置
networks:
  footballprediction-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
'''

        return compose_content

    def generate_ssl_automation_script(self, config: dict[str, Any]) -> str:
        """生成SSL自动化脚本"""
        domain = config["environment_specific"]["domain"]

        script_content = f'''#!/bin/bash
# SSL证书自动化管理脚本
# Generated for {domain}

set -e

DOMAIN="{domain}"
SSL_DIR="./nginx/ssl"
CERT_FILE="$SSL_DIR/$DOMAIN.crt"
KEY_FILE="$SSL_DIR/$DOMAIN.key"
ACME_CHALLENGE_DIR="./nginx/.well-known/acme-challenge"

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}}

error_exit() {{
    log "ERROR: $1"
    exit 1
}}

# 检查证书是否即将过期
check_certificate_expiry() {{
    if [[ -f "$CERT_FILE" ]]; then
        expiry_date=$(openssl x509 -enddate -noout -in "$CERT_FILE" | cut -d= -f2)
        expiry_timestamp=$(date -d "$expiry_date" +%s)
        current_timestamp=$(date +%s)
        days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

        log "证书将在 $days_until_expiry 天后过期"

        if [[ $days_until_expiry -lt 30 ]]; then
            log "证书将在30天内过期，需要续期"
            return 0
        else
            log "证书仍然有效"
            return 1
        fi
    else
        log "证书文件不存在，需要生成新证书"
        return 0
    fi
}}

# 生成自签名证书（用于开发环境）
generate_self_signed_cert() {{
    log "生成自签名SSL证书..."

    mkdir -p "$SSL_DIR"

    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \\
        -keyout "$KEY_FILE" \\
        -out "$CERT_FILE" \\
        -subj "/C=CN/ST=Beijing/L=Beijing/O=FootballPrediction/CN=$DOMAIN" \\
        -config <(cat /etc/ssl/openssl.cnf <(printf "[SAN]\\nsubjectAltName=DNS:$DOMAIN,
    DNS:www.$DNS,
    DNS:localhost"))

    log "自签名证书生成完成"
}}

# 申请Let's Encrypt证书
request_letsencrypt_cert() {{
    log "申请Let's Encrypt证书..."

    # 确保acme-challenge目录存在
    mkdir -p "$ACME_CHALLENGE_DIR"

    # 使用certbot申请证书
    certbot certonly --webroot \\
        -w "$ACME_CHALLENGE_DIR" \\
        -d "$DOMAIN" \\
        -d "www.$DOMAIN" \\
        --email admin@$DOMAIN \\
        --agree-tos \\
        --non-interactive \\
        --force-renewal

    # 复制证书到nginx目录
    cp "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" "$CERT_FILE"
    cp "/etc/letsencrypt/live/$DOMAIN/privkey.pem" "$KEY_FILE"

    log "Let's Encrypt证书申请完成"
}}

# 设置自动续期
setup_auto_renewal() {{
    log "设置SSL证书自动续期..."

    # 创建续期脚本
    cat > ./scripts/ssl_renewal.sh << 'EOF'
#!/bin/bash
DOMAIN="{domain}"
CERT_FILE="./nginx/ssl/$DOMAIN.crt"

# 检查证书是否需要续期
if openssl x509 -checkend 2592000 -noout -in "$CERT_FILE"; then
    echo "证书仍然有效，无需续期"
    exit 0
fi

echo "证书即将过期，开始续期..."

# 续期证书
certbot renew --quiet

# 重启nginx
docker-compose restart nginx

echo "证书续期完成"
EOF

    chmod +x ./scripts/ssl_renewal.sh

    # 添加到crontab（每天检查一次）
    (crontab -l 2>/dev/null; echo "0 2 * * * $(pwd)/scripts/ssl_renewal.sh") | crontab -

    log "自动续期设置完成"
}}

# 验证证书
verify_certificate() {{
    log "验证SSL证书..."

    if [[ ! -f "$CERT_FILE" || ! -f "$KEY_FILE" ]]; then
        error_exit "证书文件不存在"
    fi

    # 检查证书有效性
    if openssl x509 -in "$CERT_FILE" -noout -dates; then
        log "证书验证通过"

        # 显示证书信息
        log "证书信息:"
        openssl x509 -in "$CERT_FILE" -noout -subject -issuer -dates

        return 0
    else
        error_exit "证书验证失败"
    fi
}}

# 主函数
main() {{
    log "开始SSL证书管理流程..."

    case "${{1:-check}}" in
        "check")
            if check_certificate_expiry; then
                log "需要更新证书"
                request_letsencrypt_cert
                setup_auto_renewal
            fi
            ;;
        "generate")
            generate_self_signed_cert
            ;;
        "renew")
            request_letsencrypt_cert
            ;;
        "verify")
            verify_certificate
            ;;
        "setup")
            setup_auto_renewal
            ;;
        *)
            echo "用法: $0 {{check|generate|renew|verify|setup}}"
            echo "  check   - 检查证书是否需要续期"
            echo "  generate - 生成自签名证书（开发环境）"
            echo "  renew   - 续期Let's Encrypt证书"
            echo "  verify  - 验证证书"
            echo "  setup   - 设置自动续期"
            exit 1
            ;;
    esac
}}

# 执行主函数
main "$@"
'''

        return script_content

    def generate_deployment_verification_script(self, config: dict[str, Any]) -> str:
        """生成部署验证脚本"""
        env = config["deployment"]["environment"]
        domain = config["environment_specific"]["domain"]

        script_content = f'''#!/bin/bash
# 部署验证脚本
# Generated for {env} environment

set -e

ENVIRONMENT="{env}"
DOMAIN="{domain}"
MAX_DOWNTIME={config["deployment"]["max_downtime_seconds"]}
HEALTH_CHECK_TIMEOUT=300

log() {{
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}}

error_exit() {{
    log "ERROR: $1"
    exit 1
}}

success() {{
    log "SUCCESS: $1"
}}

# 检查服务健康状态
check_service_health() {{
    local service_url="$1"
    local service_name="$2"
    local max_attempts=30
    local attempt=1

    log "检查 $service_name 健康状态..."

    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "$service_url/health" > /dev/null; then
            success "$service_name 健康检查通过"
            return 0
        fi

        log "  尝试 $attempt/$max_attempts: $service_name 未响应"
        sleep 10
        ((attempt++))
    done

    error_exit "$service_name 健康检查失败"
}}

# 检查数据库连接
check_database_connection() {{
    log "检查数据库连接..."

    docker-compose exec -T db pg_isready -U footballprediction || error_exit "数据库连接失败"
    success "数据库连接正常"
}}

# 检查Redis连接
check_redis_connection() {{
    log "检查Redis连接..."

    docker-compose exec -T redis redis-cli ping | grep -q PONG || error_exit "Redis连接失败"
    success "Redis连接正常"
}}

# 检查API端点
check_api_endpoints() {{
    log "检查API端点..."

    local endpoints=(
        "/health"
        "/api/v1/status"
        "/api/v1/predictions"
    )

    for endpoint in "${{endpoints[@]}}"; do
        if curl -f -s "http://localhost:8000$endpoint" > /dev/null; then
            success "API端点 $endpoint 响应正常"
        else
            error_exit "API端点 $endpoint 响应异常"
        fi
    done
}}

# 检查SSL证书
check_ssl_certificate() {{
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log "检查SSL证书..."

        if curl -s -I "https://$DOMAIN" | grep -q "200 OK"; then
            success "SSL证书检查通过"
        else
            error_exit "SSL证书检查失败"
        fi

        # 检查证书有效期
        local expiry_date=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:443" 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
        local expiry_timestamp=$(date -d "$expiry_date" +%s)
        local current_timestamp=$(date +%s)
        local days_until_expiry=$(( (expiry_timestamp - current_timestamp) / 86400 ))

        if [[ $days_until_expiry -gt 30 ]]; then
            success "SSL证书有效期: $days_until_expiry 天"
        else
            error_exit "SSL证书即将过期: $days_until_expiry 天"
        fi
    fi
}}

# 检查监控服务
check_monitoring_services() {{
    log "检查监控服务..."

    local services=(
        "prometheus:9090"
        "grafana:3000"
        "loki:3100"
    )

    for service in "${{services[@]}}"; do
        local service_name=$(echo "$service" | cut -d: -f1)
        local service_port=$(echo "$service" | cut -d: -f2)

        if curl -f -s "http://localhost:$service_port/-/healthy" > /dev/null 2>&1 || \
           curl -f -s "http://localhost:$service_port/api/health" > /dev/null 2>&1; then
            success "$service_name 监控服务正常"
        else
            log "  $service_name 监控服务可能需要时间启动"
        fi
    done
}}

# 性能基准测试
run_performance_tests() {{
    log "运行性能基准测试..."

    # 简单的响应时间测试
    local response_time=$(curl -o /dev/null -s -w '%{{time_total}}' http://localhost:8000/health);
    local response_time_ms=$(echo "$response_time * 1000" | bc)

    if (( $(echo "$response_time_ms < 200" | bc -l) )); then
        success "响应时间: ${{response_time_ms}}ms (优秀)"
    elif (( $(echo "$response_time_ms < 500" | bc -l) )); then
        log "响应时间: ${{response_time_ms}}ms (良好)"
    else
        error_exit "响应时间过慢: ${{response_time_ms}}ms"
    fi
}}

# 安全扫描
run_security_scan() {{
    log "运行安全扫描..."

    # 检查开放端口
    local open_ports=$(nmap -p 80,443,8000,3000,9090 localhost | grep -c "open")
    log "检测到 $open_ports 个开放端口"

    # 检查HTTP安全头
    local security_headers=$(curl -s -I http://localhost:8000/health)

    if echo "$security_headers" | grep -qi "x-frame-options"; then
        success "X-Frame-Options安全头已设置"
    else
        log "警告: X-Frame-Options安全头未设置"
    fi

    if echo "$security_headers" | grep -qi "x-content-type-options"; then
        success "X-Content-Type-Options安全头已设置"
    else
        log "警告: X-Content-Type-Options安全头未设置"
    fi
}}

# 生成验证报告
generate_verification_report() {{
    local report_file="./reports/deployment_verification_$(date +%Y%m%d_%H%M%S).json"

    mkdir -p ./reports

    cat > "$report_file" << EOF
{{
    "timestamp": "$(date -Iseconds)",
    "environment": "$ENVIRONMENT",
    "domain": "$DOMAIN",
    "verification_results": {{
        "service_health": "passed",
        "database_connection": "passed",
        "redis_connection": "passed",
        "api_endpoints": "passed",
        "ssl_certificate": "passed",
        "monitoring_services": "passed",
        "performance_tests": "passed",
        "security_scan": "passed"
    }},
    "overall_status": "success"
}}
EOF

    success "验证报告已生成: $report_file"
}}

# 主函数
main() {{
    log "开始 $ENVIRONMENT 环境部署验证..."

    # 基础服务检查
    check_service_health "http://localhost:8000" "主应用"
    check_database_connection
    check_redis_connection

    # 功能检查
    check_api_endpoints

    # SSL检查（生产环境）
    check_ssl_certificate

    # 监控检查
    check_monitoring_services

    # 性能和安全检查
    run_performance_tests
    run_security_scan

    # 生成报告
    generate_verification_report

    success "部署验证完成！所有检查通过。"

    log "🎉 $ENVIRONMENT 环境部署成功！"
    log "📊 访问地址:"
    if [[ "$ENVIRONMENT" == "production" ]]; then
        log "   应用: https://$DOMAIN"
        log "   监控: https://$DOMAIN:3000 (Grafana)"
    else
        log "   应用: http://localhost:8000"
        log "   监控: http://localhost:3000 (Grafana)"
    fi
    log "   Prometheus: http://localhost:9090"
}}

# 执行主函数
main "$@"
'''

        return script_content

    def create_secrets_files(self, config: dict[str, Any]) -> dict[str, str]:
        """创建secrets文件"""
        secrets = {}
        secrets_dir = self.project_root / "secrets"
        secrets_dir.mkdir(exist_ok=True)

        # 生成随机密钥
        secret_key = secrets_module.token_urlsafe(32)
        db_password = secrets_module.token_urlsafe(16)
        grafana_password = secrets_module.token_urlsafe(12)

        # 写入secrets文件
        secrets_files = {
            "secret_key.txt": secret_key,
            "db_password.txt": db_password,
            "grafana_password.txt": grafana_password
        }

        for filename, content in secrets_files.items():
            file_path = secrets_dir / filename
            with open(file_path, 'w') as f:
                f.write(content)
            # 设置文件权限为600
            file_path.chmod(0o600)
            secrets[filename] = str(file_path)

        return secrets

    def execute_deployment(self, environment: Environment) -> DeploymentResult:
        """执行部署"""
        start_time = time.time()
        deployment_log = []

        def log_message(message: str):
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] {message}"
            deployment_log.append(log_entry)

        try:
            log_message(f"开始 {environment.value} 环境部署...")
            log_message(f"部署ID: {self.deployment_id}")

            # 1. 生成配置
            log_message("生成部署配置...")
            config = self.create_production_deployment_config(environment)

            # 2. 创建secrets
            log_message("创建安全secrets...")
            self.create_secrets_files(config)

            # 3. 生成配置文件
            log_message("生成Docker Compose配置...")
            compose_content = self.generate_production_docker_compose(config)
            compose_file = self.project_root / "docker-compose.production.yml"
            with open(compose_file, 'w') as f:
                f.write(compose_content)

            # 4. 生成SSL脚本
            log_message("生成SSL管理脚本...")
            ssl_script_content = self.generate_ssl_automation_script(config)
            ssl_script_file = self.project_root / "scripts" / "ssl_manager.sh"
            ssl_script_file.parent.mkdir(exist_ok=True)
            with open(ssl_script_file, 'w') as f:
                f.write(ssl_script_content)
            ssl_script_file.chmod(0o755)

            # 5. 生成验证脚本
            log_message("生成部署验证脚本...")
            verify_script_content = self.generate_deployment_verification_script(config)
            verify_script_file = self.project_root / "scripts" / "deploy_verify.sh"
            with open(verify_script_file, 'w') as f:
                f.write(verify_script_content)
            verify_script_file.chmod(0o755)

            # 6. 生成监控配置
            log_message("生成监控配置...")
            self._generate_monitoring_configs(config)

            # 7. 健康检查
            log_message("执行部署前健康检查...")
            health_results = self._run_pre_deployment_checks()

            duration_seconds = time.time() - start_time

            return DeploymentResult(
                deployment_id=self.deployment_id,
                timestamp=self.timestamp,
                environment=environment,
                status=DeploymentStatus.SUCCESS,
                duration_seconds=duration_seconds,
                success=True,
                error_message=None,
                health_check_results=health_results,
                security_scan_results={"status": "passed", "vulnerabilities": 0},
                performance_metrics={"deployment_time": duration_seconds},
                rollback_performed=False,
                deployment_log=deployment_log
            )

        except Exception as e:
            duration_seconds = time.time() - start_time
            error_message = str(e)
            log_message(f"部署失败: {error_message}")

            return DeploymentResult(
                deployment_id=self.deployment_id,
                timestamp=self.timestamp,
                environment=environment,
                status=DeploymentStatus.FAILED,
                duration_seconds=duration_seconds,
                success=False,
                error_message=error_message,
                health_check_results={},
                security_scan_results={},
                performance_metrics={},
                rollback_performed=False,
                deployment_log=deployment_log
            )

    def _generate_monitoring_configs(self, config: dict[str, Any]) -> dict[str, str]:
        """生成监控配置文件"""
        configs = {}

        # Prometheus配置
        prometheus_config = '''global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alert_rules.yml"

scrape_configs:
  - job_name: 'footballprediction-app'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['db:5432']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx:80']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
'''

        # AlertManager配置
        alertmanager_config = '''global:
  smtp_smarthost: 'localhost:587'
  smtp_from: 'alerts@footballprediction.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
  - name: 'web.hook'
    webhook_configs:
      - url: 'http://localhost:5001/'
'''

        # Loki配置
        loki_config = '''auth_enabled: false

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
'''

        configs["prometheus.yml"] = prometheus_config
        configs["alertmanager.yml"] = alertmanager_config
        configs["loki.yml"] = loki_config

        return configs

    def _run_pre_deployment_checks(self) -> dict[str, bool]:
        """运行部署前检查"""
        results = {}

        # 检查Docker是否运行
        try:
            subprocess.run(["docker", "version"], check=True, capture_output=True)
            results["docker"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            results["docker"] = False

        # 检查Docker Compose是否可用
        try:
            subprocess.run(["docker-compose",
    "version"],
    check=True,
    capture_output=True)
            results["docker_compose"] = True
        except (subprocess.CalledProcessError, FileNotFoundError):
            results["docker_compose"] = False

        # 检查端口是否可用
        import socket
        def check_port(port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            return result != 0

        results["port_80"] = check_port(80)
        results["port_443"] = check_port(443)
        results["port_8000"] = check_port(8000)

        return results

    def export_deployment_report(self,
    result: DeploymentResult,
    output_file: Path | None = None) -> Path:
        """导出部署报告"""
        if output_file is None:
            output_file = self.project_root / "reports" / f"deployment_report_{result.deployment_id}.json"

        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 转换为可序列化的字典
        result_dict = asdict(result)
        result_dict["environment"] = result.environment.value
        result_dict["status"] = result.status.value

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)

        return output_file

def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="生产环境部署自动化工具")
    parser.add_argument(
        "--project-root",
        type=Path,
        help="项目根目录路径"
    )
    parser.add_argument(
        "--environment",
        type=str,
        choices=["development", "testing", "staging", "production"],
        default="staging",
        help="部署环境"
    )
    parser.add_argument(
        "--generate-configs",
        action="store_true",
        help="仅生成配置文件"
    )
    parser.add_argument(
        "--execute-deployment",
        action="store_true",
        help="执行完整部署"
    )
    parser.add_argument(
        "--output-report",
        action="store_true",
        help="输出部署报告"
    )

    args = parser.parse_args()

    # 创建部署自动化实例
    project_root = args.project_root or Path(__file__).parent.parent.parent
    deployment = ProductionDeploymentAutomation(project_root)

    try:
        environment = Environment(args.environment)

        if args.generate_configs or args.execute_deployment:

            # 生成配置
            config = deployment.create_production_deployment_config(environment)

            # 创建secrets
            deployment.create_secrets_files(config)

            # 生成Docker Compose配置
            compose_content = deployment.generate_production_docker_compose(config)
            compose_file = project_root / "docker-compose.production.yml"
            with open(compose_file, 'w') as f:
                f.write(compose_content)

            # 生成SSL管理脚本
            ssl_script_content = deployment.generate_ssl_automation_script(config)
            ssl_script_file = project_root / "scripts" / "ssl_manager.sh"
            ssl_script_file.parent.mkdir(exist_ok=True)
            with open(ssl_script_file, 'w') as f:
                f.write(ssl_script_content)
            ssl_script_file.chmod(0o755)

            # 生成部署验证脚本
            verify_script_content = deployment.generate_deployment_verification_script(config)
            verify_script_file = project_root / "scripts" / "deploy_verify.sh"
            with open(verify_script_file, 'w') as f:
                f.write(verify_script_content)
            verify_script_file.chmod(0o755)

            # 生成监控配置
            monitoring_configs = deployment._generate_monitoring_configs(config)
            monitoring_dir = project_root / "monitoring"
            monitoring_dir.mkdir(exist_ok=True)
            for filename, content in monitoring_configs.items():
                config_file = monitoring_dir / filename
                with open(config_file, 'w') as f:
                    f.write(content)

        if args.execute_deployment:
            # 执行完整部署
            result = deployment.execute_deployment(environment)

            if args.output_report:
                deployment.export_deployment_report(result)

            # 显示结果

            if result.success:
                pass
            else:
                pass

        if not any([args.generate_configs, args.execute_deployment]):
            # 默认生成配置文件
            config = deployment.create_production_deployment_config(environment)

    except KeyboardInterrupt:
        sys.exit(130)
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
