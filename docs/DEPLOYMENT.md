# 🚀 部署指南

本文档提供了 FootballPrediction 系统的完整部署指南。

## 目录

- [环境要求](#环境要求)
- [本地开发环境](#本地开发环境)
- [Docker 部署](#docker-部署)
- [生产环境部署](#生产环境部署)
- [监控和日志](#监控和日志)
- [故障排除](#故障排除)

## 环境要求

### 系统要求
- **操作系统**: Linux (Ubuntu 20.04+), macOS, 或 WSL2
- **Python**: 3.11 或更高版本
- **内存**: 最少 4GB RAM，推荐 8GB+
- **存储**: 最少 20GB 可用空间

### 依赖服务
- **PostgreSQL**: 15.0 或更高版本
- **Redis**: 7.0 或更高版本
- **Docker**: 20.10 或更高版本
- **Docker Compose**: 2.0 或更高版本

## 本地开发环境

### 1. 克隆项目

```bash
git clone https://github.com/xupeng211/FootballPrediction.git
cd FootballPrediction
```

### 2. 设置 Python 环境

```bash
# 使用 pyenv 推荐
pyenv install 3.11.9
pyenv local 3.11.9

# 或使用系统 Python
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
```

### 3. 安装依赖

```bash
# 从锁文件安装依赖
make install

# 或手动安装
pip install -r requirements/requirements.lock
```

### 4. 环境配置

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
nano .env
```

必需的环境变量：
```bash
# 数据库配置
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/football_db

# Redis 配置
REDIS_URL=redis://:password@localhost:6379/0

# API 密钥
FOOTBALL_API_TOKEN=your-football-api-token
```

### 5. 启动依赖服务

```bash
# 使用 Docker Compose 启动
docker-compose up -d postgres redis

# 或使用系统服务
sudo systemctl start postgresql
sudo systemctl start redis-server
```

### 6. 运行数据库迁移

```bash
# 运行迁移
make migrate

# 或手动运行
alembic upgrade head
```

### 7. 启动应用

```bash
# 开发模式启动
make run

# 或使用 uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000/docs 查看 API 文档。

## Docker 部署

### 1. 构建镜像

```bash
# 构建生产镜像
make build

# 或手动构建
docker build -t football-prediction:latest .
```

### 2. 使用 Docker Compose

```bash
# 启动所有服务
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

### 3. Docker Compose 配置

生产环境示例 (`docker-compose.prod.yml`):

```yaml
version: '3.8'

services:
  app:
    image: football-prediction:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/football_prod
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - ENVIRONMENT=production
      - DEBUG=false
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy

  postgres:
    image: postgres:15
    environment:
      - POSTGRES_DB=football_prod
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

## 生产环境部署

### 1. 使用 Kubernetes

#### Helm Chart 安装

```bash
# 添加 Helm 仓库
helm repo add football-prediction https://charts.football-prediction.com

# 安装
helm install football-prediction football-prediction/football-prediction \
  --namespace football-prediction \
  --create-namespace \
  --set database.password=${DB_PASSWORD} \
  --set redis.password=${REDIS_PASSWORD} \
  --set api.footballToken=${FOOTBALL_API_TOKEN}
```

#### Kustomize 部署

```bash
# 应用配置
kubectl apply -k k8s/overlays/production

# 查看状态
kubectl get pods -n football-prediction
```

### 2. 使用云服务

#### AWS ECS

```bash
# 构建并推送镜像
docker build -t football-prediction:latest .
docker tag football-prediction:latest ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/football-prediction:latest
docker push ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/football-prediction:latest

# 使用 ECS CLI 部署
ecs-cli compose --project-name football-prediction \
  --file docker-compose.prod.yml \
  --cluster-config football-prediction \
  --ecs-profile football-prediction \
  up --create-log-groups
```

#### Google Cloud Run

```bash
# 构建并推送
gcloud builds submit --tag gcr.io/PROJECT_ID/football-prediction

# 部署
gcloud run deploy football-prediction \
  --image gcr.io/PROJECT_ID/football-prediction \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### 3. 蓝绿部署

使用 Nginx 实现蓝绿部署：

```nginx
upstream blue {
    server blue-app:8000;
}

upstream green {
    server green-app:8000;
}

server {
    listen 80;
    server_name football-prediction.com;

    location / {
        proxy_pass http://blue;  # 或 green
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

## 环境变量配置

### 开发环境 (.env.dev)

```bash
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

DATABASE_URL=postgresql+asyncpg://dev_user:dev_pass@localhost:5432/football_dev
REDIS_URL=redis://:dev_redis_pass@localhost:6379/0

FOOTBALL_API_TOKEN=dev_token_here
```

### 生产环境 (.env.prod)

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

DATABASE_URL=postgresql+asyncpg://prod_user:${PROD_DB_PASSWORD}@prod-db:5432/football_prod
REDIS_URL=redis://:${PROD_REDIS_PASSWORD}@prod-redis:6379/0

FOOTBALL_API_TOKEN=${FOOTBALL_API_TOKEN}

# 安全配置
SECRET_KEY=${SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}

# 监控配置
SENTRY_DSN=${SENTRY_DSN}
PROMETHEUS_ENDPOINT=http://prometheus:9090
```

## 监控和日志

### 1. Prometheus 监控

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'football-prediction'
    static_configs:
      - targets: ['football-prediction:8000']
    metrics_path: '/metrics'
```

### 2. Grafana 仪表板

预配置的 Grafana 仪表板包括：
- API 响应时间
- 数据库连接数
- Redis 使用率
- 预测准确性指标

### 3. 日志聚合

使用 ELK Stack：

```bash
# Filebeat 配置
filebeat.inputs:
- type: log
  enabled: true
  paths:
    - /var/log/football-prediction/*.log
  fields:
    app: football-prediction
  fields_under_root: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

## 健康检查

### 应用健康检查

```bash
# HTTP 健康检查
curl http://localhost:8000/health

# 详细的健康检查
curl http://localhost:8000/health/full
```

### 数据库健康检查

```bash
# PostgreSQL
pg_isready -h localhost -p 5432 -U postgres

# Redis
redis-cli -h localhost -p 6379 ping
```

## 性能调优

### 1. 数据库优化

```sql
-- 创建索引示例
CREATE INDEX CONCURRENTLY idx_matches_date ON matches(start_time);
CREATE INDEX CONCURRENTLY idx_predictions_match_id ON predictions(match_id);
```

### 2. Redis 配置

```ini
# redis.conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### 3. 应用优化

```python
# uvicorn 配置
workers = (cpu_count * 2) + 1
limit_concurrency = 1000
timeout_keep_alive = 30
```

## 故障排除

### 常见问题

#### 1. 数据库连接失败

```bash
# 检查数据库状态
docker-compose logs postgres

# 检查连接字符串
echo $DATABASE_URL

# 测试连接
psql $DATABASE_URL -c "SELECT 1"
```

#### 2. Redis 连接失败

```bash
# 检查 Redis 状态
docker-compose logs redis

# 测试连接
redis-cli -h localhost -p 6379 ping
```

#### 3. API 响应慢

```bash
# 检查日志
docker-compose logs app | grep ERROR

# 检查资源使用
docker stats

# 检查数据库慢查询
SELECT query, mean_time, calls FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;
```

#### 4. 内存泄漏

```bash
# 使用内存分析工具
pip install memory-profiler
python -m memory_profiler src/main.py

# 或使用 tracemalloc
python -m tracemalloc src/main.py
```

### 日志分析

```bash
# 查看错误日志
docker-compose logs app | grep ERROR

# 查看特定端点的错误
docker-compose logs app | grep "/predictions" | grep ERROR

# 查看性能相关日志
docker-compose logs app | grep "Slow query"
```

### 重启服务

```bash
# 重启单个服务
docker-compose restart app

# 重启所有服务
docker-compose restart
```

## 备份和恢复

### 数据库备份

```bash
# 创建备份
docker exec postgres pg_dump -U postgres football_prod > backup.sql

# 恢复
docker exec -i postgres psql -U postgres football_prod < backup.sql
```

### Redis 备份

```bash
# 创建快照
docker exec redis redis-cli BGSAVE

# 拷贝快照文件
docker cp redis:/data/dump.rdb ./backup/
```

## 安全配置

### SSL/TLS 配置

```nginx
server {
    listen 443 ssl;
    server_name football-prediction.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
}
```

### 防火墙配置

```bash
# 使用 ufw
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

## 更新和维护

### 0 停机更新

```bash
# 使用蓝绿部署
kubectl rollout status deployment/football-prediction-blue
kubectl rollout status deployment/football-prediction-green

# 切换流量
kubectl patch service football-prediction -p '{"spec":{"selector":{"version":"green"}}}'
```

### 数据库迁移

```bash
# 运行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```

### 依赖更新

```bash
# 更新依赖
pip-compile requirements/dev.in
pip install -r requirements/dev.lock

# 提交变更
git add requirements/
git commit -m "Update dependencies"
```