# 🚀 足球预测系统生产部署指南

## 📋 概述

本文档提供足球预测系统的详细生产部署指南，涵盖容器化部署、云服务配置、监控告警、数据管道和MLOps流程的完整部署方案。

## 🏗️ 系统架构

### 核心组件
- **FastAPI应用**: 主API服务，提供RESTful接口
- **PostgreSQL**: 主数据库，存储比赛数据、用户信息、预测结果
- **Redis**: 缓存层和Celery消息代理
- **Celery**: 异步任务处理（数据收集、模型训练、预测计算）
- **MLflow**: 模型生命周期管理和实验跟踪
- **Feast**: 特征存储，管理ML特征
- **Kafka**: 流式数据处理（可选）
- **Prometheus/Grafana**: 监控指标收集和可视化
- **Great Expectations**: 数据质量验证

### 部署架构图
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Load Balancer │────│     FastAPI     │────│   PostgreSQL    │
│    (ALB/Nginx)  │    │     App         │   │    Database     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │              │      Redis      │              │
         │              │    Cache/Queue  │              │
         │              └─────────────────┘              │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Prometheus    │    │     Celery      │    │     MLflow      │
│   Monitoring   │    │   Workers       │    │   Model Mgmt    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Grafana     │    │     Feast       │    │ Great Expect.   │
│  Visualization  │    │ Feature Store   │    │ Data Quality    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 环境准备

### 硬件要求
- **开发环境**: 4GB RAM, 2CPU核心
- **生产环境**: 16GB RAM, 4CPU核心 (推荐)
- **数据密集型任务**: 32GB RAM, 8CPU核心

### 软件依赖
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **Python**: 3.11+
- **PostgreSQL**: 14+
- **Redis**: 6.0+

## 📦 容器化部署

### 1. 构建Docker镜像
```bash
# 构建应用镜像
docker build -t football-prediction:latest .

# 构建特定环境镜像
docker build -t football-prediction:production --target production .
docker build -t football-prediction:development --target development .
```

### 2. Docker Compose部署
```bash
# 启动所有服务
docker-compose up -d

# 启动特定服务
docker-compose up -d postgres redis app

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f app
```

### 3. 生产环境配置
创建 `docker-compose.prod.yml`:
```yaml
version: '3.8'

services:
  app:
    image: football-prediction:production
    environment:
      - ENVIRONMENT=production
      - DATABASE_URL=postgresql://user:pass@postgres:5432/football_pred
      - REDIS_URL=redis://redis:6379
      - API_FOOTBALL_KEY=${API_FOOTBALL_KEY}
    depends_on:
      - postgres
      - redis
    ports:
      - "8000:8000"
    restart: unless-stopped

  postgres:
    image: postgres:14
    environment:
      - POSTGRES_DB=football_pred
      - POSTGRES_USER=football_user
      - POSTGRES_PASSWORD=${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped

  redis:
    image: redis:6-alpine
    ports:
      - "6379:6379"
    restart: unless-stopped

  celery_worker:
    image: football-prediction:production
    command: celery -A src.tasks.celery worker --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/football_pred
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  celery_beat:
    image: football-prediction:production
    command: celery -A src.tasks.celery beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/football_pred
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

volumes:
  postgres_data:
```

## ☁️ 云服务部署

### AWS部署方案

#### 1. ECS Fargate部署
```bash
# 创建ECS集群
aws ecs create-cluster --cluster-name football-prediction

# 创建任务定义
aws ecs register-task-definition \
  --family football-prediction-task \
  --requires-compatibilities FARGATE \
  --network-mode awsvpc \
  --cpu '2.0' \
  --memory '4.0' \
  --execution-role-arn arn:aws:iam::account:role/ecsTaskExecutionRole

# 创建服务
aws ecs create-service \
  --cluster football-prediction \
  --service-name football-prediction-service \
  --task-definition football-prediction-task \
  --desired-count 2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-12345,subnet-67890],securityGroups=[sg-12345],assignPublicIp=ENABLED}"
```

#### 2. RDS PostgreSQL配置
```bash
# 创建数据库子网组
aws rds create-db-subnet-group \
  --db-subnet-group-name football-prediction-subnet-group \
  --db-subnet-group-description "Subnet group for football prediction" \
  --subnet-ids subnet-12345 subnet-67890

# 创建数据库实例
aws rds create-db-instance \
  --db-instance-identifier football-prediction-prod \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 14.7 \
  --master-username football_user \
  --master-user-password ${DB_PASSWORD} \
  --allocated-storage 20 \
  --db-subnet-group-name football-prediction-subnet-group \
  --vpc-security-group-ids sg-12345 \
  --backup-retention-period 7 \
  --multi-az
```

