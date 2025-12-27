---
name: docker-devops
description: Containerize and deploy applications using Docker and DevOps best practices. Use when creating Dockerfiles, managing docker-compose, setting up CI/CD pipelines, or optimizing container orchestration.
---

# Docker DevOps Skill

## 技能概述
专业的Docker和DevOps技能模块，专注于容器化部署、编排优化和CI/CD流水线自动化。

## 核心能力
- **容器化优化**: Dockerfile最佳实践、多阶段构建、镜像优化
- **容器编排**: Docker Compose配置、服务发现、负载均衡
- **CI/CD流水线**: GitHub Actions、自动化测试、自动部署
- **监控运维**: Prometheus + Grafana、日志聚合、健康检查
- **安全加固**: 容器安全、镜像扫描、访问控制
- **基础设施即代码**: 配置管理、版本控制、环境一致性

## 当前应用场景：足球预测系统部署
- **容器架构**: 多服务容器化（API、数据库、Redis、监控）
- **编排工具**: Docker Compose (开发) + Kubernetes (生产)
- **CI/CD**: GitHub Actions工作流
- **监控栈**: Prometheus + Grafana + Alertmanager
- **基础设施**: 本地开发 + 云端生产

## 工具和技术栈
- **Docker**: 容器化平台
- **Docker Compose**: 多容器应用编排
- **Kubernetes**: 生产环境容器编排
- **GitHub Actions**: CI/CD自动化
- **Helm**: Kubernetes包管理
- **Prometheus**: 指标监控
- **Grafana**: 可视化仪表板
- **Traefik**: 反向代理和负载均衡
- **Portainer**: 容器管理界面

## 快速开始（第一层）

### 基础Dockerfile
```dockerfile
# 多阶段构建优化
FROM python:3.11-slim as builder

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.11-slim as runtime

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 基础Docker Compose
```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/football
      - REDIS_URL=redis://redis:6379
    depends_on:
      - db
      - redis

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: football
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

## 深入优化（第二层）

### 生产级Dockerfile
```dockerfile
# 优化的生产Dockerfile
FROM python:3.11-slim as base

# 设置安全参数
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python依赖
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# 生产环境
FROM base as production
COPY --chown=appuser:appuser . .

# 非root用户运行
USER appuser

EXPOSE 8000

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

### 优化的Docker Compose
```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
      target: production
    restart: unless-stopped
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - db
      - redis
    networks:
      - app-network

  db:
    image: postgres:15-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - app-network

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    networks:
      - app-network

  prometheus:
    image: prom/prometheus:latest
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
    networks:
      - app-network

  grafana:
    image: grafana/grafana:latest
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana:/etc/grafana/provisioning
    networks:
      - app-network

volumes:
  postgres_data:
  redis_data:
  prometheus_data:
  grafana_data:

networks:
  app-network:
    driver: bridge
```

## 高级应用（第三层）

### Kubernetes部署配置
```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: football-prediction

---
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: football-prediction
data:
  DATABASE_URL: "postgresql://user:pass@postgres:5432/football"
  REDIS_URL: "redis://redis:6379"
  ENVIRONMENT: "production"

---
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: football-api
  namespace: football-prediction
spec:
  replicas: 3
  selector:
    matchLabels:
      app: football-api
  template:
    metadata:
      labels:
        app: football-api
    spec:
      containers:
      - name: api
        image: football-prediction:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: app-config
              key: REDIS_URL
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5

---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: football-api-service
  namespace: football-prediction
spec:
  selector:
    app: football-api
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP

---
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: football-api-ingress
  namespace: football-prediction
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.football-prediction.com
    secretName: football-api-tls
  rules:
  - host: api.football-prediction.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: football-api-service
            port:
              number: 80
```

### Helm Chart结构
```
helm-chart/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── ingress.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── hpa.yaml
│   └── monitoring/
└── charts/
```

### CI/CD流水线
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'

    - name: Install dependencies
      run: |
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest tests/ --cov=src --cov-report=xml

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build-and-deploy:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - uses: actions/checkout@v3

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v4
      with:
        context: .
        push: true
        tags: |
          yourusername/football-prediction:latest
          yourusername/football-prediction:${{ github.sha }}

    - name: Deploy to Kubernetes
      uses: azure/k8s-deploy@v1
      with:
        manifests: |
          k8s/deployment.yaml
          k8s/service.yaml
          k8s/ingress.yaml
        images: |
          yourusername/football-prediction:${{ github.sha }}
```

