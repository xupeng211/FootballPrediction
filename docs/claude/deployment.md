# 部署和CI/CD指南

本文档详细介绍FootballPrediction项目的部署策略、CI/CD流水线和运维最佳实践。

---

## 📋 目录

- [🚀 部署架构概览](#-部署架构概览)
- [🐳 Docker容器化部署](#-docker容器化部署)
- [⚙️ 环境配置管理](#️-环境配置管理)
- [🔄 CI/CD流水线](#-cicd流水线)
- [🌐 多环境部署](#-多环境部署)
- [📊 监控和日志](#-监控和日志)
- [🔧 DevOps工具链](#-devops工具链)
- [🛡️ 安全和备份](#️-安全和备份)
- [📈 性能优化](#-性能优化)
- [🔍 故障排除和恢复](#-故障排除和恢复)

---

## 🚀 部署架构概览

### 整体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Load Balancer                        │
│                      (Nginx/HAProxy)                        │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   App Pod   │  │   App Pod   │  │      App Pod       │  │
│  │   (FastAPI) │  │   (FastAPI) │  │     (FastAPI)      │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────┐
│                     Data Layer                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ PostgreSQL  │  │    Redis    │  │   File Storage     │  │
│  │  (Primary)  │  │   Cluster   │  │    (NFS/S3)        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌─────────────┐                                           │
│  │ PostgreSQL  │                                           │
│  │ (Replica)   │                                           │
│  └─────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

### 部署组件说明

| 组件 | 技术栈 | 职责 | 高可用配置 |
|------|--------|------|------------|
| **负载均衡器** | Nginx/HAProxy | 请求分发、SSL终止 | 多实例、健康检查 |
| **应用服务** | FastAPI + Uvicorn | 业务逻辑处理 | 水平扩展、自动重启 |
| **数据库** | PostgreSQL 13+ | 数据持久化 | 主从复制、自动故障转移 |
| **缓存** | Redis 6+ | 缓存、会话存储 | Redis Cluster |
| **文件存储** | NFS/S3 | 静态文件存储 | 分布式存储 |
| **监控** | Prometheus + Grafana | 性能监控 | 多副本、数据备份 |

---

## 🐳 Docker容器化部署

### Dockerfile

```dockerfile
# Dockerfile
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .
COPY requirements-dev.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY src/ ./src/
COPY tests/ ./tests/
COPY pyproject.toml .
COPY pytest.ini .
COPY alembic.ini .

# 创建非root用户
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### docker-compose.yml

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/football_prediction
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
    depends_on:
      - db
      - redis
    volumes:
      - ./src:/app/src
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:13
    environment:
      - POSTGRES_DB=football_prediction
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init_db.sql
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 3

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./nginx/ssl:/etc/nginx/ssl
    depends_on:
      - app
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### 生产环境 docker-compose

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    image: football-prediction:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/football_prediction
      - REDIS_URL=redis://redis:6379/0
      - ENVIRONMENT=production
      - LOG_LEVEL=WARNING
      - SECRET_KEY=${SECRET_KEY}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 15s
      timeout: 10s
      retries: 3
      start_period: 30s

  db:
    image: postgres:13
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - POSTGRES_DB=football_prediction
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    restart_policy:
      condition: on-failure

  redis:
    image: redis:6-alpine
    deploy:
      replicas: 1
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
```

---

## ⚙️ 环境配置管理

### 环境变量配置

#### .env.example
```bash
# .env.example - 环境变量模板

# 应用配置
APP_NAME=football-prediction
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here
LOG_LEVEL=INFO

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/football_prediction
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_TIMEOUT=30

# Redis配置
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10
REDIS_TIMEOUT=5

# API配置
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# 外部服务配置
FOOTBALL_API_KEY=your-football-api-key
FOOTBALL_API_BASE_URL=https://api.football-data.org/v4

# 监控配置
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000

# 文件存储
UPLOAD_PATH=/app/uploads
MAX_UPLOAD_SIZE=10485760

# 邮件配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# 安全配置
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=30

# 缓存配置
CACHE_TTL=3600
CACHE_PREFIX=fp:
```

#### .env.ci (CI环境)
```bash
# .env.ci
ENVIRONMENT=ci
DEBUG=false
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/test_fp
REDIS_URL=redis://localhost:6379/1
LOG_LEVEL=ERROR
SECRET_KEY=test-secret-key
API_WORKERS=1
```

#### .env.production (生产环境)
```bash
# .env.production
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://postgres:${DB_PASSWORD}@db:5432/football_prediction
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=WARNING
SECRET_KEY=${SECRET_KEY}
API_WORKERS=8
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40
```

### 配置管理脚本

**环境检查脚本**
```bash
#!/bin/bash
# scripts/check_env.sh

echo "🔍 检查环境配置..."

# 检查必需的环境变量
required_vars=(
    "DATABASE_URL"
    "REDIS_URL"
    "SECRET_KEY"
    "ENVIRONMENT"
)

missing_vars=()
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    fi
done

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo "❌ 缺少必需的环境变量:"
    printf '  %s\n' "${missing_vars[@]}"
    exit 1
fi

echo "✅ 所有必需的环境变量已设置"

# 检查数据库连接
echo "🔍 检查数据库连接..."
python3 -c "
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine

async def check_db():
    engine = create_async_engine(os.getenv('DATABASE_URL'))
    async with engine.begin() as conn:
        await conn.execute('SELECT 1')
    print('✅ 数据库连接正常')

asyncio.run(check_db())
"

# 检查Redis连接
echo "🔍 检查Redis连接..."
python3 -c "
import asyncio
import aioredis
import os

async def check_redis():
    redis = aioredis.from_url(os.getenv('REDIS_URL'))
    await redis.ping()
    print('✅ Redis连接正常')

asyncio.run(check_redis())
"

echo "✅ 环境检查完成"
```

**环境创建脚本**
```bash
#!/bin/bash
# scripts/create_env.sh

ENV_TYPE=${1:-development}

echo "🔧 创建 ${ENV_TYPE} 环境配置..."

# 复制模板文件
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo "✅ 已从 .env.example 创建 .env 文件"
else
    echo "⚠️ .env 文件已存在，跳过创建"
fi

# 根据环境类型设置特定配置
case $ENV_TYPE in
    "development")
        echo "🔧 设置开发环境配置..."
        sed -i 's/ENVIRONMENT=.*/ENVIRONMENT=development/' .env
        sed -i 's/DEBUG=.*/DEBUG=true/' .env
        sed -i 's/LOG_LEVEL=.*/LOG_LEVEL=INFO/' .env
        ;;
    "ci")
        echo "🔧 设置CI环境配置..."
        sed -i 's/ENVIRONMENT=.*/ENVIRONMENT=ci/' .env
        sed -i 's/DEBUG=.*/DEBUG=false/' .env
        sed -i 's/LOG_LEVEL=.*/LOG_LEVEL=ERROR/' .env
        ;;
    "production")
        echo "🔧 设置生产环境配置..."
        sed -i 's/ENVIRONMENT=.*/ENVIRONMENT=production/' .env
        sed -i 's/DEBUG=.*/DEBUG=false/' .env
        sed -i 's/LOG_LEVEL=.*/LOG_LEVEL=WARNING/' .env
        ;;
esac

echo "✅ 环境配置创建完成"
echo "💡 请编辑 .env 文件设置具体的环境变量值"
```

---

## 🔄 CI/CD流水线

### GitHub Actions 工作流

#### .github/workflows/ci.yml
```yaml
name: CI Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: [3.11, 3.12]

    services:
      postgres:
        image: postgres:13
        env:
          POSTGRES_PASSWORD: postgres
          POSTGRES_DB: test_fp
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:6
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4
      with:
        python-version: ${{ matrix.python-version }}

    - name: Cache dependencies
      uses: actions/cache@v3
      with:
        path: ~/.cache/pip
        key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements*.txt') }}
        restore-keys: |
          ${{ runner.os }}-pip-

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt
        pip install -r requirements-dev.txt

    - name: Lint with Ruff
      run: |
        ruff check src/ tests/
        ruff format --check src/ tests/

    - name: Type check with MyPy
      run: mypy src/ --ignore-missing-imports

    - name: Run Smart Tests
      run: |
        cp .env.ci .env
        make test.smart
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_fp
        REDIS_URL: redis://localhost:6379/1

    - name: Run full unit tests
      run: |
        make test.unit
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_fp
        REDIS_URL: redis://localhost:6379/1

    - name: Run integration tests
      run: |
        make test.integration
      env:
        DATABASE_URL: postgresql://postgres:postgres@localhost:5432/test_fp
        REDIS_URL: redis://localhost:6379/1

    - name: Generate coverage report
      run: |
        make coverage
        make cov.html

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

    - name: Run security audit
      run: |
        pip-audit
        bandit -r src/ -f json -o bandit-report.json

    - name: Upload security report
      uses: actions/upload-artifact@v3
      if: always()
      with:
        name: security-report
        path: bandit-report.json

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Login to Docker Hub
      uses: docker/login-action@v3
      with:
        username: ${{ secrets.DOCKER_USERNAME }}
        password: ${{ secrets.DOCKER_PASSWORD }}

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: |
          ${{ secrets.DOCKER_USERNAME }}/football-prediction:latest
          ${{ secrets.DOCKER_USERNAME }}/football-prediction:${{ github.sha }}
        cache-from: type=gha
        cache-to: type=gha,mode=max
```

#### .github/workflows/deploy.yml
```yaml
name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Deploy to server
      uses: appleboy/ssh-action@v1.0.0
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.SSH_KEY }}
        script: |
          cd /opt/football-prediction
          docker-compose -f docker-compose.prod.yml pull
          docker-compose -f docker-compose.prod.yml up -d
          docker system prune -f

    - name: Run health check
      run: |
        sleep 30
        curl -f ${{ secrets.PROD_URL }}/health

    - name: Notify Slack
      uses: 8398a7/action-slack@v3
      if: always()
      with:
        status: ${{ job.status }}
        channel: '#deployments'
        webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

### 部署脚本

#### scripts/deploy.sh
```bash
#!/bin/bash
# scripts/deploy.sh

set -e

ENVIRONMENT=${1:-production}
VERSION=${2:-latest}

echo "🚀 开始部署 $ENVIRONMENT 环境，版本: $VERSION"

# 检查必要工具
command -v docker >/dev/null 2>&1 || { echo "❌ Docker 未安装"; exit 1; }
command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose 未安装"; exit 1; }

# 备份当前版本
echo "📦 备份当前版本..."
mkdir -p backups
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres football_prediction > backups/backup_$(date +%Y%m%d_%H%M%S).sql

# 拉取最新镜像
echo "📥 拉取最新镜像..."
docker-compose -f docker-compose.prod.yml pull

# 停止旧容器
echo "⏹️ 停止旧容器..."
docker-compose -f docker-compose.prod.yml down

# 启动新容器
echo "▶️ 启动新容器..."
docker-compose -f docker-compose.prod.yml up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 健康检查
echo "🔍 执行健康检查..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -f http://localhost:8000/health; then
        echo "✅ 健康检查通过"
        break
    fi

    RETRY_COUNT=$((RETRY_COUNT + 1))
    echo "⏳ 等待服务启动... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 5
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ 健康检查失败"
    echo "🔄 回滚到上一版本..."
    docker-compose -f docker-compose.prod.yml down
    # 这里可以添加回滚逻辑
    exit 1
fi

# 清理旧镜像
echo "🧹 清理旧镜像..."
docker image prune -f

echo "✅ 部署完成!"
```

#### scripts/rollback.sh
```bash
#!/bin/bash
# scripts/rollback.sh

set -e

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
    echo "❌ 请指定备份文件"
    echo "用法: $0 <backup_file.sql>"
    exit 1
fi

echo "🔄 开始回滚到备份: $BACKUP_FILE"

# 恢复数据库
echo "📊 恢复数据库..."
docker-compose -f docker-compose.prod.yml exec -T db psql -U postgres -d football_prediction < "$BACKUP_FILE"

# 重启应用
echo "🔄 重启应用..."
docker-compose -f docker-compose.prod.yml restart app

# 健康检查
echo "🔍 执行健康检查..."
sleep 10
if curl -f http://localhost:8000/health; then
    echo "✅ 回滚成功"
else
    echo "❌ 回滚失败"
    exit 1
fi

echo "✅ 回滚完成!"
```

---

## 🌐 多环境部署

### 环境配置

| 环境 | 用途 | 域名 | 数据库 | 缓存 | 监控 |
|------|------|------|--------|------|------|
| **开发环境** | 日常开发测试 | dev.fp.local | PostgreSQL单实例 | Redis单实例 | 基础监控 |
| **测试环境** | 集成测试 | test.fp.local | PostgreSQL单实例 | Redis单实例 | 完整监控 |
| **预发布环境** | 上线前验证 | staging.fp.local | PostgreSQL主从 | Redis Cluster | 生产级监控 |
| **生产环境** | 正式服务 | api.fp.com | PostgreSQL主从 | Redis Cluster | 生产级监控 |

### 环境隔离策略

#### Kubernetes Namespace配置
```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: football-prediction-dev
  labels:
    environment: development
    project: football-prediction

---
apiVersion: v1
kind: Namespace
metadata:
  name: football-prediction-prod
  labels:
    environment: production
    project: football-prediction
```

#### 环境特定配置
```yaml
# k8s/configmap-dev.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: football-prediction-dev
data:
  ENVIRONMENT: "development"
  DEBUG: "true"
  LOG_LEVEL: "INFO"
  DATABASE_URL: "postgresql://postgres:password@postgres-dev:5432/fp_dev"
  REDIS_URL: "redis://redis-dev:6379/0"
```

```yaml
# k8s/configmap-prod.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: app-config
  namespace: football-prediction-prod
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  LOG_LEVEL: "WARNING"
  DATABASE_URL: "postgresql://postgres:${DB_PASSWORD}@postgres-prod:5432/fp_prod"
  REDIS_URL: "redis://redis-prod:6379/0"
```

### 蓝绿部署策略

#### 蓝绿部署脚本
```bash
#!/bin/bash
# scripts/blue_green_deploy.sh

set -e

CURRENT_ENV=$1
NEW_VERSION=$2

if [ "$CURRENT_ENV" = "blue" ]; then
    TARGET_ENV="green"
else
    TARGET_ENV="blue"
fi

echo "🔄 执行蓝绿部署: $CURRENT_ENV → $TARGET_ENV (版本: $NEW_VERSION)"

# 部署新环境
echo "📦 部署 $TARGET_ENV 环境..."
kubectl set image deployment/football-prediction-$TARGET_ENV \
  app=football-prediction:$NEW_VERSION \
  -n football-prediction-prod

# 等待部署完成
echo "⏳ 等待 $TARGET_ENV 环境就绪..."
kubectl rollout status deployment/football-prediction-$TARGET_ENV \
  -n football-prediction-prod --timeout=300s

# 健康检查
echo "🔍 执行 $TARGET_ENV 环境健康检查..."
TARGET_POD=$(kubectl get pods -n football-prediction-prod -l env=$TARGET_ENV -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n football-prediction-prod $TARGET_POD -- curl -f http://localhost:8000/health

# 切换流量
echo "🔀 切换流量到 $TARGET_ENV 环境..."
kubectl patch service football-prediction-service -n football-prediction-prod \
  -p '{"spec":{"selector":{"env":"'$TARGET_ENV'"}}}'

echo "✅ 蓝绿部署完成，当前活跃环境: $TARGET_ENV"
```

---

## 📊 监控和日志

### Prometheus监控配置

#### prometheus.yml
```yaml
# prometheus.yml
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
  - job_name: 'football-prediction'
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

  - job_name: 'nginx'
    static_configs:
      - targets: ['nginx-exporter:9113']
```

#### alert_rules.yml
```yaml
# alert_rules.yml
groups:
  - name: football-prediction-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value }} errors per second"

      - alert: HighMemoryUsage
        expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.9
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High memory usage"
          description: "Memory usage is {{ $value | humanizePercentage }}"

      - alert: DatabaseConnectionFailure
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database connection failure"
          description: "Cannot connect to PostgreSQL database"

      - alert: RedisConnectionFailure
        expr: up{job="redis"} == 0
        for: 1m
        labels:
          severity: warning
        annotations:
          summary: "Redis connection failure"
          description: "Cannot connect to Redis server"
```

### Grafana仪表板

#### 应用监控指标
```python
# src/monitoring/metrics.py
from prometheus_client import Counter, Histogram, Gauge, start_http_server
import time
import functools

# 定义监控指标
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

REQUEST_DURATION = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

ACTIVE_CONNECTIONS = Gauge(
    'active_connections',
    'Number of active connections'
)

PREDICTION_COUNT = Counter(
    'predictions_total',
    'Total predictions made',
    ['strategy_type', 'result']
)

def track_requests(func):
    """请求追踪装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            status_code = getattr(result, 'status_code', 200)
            REQUEST_COUNT.labels(
                method='GET',
                endpoint=func.__name__,
                status_code=status_code
            ).inc()
            return result
        except Exception as e:
            REQUEST_COUNT.labels(
                method='GET',
                endpoint=func.__name__,
                status_code=500
            ).inc()
            raise
        finally:
            REQUEST_DURATION.labels(
                method='GET',
                endpoint=func.__name__
            ).observe(time.time() - start_time)

    return wrapper

def start_metrics_server():
    """启动指标服务器"""
    start_http_server(9090)
```

### 日志聚合配置

#### ELK Stack配置
```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    ports:
      - "5044:5044"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline
      - ./logstash/config:/usr/share/logstash/config
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

#### Logstash配置
```ruby
# logstash/pipeline/football-prediction.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "football-prediction" {
    json {
      source => "message"
    }

    date {
      match => [ "timestamp", "ISO8601" ]
    }

    if [level] == "ERROR" {
      mutate {
        add_tag => [ "error" ]
      }
    }

    if [user_id] {
      mutate {
        add_field => { "user_identifier" => "%{user_id}" }
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "football-prediction-%{+YYYY.MM.dd}"
  }

  if "error" in [tags] {
    email {
      to => "admin@football-prediction.com"
      subject => "Error Alert: %{[fields][service]}"
      body => "Error occurred: %{message}"
    }
  }
}
```

---

## 🔧 DevOps工具链

### Makefile集成

```makefile
# Makefile (DevOps相关命令)

.PHONY: docker-build docker-push deploy deploy-staging rollback

# Docker构建
docker-build:
	docker build -t football-prediction:$(VERSION) .

# Docker推送
docker-push:
	docker tag football-prediction:$(VERSION) $(DOCKER_REGISTRY)/football-prediction:$(VERSION)
	docker push $(DOCKER_REGISTRY)/football-prediction:$(VERSION)

# 部署到测试环境
deploy-staging:
	@echo "🚀 部署到测试环境..."
	ENVIRONMENT=staging VERSION=$(VERSION) scripts/deploy.sh

# 部署到生产环境
deploy-production:
	@echo "🚀 部署到生产环境..."
	ENVIRONMENT=production VERSION=$(VERSION) scripts/deploy.sh

# 回滚
rollback:
	@echo "🔄 回滚到上一个版本..."
	scripts/rollback.sh $(BACKUP_FILE)

# 数据库迁移
migrate:
	@echo "📊 执行数据库迁移..."
	alembic upgrade head

# 备份数据库
backup:
	@echo "💾 备份数据库..."
	./scripts/backup_database.sh

# 恢复数据库
restore:
	@echo "🔄 恢复数据库..."
	./scripts/restore_database.sh $(BACKUP_FILE)

# 健康检查
health-check:
	@echo "🔍 执行健康检查..."
	curl -f $(API_URL)/health || exit 1

# 性能测试
performance-test:
	@echo "⚡ 执行性能测试..."
	./scripts/performance_test.sh

# 安全扫描
security-scan:
	@echo "🔒 执行安全扫描..."
	docker run --rm -v $(PWD):/app clair-scanner:latest

# 依赖检查
dependency-check:
	@echo "📦 检查依赖安全..."
	pip-audit
	safety check

# 代码质量检查
quality-check:
	@echo "🔍 执行代码质量检查..."
	make lint
	make type-check
	make security-scan

# CI完整流程
ci-full:
	@echo "🔄 执行完整CI流程..."
	make quality-check
	make test.unit
	make test.integration
	make coverage
	make security-scan

# CD完整流程
cd-full:
	@echo "🚀 执行完整CD流程..."
	make ci-full
	make docker-build
	make docker-push
	make deploy-staging
	make health-check
```

### 自动化脚本

#### 数据库备份脚本
```bash
#!/bin/bash
# scripts/backup_database.sh

set -e

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/football_prediction_backup_$DATE.sql"

# 创建备份目录
mkdir -p $BACKUP_DIR

# 执行备份
echo "📊 开始备份数据库..."
docker-compose -f docker-compose.prod.yml exec -T db pg_dump -U postgres -Fc football_prediction > $BACKUP_FILE

# 压缩备份文件
gzip $BACKUP_FILE

# 清理旧备份（保留30天）
find $BACKUP_DIR -name "*.gz" -mtime +30 -delete

echo "✅ 数据库备份完成: $BACKUP_FILE.gz"

# 上传到云存储（可选）
if [ -n "$S3_BUCKET" ]; then
    aws s3 cp $BACKUP_FILE.gz s3://$S3_BUCKET/backups/
    echo "☁️ 备份已上传到S3"
fi
```

#### 健康检查脚本
```bash
#!/bin/bash
# scripts/health_check.sh

API_URL=${1:-http://localhost:8000}
MAX_RETRIES=30
RETRY_INTERVAL=5

echo "🔍 执行健康检查: $API_URL"

for i in $(seq 1 $MAX_RETRIES); do
    if curl -f -s "$API_URL/health" > /dev/null; then
        echo "✅ 健康检查通过"
        exit 0
    fi

    echo "⏳ 健康检查失败，重试中... ($i/$MAX_RETRIES)"
    sleep $RETRY_INTERVAL
done

echo "❌ 健康检查失败"
exit 1
```

---

## 🛡️ 安全和备份

### 安全配置

#### SSL/TLS配置
```nginx
# nginx/ssl.conf
server {
    listen 443 ssl http2;
    server_name api.football-prediction.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # 安全头
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### 网络安全
```yaml
# docker-compose.security.yml
version: '3.8'

services:
  app:
    networks:
      - app-network
      - db-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
    security_opt:
      - no-new-privileges:true
    user: "1000:1000"
    read_only: true
    tmpfs:
      - /tmp
      - /var/run

  db:
    networks:
      - db-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
    environment:
      - POSTGRES_INITDB_ARGS=--auth-host=scram-sha-256
    command: >
      postgres
      -c ssl=on
      -c ssl_cert_file=/var/lib/postgresql/server.crt
      -c ssl_key_file=/var/lib/postgresql/server.key

networks:
  app-network:
    driver: bridge
    internal: false
  db-network:
    driver: bridge
    internal: true
```

### 备份策略

#### 自动化备份
```bash
#!/bin/bash
# scripts/automated_backup.sh

set -e

BACKUP_TYPE=${1:-full}  # full, incremental, differential
RETENTION_DAYS=${2:-30}

echo "📦 开始 $BACKUP_TYPE 备份，保留 $RETENTION_DAYS 天"

case $BACKUP_TYPE in
    "full")
        echo "📊 完整数据库备份..."
        docker-compose exec db pg_dump -U postgres -Fc football_prediction > /backups/full_$(date +%Y%m%d_%H%M%S).dump
        ;;
    "incremental")
        echo "📊 增量备份..."
        # 基于WAL日志的增量备份
        docker-compose exec db pg_basebackup -U postgres -D /backups/incremental_$(date +%Y%m%d_%H%M%S) -Ft -z -P
        ;;
    "differential")
        echo "📊 差异备份..."
        # 从上一个完整备份的差异
        ;;
esac

# 备份应用数据
echo "📁 备份应用数据..."
tar -czf /backups/app_data_$(date +%Y%m%d_%H%M%S).tar.gz /app/uploads

# 清理过期备份
echo "🧹 清理过期备份..."
find /backups -name "*$(date -d "$RETENTION_DAYS days ago" +%Y%m%d)*" -delete

# 上传到云存储
echo "☁️ 上传备份到云存储..."
aws s3 sync /backups s3://$S3_BUCKET/backups/ --delete

echo "✅ 备份完成"
```

---

## 📈 性能优化

### 应用性能优化

#### 数据库优化
```sql
-- 数据库性能优化
-- 创建索引
CREATE INDEX CONCURRENTLY idx_predictions_match_id ON predictions(match_id);
CREATE INDEX CONCURRENTLY idx_predictions_created_at ON predictions(created_at);
CREATE INDEX CONCURRENTLY idx_matches_date ON matches(match_date);

-- 分析表统计信息
ANALYZE predictions;
ANALYZE matches;
ANALYZE teams;

-- 配置连接池
-- postgresql.conf
max_connections = 200
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
maintenance_work_mem = 64MB
```

#### 缓存策略
```python
# src/cache/strategies.py
from functools import wraps
import redis
import json
import hashlib

class RedisCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.default_ttl = 3600  # 1小时

    def cache_result(self, key_prefix, ttl=None):
        """缓存装饰器"""
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # 生成缓存键
                cache_key = self._generate_cache_key(key_prefix, args, kwargs)

                # 尝试从缓存获取
                cached_result = await self.redis.get(cache_key)
                if cached_result:
                    return json.loads(cached_result)

                # 执行函数
                result = await func(*args, **kwargs)

                # 存入缓存
                await self.redis.setex(
                    cache_key,
                    ttl or self.default_ttl,
                    json.dumps(result, default=str)
                )

                return result
            return wrapper
        return decorator

    def _generate_cache_key(self, prefix, args, kwargs):
        """生成缓存键"""
        key_data = f"{prefix}:{str(args)}:{str(sorted(kwargs.items()))}"
        return hashlib.md5(key_data.encode()).hexdigest()

# 使用示例
cache = RedisCache(redis_client)

@cache.cache_result("prediction", ttl=1800)  # 30分钟缓存
async def get_prediction(match_id, strategy_type):
    # 复杂的预测逻辑
    pass
```

### 负载测试

#### Locust性能测试
```python
# tests/performance/locustfile.py
from locust import HttpUser, task, between
import random

class FootballPredictionUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """用户开始时执行"""
        # 登录获取token
        response = self.client.post("/api/auth/login", json={
            "username": "test_user",
            "password": "test_password"
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.headers = {}

    @task(3)
    def get_matches(self):
        """获取比赛列表"""
        self.client.get("/api/matches", headers=self.headers)

    @task(2)
    def create_prediction(self):
        """创建预测"""
        match_ids = ["match_1", "match_2", "match_3"]
        strategies = ["ml_model", "historical", "statistical"]

        self.client.post("/api/predictions", json={
            "match_id": random.choice(match_ids),
            "strategy_type": random.choice(strategies)
        }, headers=self.headers)

    @task(1)
    def get_prediction(self):
        """获取预测结果"""
        prediction_id = f"pred_{random.randint(1, 1000)}"
        self.client.get(f"/api/predictions/{prediction_id}", headers=self.headers)

    @task(1)
    def health_check(self):
        """健康检查"""
        self.client.get("/health")

class AdminUser(FootballPredictionUser):
    wait_time = between(2, 5)

    @task(2)
    def get_system_stats(self):
        """获取系统统计"""
        self.client.get("/api/admin/stats", headers=self.headers)

    @task(1)
    def get_users(self):
        """获取用户列表"""
        self.client.get("/api/admin/users", headers=self.headers)
```

---

## 🔍 故障排除和恢复

### 常见问题诊断

#### 服务故障排除
```bash
#!/bin/bash
# scripts/diagnose.sh

echo "🔍 系统诊断开始..."

# 检查容器状态
echo "📦 检查容器状态..."
docker-compose -f docker-compose.prod.yml ps

# 检查资源使用
echo "💾 检查资源使用..."
docker stats --no-stream

# 检查日志错误
echo "📝 检查最近错误日志..."
docker-compose -f docker-compose.prod.yml logs --tail=100 app | grep ERROR

# 检查数据库连接
echo "🗄️ 检查数据库连接..."
docker-compose -f docker-compose.prod.yml exec db pg_isready -U postgres

# 检查Redis连接
echo "🗄️ 检查Redis连接..."
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# 检查磁盘空间
echo "💾 检查磁盘空间..."
df -h

# 检查网络连接
echo "🌐 检查网络连接..."
curl -f http://localhost:8000/health || echo "❌ 应用健康检查失败"

echo "🔍 系统诊断完成"
```

#### 自动故障恢复
```python
# src/monitoring/auto_recovery.py
import asyncio
import logging
from typing import Dict, Any
import docker

class AutoRecovery:
    def __init__(self):
        self.docker_client = docker.from_env()
        self.logger = logging.getLogger(__name__)

    async def check_and_recover(self):
        """检查系统状态并自动恢复"""
        while True:
            try:
                await self._check_services()
                await asyncio.sleep(60)  # 每分钟检查一次
            except Exception as e:
                self.logger.error(f"自动恢复检查失败: {e}")

    async def _check_services(self):
        """检查各项服务"""
        # 检查应用服务
        if not await self._check_app_health():
            await self._recover_app()

        # 检查数据库
        if not await self._check_database():
            await self._recover_database()

        # 检查Redis
        if not await self._check_redis():
            await self._recover_redis()

    async def _check_app_health(self) -> bool:
        """检查应用健康状态"""
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get('http://localhost:8000/health') as response:
                    return response.status == 200
        except:
            return False

    async def _recover_app(self):
        """恢复应用服务"""
        self.logger.warning("应用服务异常，开始自动恢复...")

        try:
            # 重启应用容器
            container = self.docker_client.containers.get('football-prediction-app')
            container.restart()
            self.logger.info("应用容器重启成功")
        except Exception as e:
            self.logger.error(f"应用恢复失败: {e}")
            # 发送告警
            await self._send_alert("应用服务自动恢复失败", str(e))

    async def _check_database(self) -> bool:
        """检查数据库连接"""
        try:
            import asyncpg
            conn = await asyncpg.connect("postgresql://postgres:password@localhost:5432/football_prediction")
            await conn.execute('SELECT 1')
            await conn.close()
            return True
        except:
            return False

    async def _recover_database(self):
        """恢复数据库"""
        self.logger.warning("数据库异常，开始自动恢复...")

        try:
            # 重启数据库容器
            container = self.docker_client.containers.get('football-prediction-db')
            container.restart()
            self.logger.info("数据库容器重启成功")
        except Exception as e:
            self.logger.error(f"数据库恢复失败: {e}")
            await self._send_alert("数据库自动恢复失败", str(e))

    async def _check_redis(self) -> bool:
        """检查Redis连接"""
        try:
            import aioredis
            redis = aioredis.from_url("redis://localhost:6379/0")
            await redis.ping()
            await redis.close()
            return True
        except:
            return False

    async def _recover_redis(self):
        """恢复Redis"""
        self.logger.warning("Redis异常，开始自动恢复...")

        try:
            # 重启Redis容器
            container = self.docker_client.containers.get('football-prediction-redis')
            container.restart()
            self.logger.info("Redis容器重启成功")
        except Exception as e:
            self.logger.error(f"Redis恢复失败: {e}")
            await self._send_alert("Redis自动恢复失败", str(e))

    async def _send_alert(self, title: str, message: str):
        """发送告警"""
        # 发送邮件、Slack或其他告警方式
        self.logger.error(f"告警: {title} - {message}")
        # 这里可以集成具体的告警系统
```

### 灾难恢复计划

#### RTO/RPO目标
| 服务 | RTO (恢复时间目标) | RPO (恢复点目标) | 备份频率 |
|------|-------------------|-------------------|----------|
| **应用服务** | 5分钟 | 1分钟 | 实时镜像 |
| **数据库** | 30分钟 | 15分钟 | 每15分钟增量 |
| **Redis缓存** | 5分钟 | 0分钟 | 无状态 |
| **文件存储** | 1小时 | 1小时 | 每日全量 |

#### 灾难恢复流程
```bash
#!/bin/bash
# scripts/disaster_recovery.sh

set -e

DISASTER_TYPE=$1
BACKUP_LOCATION=$2

echo "🚨 开始灾难恢复流程"
echo "灾难类型: $DISASTER_TYPE"
echo "备份位置: $BACKUP_LOCATION"

case $DISASTER_TYPE in
    "data_corruption")
        echo "📊 数据损坏恢复..."
        ./scripts/restore_database.sh $BACKUP_LOCATION/latest_full_backup.dump
        ;;
    "server_failure")
        echo "🖥️ 服务器故障恢复..."
        # 1. 在新服务器上部署环境
        ./scripts/setup_new_server.sh
        # 2. 恢复数据
        ./scripts/restore_all_data.sh $BACKUP_LOCATION
        # 3. 更新DNS
        ./scripts/update_dns.sh
        ;;
    "network_outage")
        echo "🌐 网络中断恢复..."
        # 切换到备用网络
        ./scripts/failover_network.sh
        ;;
    "security_breach")
        echo "🔒 安全事件恢复..."
        # 1. 隔离受感染系统
        ./scripts/isolate_compromised_systems.sh
        # 2. 从干净备份恢复
        ./scripts/restore_from_clean_backup.sh $BACKUP_LOCATION
        # 3. 重置所有密码和密钥
        ./_scripts/reset_credentials.sh
        ;;
esac

echo "✅ 灾难恢复完成"
echo "🔍 执行恢复后验证..."
./scripts/post_recovery_verification.sh

echo "📢 通知相关人员恢复完成"
./scripts/notify_recovery_completion.sh
```

---

## 🎯 部署最佳实践

### 1. 部署清单
- [ ] 环境变量配置正确
- [ ] 数据库迁移完成
- [ ] 健康检查通过
- [ ] 性能基准达标
- [ ] 安全扫描通过
- [ ] 监控告警配置
- [ ] 日志聚合正常
- [ ] 备份策略验证

### 2. 发布策略
- **蓝绿部署**: 零停机时间部署
- **金丝雀发布**: 逐步流量切换
- **功能开关**: 动态功能控制
- **回滚机制**: 快速故障恢复

### 3. 监控指标
- **应用指标**: 响应时间、错误率、吞吐量
- **系统指标**: CPU、内存、磁盘、网络
- **业务指标**: 预测准确率、用户活跃度
- **安全指标**: 登录失败、异常访问

### 4. 运维自动化
- **自动部署**: CI/CD流水线
- **自动扩缩容**: 基于负载的弹性扩展
- **自动故障恢复**: 异常检测和自动处理
- **自动备份**: 定期数据备份和验证

---

*文档版本: v1.0 | 更新时间: 2025-11-16*