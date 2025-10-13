# 部署指南 V2

本文档提供了足球预测系统 V2 的完整部署指南，包括本地开发、测试环境和生产环境的部署。

## 目录

1. [系统要求](#系统要求)
2. [本地开发环境](#本地开发环境)
3. [Docker 部署](#docker-部署)
4. [Kubernetes 部署](#kubernetes-部署)
5. [云平台部署](#云平台部署)
6. [配置管理](#配置管理)
7. [监控和日志](#监控和日志)
8. [性能调优](#性能调优)
9. [安全配置](#安全配置)

## 系统要求

### 最低配置
- **CPU**: 2 核心
- **内存**: 4 GB RAM
- **存储**: 20 GB SSD
- **操作系统**: Linux (Ubuntu 20.04+), macOS, Windows 10+

### 推荐配置
- **CPU**: 4 核心
- **内存**: 8 GB RAM
- **存储**: 50 GB SSD
- **网络**: 100 Mbps

### 依赖服务
- PostgreSQL 14+
- Redis 6+
- Python 3.11+
- Docker 20.10+ (可选)
- Kubernetes 1.20+ (可选)

## 本地开发环境

### 1. 克隆项目

```bash
git clone https://github.com/your-org/football-prediction.git
cd football-prediction
```

### 2. 创建虚拟环境

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 安装开发依赖
pip install -r requirements/dev.lock

# 安装预提交钩子
pre-commit install
```

### 4. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env.local

# 编辑配置
vim .env.local
```

**必需的环境变量：**

```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/football_prediction
REDIS_URL=redis://localhost:6379/0

# API配置
SECRET_KEY=your-secret-key-here
ENVIRONMENT=development
LOG_LEVEL=INFO

# 外部服务
FOOTBALL_API_TOKEN=your-football-api-token
MLFLOW_TRACKING_URI=http://localhost:5002

# 可选服务
SENTRY_DSN=your-sentry-dsn
SLACK_WEBHOOK_URL=your-slack-webhook
```

### 5. 启动依赖服务

```bash
# 启动 PostgreSQL 和 Redis
docker-compose -f docker-compose.test.yml up -d postgres redis
```

### 6. 数据库迁移

```bash
# 运行迁移
alembic upgrade head

# 或使用 Makefile
make migrate
```

### 7. 启动开发服务器

```bash
# 启动 API 服务
uvicorn src.api.app:app --reload --host 0.0.0.0 --port 8000

# 或使用 Makefile
make run-dev
```

### 8. 验证安装

```bash
# 健康检查
curl http://localhost:8000/api/health

# 查看 API 文档
open http://localhost:8000/docs
```

## Docker 部署

### 1. 构建镜像

```bash
# 构建应用镜像
docker build -t football-prediction:latest .

# 或使用 Makefile
make build
```

### 2. 使用 Docker Compose

#### 开发环境

```bash
docker-compose -f docker-compose.yml up -d
```

#### 测试环境

```bash
docker-compose -f docker-compose.staging.yml up -d
```

#### 生产环境

```bash
# 准备生产环境配置
cp .env.example .env.prod
# 编辑 .env.prod

# 启动生产服务
docker-compose -f docker-compose.prod.yml up -d
```

### 3. 验证部署

```bash
# 检查服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app

# 测试 API
curl http://localhost:8000/api/health
```

## Kubernetes 部署

### 1. 准备 Kubernetes 清单

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
  name: football-config
  namespace: football-prediction
data:
  ENVIRONMENT: "production"
  LOG_LEVEL: "INFO"
```

### 2. 创建 Secret

```bash
kubectl create secret generic football-secrets \
  --from-literal=database-url="postgresql+asyncpg://..." \
  --from-literal=redis-url="redis://..." \
  --from-literal=secret-key="..." \
  -n football-prediction
```

### 3. 部署应用

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: football-prediction
  namespace: football-prediction
spec:
  replicas: 3
  selector:
    matchLabels:
      app: football-prediction
  template:
    metadata:
      labels:
        app: football-prediction
    spec:
      containers:
      - name: app
        image: football-prediction:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: football-config
        - secretRef:
            name: football-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
# service.yaml
apiVersion: v1
kind: Service
metadata:
  name: football-prediction-service
  namespace: football-prediction
spec:
  selector:
    app: football-prediction
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### 4. 部署命令

```bash
# 应用所有配置
kubectl apply -f k8s/

# 检查部署状态
kubectl get pods -n football-prediction
kubectl get services -n football-prediction

# 查看日志
kubectl logs -f deployment/football-prediction -n football-prediction
```

## 云平台部署

### AWS ECS 部署

#### 1. 创建 ECR 仓库

```bash
aws ecr create-repository \
  --repository-name football-prediction \
  --region us-west-2
```

#### 2. 推送镜像

```bash
# 获取登录令牌
aws ecr get-login-password --region us-west-2 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-west-2.amazonaws.com

# 标记镜像
docker tag football-prediction:latest <account-id>.dkr.ecr.us-west-2.amazonaws.com/football-prediction:latest

# 推送镜像
docker push <account-id>.dkr.ecr.us-west-2.amazonaws.com/football-prediction:latest
```

#### 3. 创建 ECS 任务定义

```json
{
  "family": "football-prediction",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::<account-id>:role/ecsTaskRole",
  "containerDefinitions": [
    {
      "name": "football-prediction",
      "image": "<account-id>.dkr.ecr.us-west-2.amazonaws.com/football-prediction:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "ENVIRONMENT",
          "value": "production"
        }
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:us-west-2:<account-id>:secret:football-db:url"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/football-prediction",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

### Google Cloud Run 部署

```bash
# 构建并推送镜像
gcloud builds submit --tag gcr.io/PROJECT_ID/football-prediction

# 部署到 Cloud Run
gcloud run deploy football-prediction \
  --image gcr.io/PROJECT_ID/football-prediction \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 100 \
  --set-env-vars ENVIRONMENT=production
```

## 配置管理

### 1. 环境配置层级

```yaml
# config/base.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: football-base-config
data:
  LOG_LEVEL: "INFO"
  MAX_WORKERS: "4"
  REDIS_POOL_SIZE: "10"

---
# config/production.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: football-prod-config
data:
  ENVIRONMENT: "production"
  DEBUG: "false"
  SENTRY_ENABLED: "true"

---
# config/development.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: football-dev-config
data:
  ENVIRONMENT: "development"
  DEBUG: "true"
  LOG_LEVEL: "DEBUG"
```

### 2. 使用 Kustomize 管理配置

```yaml
# kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
namespace: football-prediction
resources:
- deployment.yaml
- service.yaml
configMapGenerator:
- name: football-config
  literals:
- ENVIRONMENT=production
patchesStrategicMerge:
- patches/production.yaml
```

## 监控和日志

### 1. Prometheus 监控

```yaml
# prometheus-config.yaml
global:
  scrape_interval: 15s

scrape_configs:
- job_name: 'football-prediction'
  static_configs:
  - targets: ['football-prediction-service:80']
  metrics_path: /metrics
  scrape_interval: 5s
```

### 2. Grafana 仪表板

```json
{
  "dashboard": {
    "title": "Football Prediction Metrics",
    "panels": [
      {
        "title": "Prediction Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(predictions_total[5m])",
            "legendFormat": "{{model_version}}"
          }
        ]
      },
      {
        "title": "Prediction Accuracy",
        "type": "stat",
        "targets": [
          {
            "expr": "prediction_accuracy",
            "legendFormat": "{{model_version}}"
          }
        ]
      }
    ]
  }
}
```

### 3. ELK 日志栈

```yaml
# filebeat.yml
filebeat.inputs:
- type: container
  paths:
    - '/var/log/containers/*football*.log'
  processors:
  - add_kubernetes_metadata:
      host: ${NODE_NAME}
      matchers:
      - logs_path:
          logs_path: "/var/log/containers/"

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

## 性能调优

### 1. 数据库优化

```sql
-- 创建索引
CREATE INDEX CONCURRENTLY idx_predictions_match_created
ON predictions(match_id, created_at);

-- 分区表
CREATE TABLE predictions_2024 PARTITION OF predictions
FOR VALUES FROM ('2024-01-01') TO ('2025-01-01');
```

### 2. Redis 配置

```conf
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 3. 应用配置

```python
# config.py
from src.core.config import Settings

settings = Settings(
    # 连接池配置
    DB_POOL_SIZE=20,
    DB_MAX_OVERFLOW=30,
    REDIS_POOL_SIZE=50,

    # 缓存配置
    CACHE_TTL_PREDICTIONS=1800,  # 30分钟
    CACHE_TTL_FEATURES=3600,     # 1小时

    # 异步配置
    MAX_CONCURRENT_PREDICTIONS=10,
    PREDICTION_TIMEOUT=30.0,
)
```

## 安全配置

### 1. HTTPS 配置

```yaml
# nginx/nginx.prod.conf
server {
    listen 443 ssl http2;
    server_name api.football-prediction.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    location / {
        proxy_pass http://app:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 2. 安全头配置

```python
# middleware/security.py
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["api.football-prediction.com", "*.football-prediction.com"]
)
app.add_middleware(HTTPSRedirectMiddleware)
```

### 3. 访问控制

```python
# rbac.py
from enum import Enum

class Role(str, Enum):
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"

PERMISSIONS = {
    Role.ADMIN: ["read", "write", "delete", "admin"],
    Role.ANALYST: ["read", "write"],
    Role.VIEWER: ["read"]
}
```

## 故障排除

### 常见问题

1. **数据库连接失败**
   ```bash
   # 检查连接字符串
   psql $DATABASE_URL -c "SELECT 1"
   ```

2. **Redis 连接超时**
   ```bash
   # 检查 Redis
   redis-cli ping
   ```

3. **内存不足**
   ```bash
   # 检查内存使用
   docker stats
   ```

### 日志查看

```bash
# 应用日志
docker-compose logs -f app

# 系统日志
journalctl -u football-prediction

# Kubernetes 日志
kubectl logs -f deployment/football-prediction -n football-prediction
```

## 更新和维护

### 滚动更新

```bash
# 1. 更新镜像
docker pull football-prediction:new-version

# 2. 更新部署
kubectl set image deployment/football-prediction \
  app=football-prediction:new-version -n football-prediction

# 3. 等待滚动更新
kubectl rollout status deployment/football-prediction -n football-prediction
```

### 备份策略

```bash
# 数据库备份
kubectl exec -it postgres-pod -- pg_dump -U user football_prod > backup.sql

# Redis 备份
kubectl exec -it redis-pod -- redis-cli BGSAVE
```

## 联系支持

如有部署问题，请联系：

- 邮箱：support@football-prediction.com
- 文档：https://docs.football-prediction.com
- GitHub Issues：https://github.com/your-org/football-prediction/issues