## 监控和可观测性

### Prometheus配置
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  - "alerts.yml"

scrape_configs:
  - job_name: 'football-api'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

alerting:
  alertmanagers:
    - static_configs:
        - targets:
          - alertmanager:9093
```

### 告警规则
```yaml
# monitoring/alerts.yml
groups:
  - name: api_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High error rate detected"
          description: "Error rate is above 5% for 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "95th percentile latency is above 1 second"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"
          description: "PostgreSQL database has been down for more than 1 minute"
```

### Grafana仪表板
```json
{
  "dashboard": {
    "title": "Football Prediction API",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Error Rate",
        "type": "singlestat",
        "targets": [
          {
            "expr": "rate(http_requests_total{status=~\"5..\"}[5m]) / rate(http_requests_total[5m])",
            "legendFormat": "Error Rate"
          }
        ]
      }
    ]
  }
}
```

## 安全加固

### 容器安全配置
```dockerfile
FROM python:3.11-slim

# 创建非root用户
RUN groupadd -r appuser && useradd -r -g appuser appuser

# 最小化安装
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# 设置安全选项
WORKDIR /app
COPY --chown=appuser:appuser . .
RUN chown -R appuser:appuser /app

# 非特权端口
EXPOSE 8000

# 非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 网络安全配置
```yaml
# docker-compose.security.yml
version: '3.8'

services:
  app:
    build: .
    networks:
      - internal
      - external
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G

  db:
    image: postgres:15-alpine
    networks:
      - internal  # 仅内部网络
    environment:
      POSTGRES_DB: football
      POSTGRES_USER: user
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  reverse-proxy:
    image: traefik:v2.10
    ports:
      - "80:80"
      - "443:443"
    networks:
      - external
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./acme.json:/acme.json
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.myresolver.acme.tlschallenge=true"

networks:
  internal:
    driver: bridge
    internal: true  # 内部网络，无法访问外网
  external:
    driver: bridge
```

## 性能优化

### 容器资源优化
```yaml
# docker-compose.performance.yml
version: '3.8'

services:
  app:
    build: .
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - WORKERS=4
      - MAX_CONNECTIONS=100

  db:
    image: postgres:15-alpine
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
    environment:
      - POSTGRES_SHARED_PRELOAD_LIBRARIES=pg_stat_statements
      - POSTGRES_MAX_CONNECTIONS=200
    command: >
      postgres
      -c shared_preload_libraries=pg_stat_statements
      -c max_connections=200
      -c shared_buffers=256MB
      -c effective_cache_size=1GB
      -c maintenance_work_mem=64MB
      -c checkpoint_completion_target=0.9
      -c wal_buffers=16MB
      -c default_statistics_target=100
      -c random_page_cost=1.1
      -c effective_io_concurrency=200
```

### Docker镜像优化
```dockerfile
# 多阶段构建 - 最小化镜像大小
FROM python:3.11-slim as builder

# 安装构建依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# 生产镜像 - 仅包含运行时依赖
FROM python:3.11-slim

# 仅安装运行时依赖
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

WORKDIR /app

# 从构建阶段复制Python包
COPY --from=builder /root/.local /root/.local

# 复制应用代码
COPY --chown=appuser:appuser . .

# 设置PATH
ENV PATH=/root/.local/bin:$PATH

# 非root用户
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 最佳实践

1. **镜像优化**
   - 使用多阶段构建减少镜像大小
   - 选择合适的基础镜像（alpine、slim）
   - 利用Docker层缓存优化构建速度

2. **安全实践**
   - 使用非root用户运行容器
   - 定期更新基础镜像
   - 扫描镜像安全漏洞
   - 使用.secrets管理敏感信息

3. **监控和日志**
   - 集中化日志收集
   - 关键指标监控
   - 健康检查和自动恢复
   - 告警和通知

4. **CI/CD优化**
   - 自动化测试和部署
   - 蓝绿部署或滚动更新
   - 回滚机制
   - 环境隔离

5. **运维管理**
   - 基础设施即代码
   - 版本控制配置
   - 自动化扩缩容
   - 备份和恢复策略

## Related Skills
- `deployment-management`: Deployment management (Docker, production)
- `deployment-operations`: Container deployment and automation
- `code-quality`: Code quality management
- `performance-monitoring`: System performance monitoring

---
*Last updated: 2025-12-28*
*Target: 足球预测系统容器化和CI/CD优化*