#### 3. ElastiCache Redis配置
```bash
# 创建Redis子网组
aws elasticache create-cache-subnet-group \
  --cache-subnet-group-name football-prediction-redis-subnet \
  --cache-subnet-group-description "Redis subnet group" \
  --subnet-ids subnet-12345 subnet-67890

# 创建Redis集群
aws elasticache create-replication-group \
  --replication-group-id football-prediction-redis \
  --replication-group-description "Redis cluster for football prediction" \
  --cache-node-type cache.t3.micro \
  --engine redis \
  --engine-version 6.x \
  --num-cache-clusters 2 \
  --automatic-failover-enabled \
  --cache-subnet-group-name football-prediction-redis-subnet \
  --security-group-ids sg-12345
```

### Kubernetes部署方案

#### 1. Helm Chart部署
```yaml
# values.yaml
replicaCount: 3

image:
  repository: football-prediction
  tag: latest
  pullPolicy: Always

service:
  type: LoadBalancer
  port: 8000

database:
  host: postgres-service
  port: 5432
  name: football_pred
  user: football_user
  password: ${DB_PASSWORD}

redis:
  host: redis-service
  port: 6379

resources:
  limits:
    cpu: 500m
    memory: 1Gi
  requests:
    cpu: 250m
    memory: 512Mi
```

#### 2. 部署命令
```bash
# 安装Helm Chart
helm install football-prediction ./helm-chart

# 更新部署
helm upgrade football-prediction ./helm-chart

# 回滚
helm rollback football-prediction 1
```

## 🔐 安全配置

### 1. 环境变量管理
```bash
# 使用AWS Secrets Manager
aws secretsmanager create-secret \
  --name football-prediction-env \
  --description "Environment variables for football prediction"

# 在容器中获取密钥
aws secretsmanager get-secret-value \
  --secret-id football-prediction-env \
  --query SecretString \
  --output text > /app/.env
```

### 2. 网络安全
- **VPC配置**: 创建私有子网部署应用，公有子网部署负载均衡器
- **安全组**: 限制数据库和Redis仅允许应用访问
- **SSL/TLS**: 强制HTTPS，使用Let's Encrypt或AWS ACM证书

### 3. 数据安全
- **数据库加密**: 启用PostgreSQL静态加密
- **备份策略**: 每日自动备份，保留30天
- **访问控制**: 基于角色的访问控制(RBAC)

## 📊 监控和告警

### 1. Prometheus监控
```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'football-prediction'
    static_configs:
      - targets: ['app:8000']
    metrics_path: '/metrics'
    scrape_interval: 5s

  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
```

### 2. Grafana仪表板
预配置的仪表板包括：
- **系统监控**: CPU、内存、磁盘使用率
- **应用监控**: 请求响应时间、错误率、QPS
- **数据库监控**: 连接数、查询性能、慢查询
- **业务监控**: 预测准确率、数据收集状态

### 3. 告警规则
```yaml
# alertmanager.yml
groups:
  - name: football-prediction
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "Database is down"
```

## 🔄 数据管道部署

### 1. 数据收集任务
```bash
# 启动Celery worker处理数据收集
celery -A src.tasks.celery worker -Q data_collection --loglevel=info

# 查看任务状态
celery -A src.tasks.celery inspect active

# 查看统计信息
celery -A src.tasks.celery inspect stats
```

### 2. 定时任务配置
```python
# celeryconfig.py
beat_schedule = {
    'collect-daily-matches': {
        'task': 'src.tasks.data_collection.collect_daily_matches',
        'schedule': crontab(hour=0, minute=0),  # 每日午夜
    },
    'update-models': {
        'task': 'src.tasks.model_training.update_models',
        'schedule': crontab(hour=2, minute=0),  # 每日凌晨2点
    },
    'cleanup-old-data': {
        'task': 'src.tasks.data_cleanup.cleanup_old_data',
        'schedule': crontab(hour=4, minute=0),  # 每日凌晨4点
    },
}
```

## 🤖 MLOps部署

### 1. MLflow服务器配置
```bash
# 启动MLflow服务器
mlflow server \
  --host 0.0.0.0 \
  --port 5000 \
  --backend-store-uri postgresql://user:pass@host/db \
  --default-artifact-root s3://football-prediction-mlflow-artifacts/
```

### 2. 模型注册表
```python
# 注册模型
mlflow.register_model(
    "runs:/<run_id>/model",
    "football-prediction-model"
)

# 部署模型到生产
client.transition_model_version_stage(
    name="football-prediction-model",
    version=1,
    stage="Production"
)
```

### 3. 特征存储部署
```yaml
# feature_store.yaml
project: football-prediction
registry: data/registry.db

provider: local
offline_store:
  type: postgres
  host: localhost
  port: 5432
  database: football_pred

online_store:
  type: redis
  connection_string: localhost:6379
```

## 🚀 部署脚本

### 1. 自动化部署脚本
```bash
#!/bin/bash
# deploy.sh

set -e

ENVIRONMENT=${1:-development}
echo "部署到环境: $ENVIRONMENT"

# 构建镜像
echo "构建Docker镜像..."
docker build -t football-prediction:$ENVIRONMENT --target $ENVIRONMENT .

# 停止现有服务
echo "停止现有服务..."
docker-compose -f docker-compose.$ENVIRONMENT.yml down

# 启动新服务
echo "启动新服务..."
docker-compose -f docker-compose.$ENVIRONMENT.yml up -d

# 等待服务启动
echo "等待服务启动..."
sleep 30

# 健康检查
echo "执行健康检查..."
curl -f http://localhost:8000/health || exit 1

echo "部署完成！"
```

### 2. CI/CD流水线
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Login to Docker Hub
        uses: docker/login-action@v2
        with:
          username: ${{ secrets.DOCKERHUB_USERNAME }}
          password: ${{ secrets.DOCKERHUB_TOKEN }}

      - name: Build and push
        uses: docker/build-push-action@v4
        with:
          context: .
          push: true
          tags: football-prediction:latest

      - name: Deploy to ECS
        uses: aws-actions/amazon-ecs-deploy-task-definition@v1
        with:
          task-definition: task-definition.json
          service: football-prediction-service
          cluster: football-prediction
          wait-for-service-stability: true
```

## 🔍 健康检查

### 1. 应用健康检查
```bash
# 基本健康检查
curl http://localhost:8000/health

# 详细健康检查
curl http://localhost:8000/health/detailed

# 数据库连接检查
curl http://localhost:8000/health/database

# Redis连接检查
curl http://localhost:8000/health/redis
```

### 2. 监控指标
```bash
# Prometheus指标
curl http://localhost:8000/metrics

# 应用统计
curl http://localhost:8000/stats
```

## 🚨 故障排除

### 常见问题及解决方案

#### 1. 数据库连接失败
```bash
# 检查数据库状态
docker-compose exec postgres pg_isready

# 查看数据库日志
docker-compose logs postgres

# 测试连接
docker-compose exec app python -c "
from src.database.connection import get_database
import asyncio
async def test():
    db = get_database()
    print('Database connection successful')
asyncio.run(test())
"
```

#### 2. Redis连接失败
```bash
# 检查Redis状态
docker-compose exec redis redis-cli ping

# 查看Redis日志
docker-compose logs redis

# 测试连接
docker-compose exec app python -c "
from src.cache.redis_client import get_redis_client
client = get_redis_client()
print('Redis connection successful:', client.ping())
"
```

#### 3. Celery任务失败
```bash
# 查看Celery worker状态
celery -A src.tasks.celery inspect active

# 查看失败的任务
celery -A src.tasks.celery inspect scheduled

# 重新执行失败的任务
celery -A src.tasks.celery purge
```

#### 4. 内存泄漏
```bash
# 监控内存使用
docker stats

# 重启服务
docker-compose restart app

# 清理Docker缓存
docker system prune -f
```

## 📈 性能优化

### 1. 数据库优化
- **索引优化**: 为常用查询字段创建索引
- **连接池**: 配置适当的连接池大小
- **查询优化**: 使用EXPLAIN分析慢查询
- **分区表**: 对大表进行分区

### 2. 缓存优化
- **Redis缓存**: 缓存频繁访问的数据
- **应用缓存**: 使用内存缓存减少数据库查询
- **CDN缓存**: 静态资源使用CDN

### 3. 应用优化
- **异步处理**: 使用异步I/O提高并发性能
- **连接池**: 复用数据库和Redis连接
- **负载均衡**: 多实例部署提高可用性

## 🔧 维护操作

### 1. 数据库维护
```bash
# 备份数据库
docker-compose exec postgres pg_dump -U football_user football_pred > backup.sql

# 恢复数据库
docker-compose exec -T postgres psql -U football_user football_pred < backup.sql

# 清理旧数据
docker-compose exec app python -m src.scripts.cleanup_old_data
```

### 2. 日志管理
```bash
# 查看应用日志
docker-compose logs -f app

# 清理旧日志
find logs/ -name "*.log" -mtime +30 -delete

# 日志轮转配置
logrotate /etc/logrotate.d/football-prediction
```

### 3. 系统更新
```bash
# 更新依赖
pip install -r requirements.txt --upgrade

# 更新Docker镜像
docker-compose pull

# 重新部署
docker-compose up -d --force-recreate
```

## 📞 支持和文档

### 相关文档
- [API文档](http://localhost:8000/docs)
- [数据库架构](docs/DATABASE_SCHEMA.md)
- [开发指南](docs/DEVELOPMENT_GUIDE.md)
- [监控指南](docs/MONITORING_GUIDE.md)

### 获取帮助
- **GitHub Issues**: 报告Bug和功能请求
- **Wiki**: 详细的使用文档
- **Discussions**: 社区讨论和问答

---

**祝您部署顺利！** 🎉

如有问题，请参考故障排除部分或创建GitHub Issue寻求帮助。
