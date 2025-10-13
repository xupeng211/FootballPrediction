# 🚀 足球预测系统生产部署执行手册

**系统名称**: 足球预测系统 (Football Prediction System)
**版本**: Phase 6 Production Ready
**最后更新**: 2025-09-25
**文档目标**: 提供标准化、可执行的生产部署手册，确保部署过程安全、可控、可回滚

---

## 📋 执行摘要

### 🎯 手册目标

本手册旨在为足球预测系统的生产部署提供标准化的执行流程，涵盖从部署准备到验证再到回滚演练的完整环节。通过遵循本手册，确保系统部署过程的安全性、可控性和可回滚性。

### 🏗️ 上线涉及的核心组件

| 组件类别 | 组件名称 | 端口 | 关键作用 |
|---------|---------|------|---------|
| **应用服务** | FastAPI Application | 8000 | 核心API服务和预测功能 |
| **数据库** | PostgreSQL 15 | 5432 | 主数据库存储 |
| **缓存** | Redis 7 | 6379 | 缓存和会话存储 |
| **消息队列** | Kafka 3.6.1 | 9092 | 异步消息处理 |
| **模型服务** | MLflow | 5002 | 模型生命周期管理 |
| **对象存储** | MinIO | 9000 | 模型文件和数据存储 |
| **数据血缘** | Marquez | 5000 | 数据血缘追踪 |
| **监控系统** | Prometheus/Grafana | 9090/3000 | 监控告警 |
| **负载均衡** | Nginx | 80/443 | 反向代理和负载均衡 |
| **任务队列** | Celery | - | 后台任务处理 |

---

## 🔧 部署前准备

### 1. 代码和CI/CD验证

#### ✅ 检查清单：代码准备

- [ ] **主分支状态**: 确认代码已合并至 `main` 分支
- [ ] **CI/CD通过**: 最新提交的CI/CD流程全部通过
- [ ] **版本标记**: 使用正确的版本标签格式 `football-predict:phase6`
- [ ] **测试覆盖率**: 确认测试覆盖率 ≥70%
- [ ] **安全扫描**: Bandit和Safety安全扫描通过

#### 🔄 版本号规范

```bash
# 版本命名规范
football-predict:phase6              # Phase 6 生产版本
football-predict:phase6-v1.0.0       # 语义化版本
football-predict:phase6-<git-sha>    # Git SHA版本
football-predict:phase6-<timestamp>  # 时间戳版本
```

#### 📋 验证命令

```bash
# 1. 检查代码状态
git status
git log --oneline -5

# 2. 验证CI/CD状态
gh run list --limit=5

# 3. 检查测试覆盖率
./venv/bin/pytest tests/unit --cov=src --cov-report=term --cov-fail-under=70

# 4. 安全扫描验证
bandit -r src/ -f json -o bandit-latest.json
safety check --json --output safety-latest.json
```

### 2. 环境变量准备

#### 🔐 环境变量清单

```bash
# =============================================================================
# 应用基础配置
# =============================================================================
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com

# =============================================================================
# 安全配置
# =============================================================================
JWT_SECRET_KEY=your_super_secure_jwt_secret_key_here_minimum_32_characters
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# =============================================================================
# 数据库配置 - 主数据库
# =============================================================================
DB_HOST=db
DB_PORT=5432
DB_NAME=football_prediction_dev
DB_USER=football_user
DB_PASSWORD=your_secure_db_password_here

# PostgreSQL 根用户
POSTGRES_DB=football_prediction_dev
POSTGRES_USER=football_user
POSTGRES_PASSWORD=your_secure_postgres_password_here

# 多用户架构
DB_READER_USER=football_reader
DB_READER_PASSWORD=your_reader_password_here
DB_WRITER_USER=football_writer
DB_WRITER_PASSWORD=your_writer_password_here
DB_ADMIN_USER=football_admin
DB_ADMIN_PASSWORD=your_admin_password_here

# =============================================================================
# 缓存配置
# =============================================================================
REDIS_PASSWORD=your_secure_redis_password_here
REDIS_URL=redis://:your_secure_redis_password_here@redis:6379/0

# Celery 任务队列
CELERY_BROKER_URL=redis://:your_secure_redis_password_here@redis:6379/0
CELERY_RESULT_BACKEND=redis://:your_secure_redis_password_here@redis:6379/0

# =============================================================================
# 对象存储配置
# =============================================================================
MINIO_ROOT_USER=football_minio_admin
MINIO_ROOT_PASSWORD=your_secure_minio_password_here
MINIO_SECRET_KEY=your_minio_secret_key_here

# AWS (for MinIO compatibility)
AWS_ACCESS_KEY_ID=football_minio_admin
AWS_SECRET_ACCESS_KEY=your_secure_minio_password_here
AWS_DEFAULT_REGION=us-east-1

# =============================================================================
# MLflow 配置
# =============================================================================
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_EXPERIMENT_NAME=football_prediction
MLFLOW_REGISTRY_URI=http://mlflow:5000
MLFLOW_BACKEND_STORE_URI=postgresql://mlflow_user:mlflow_password@mlflow-db:5432/mlflow
MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://football-models/mlflow-artifacts
MLFLOW_S3_ENDPOINT_URL=http://minio:9000

# MLflow 数据库
MLFLOW_DB_USER=mlflow_user
MLFLOW_DB_PASSWORD=your_mlflow_password_here
MLFLOW_DB_NAME=mlflow

# =============================================================================
# 数据血缘配置
# =============================================================================
MARQUEZ_DB_USER=marquez_user
MARQUEZ_DB_PASSWORD=your_marquez_password_here
MARQUEZ_DB_NAME=marquez

# =============================================================================
# 监控配置
# =============================================================================
GRAFANA_ADMIN_PASSWORD=your_grafana_password_here

# =============================================================================
# 模型配置
# =============================================================================
MODEL_CACHE_TTL_HOURS=1
PREDICTION_CACHE_TTL_MINUTES=30
PRODUCTION_MODEL_NAME=football-match-predictor
PRODUCTION_MODEL_VERSION=latest
```

#### 📁 环境文件创建

```bash
# 1. 创建生产环境文件
cp .env.production.example .env.production

# 2. 编辑环境变量（使用安全的方式）
# 推荐使用密钥管理服务或加密的环境变量
# 或者使用安全配置管理工具

# 3. 验证环境变量
grep -E "PASSWORD|SECRET|KEY" .env.production
```

### 3. 数据库迁移检查

#### ✅ 检查清单：数据库准备

- [ ] **迁移文件完整**: 确认所有12个Alembic迁移文件存在
- [ ] **数据库备份**: 生产数据库有完整备份
- [ ] **连接测试**: 数据库连接配置正确
- [ ] **权限验证**: 数据库用户权限正确设置
- [ ] **性能配置**: 数据库性能参数优化

#### 🗄️ 数据库迁移命令

```bash
# 1. 检查迁移状态
alembic current
alembic history --verbose

# 2. 验证迁移文件
ls -la src/database/migrations/versions/
wc -l src/database/migrations/versions/*.py

# 3. 测试数据库连接
python -c "
import asyncio
from src.database.config import get_database_config
config = get_database_config()
print(f'Database URL: {config.database_url}')
"

# 4. 运行迁移（如果需要）
alembic upgrade head

# 5. 验证数据库表
python -c "
import asyncio
from src.database.connection import get_async_session
async def check_tables():
    async with get_async_session() as session:
        result = await session.execute('SELECT tablename FROM pg_tables WHERE schemaname = \'public\'')
        tables = [row[0] for row in result.fetchall()]
        print(f'Tables: {tables}')
asyncio.run(check_tables())
"
```

### 4. 模型文件与缓存预加载

#### ✅ 检查清单：模型准备

- [ ] **模型文件存在**: 确认MLflow中已注册生产模型
- [ ] **模型版本正确**: 使用正确的模型版本标签
- [ ] **Feature Store**: Feast feature store已初始化
- [ ] **缓存预热**: Redis缓存已预热
- [ ] **模型加载**: 模型加载测试通过

#### 🤖 模型验证命令

```bash
# 1. 检查MLflow模型注册
curl -s http://mlflow:5000/api/2.0/registered-models/list | jq '.registered_models[].name'

# 2. 验证生产模型版本
curl -s http://mlflow:5000/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[]'

# 3. 初始化Feature Store
python -c "
from src.features.feature_store import FootballFeatureStore
store = FootballFeatureStore()
store.initialize()
print('Feature Store initialized successfully')
"

# 4. 测试模型加载
python -c "
from src.models.prediction_service import PredictionService
service = PredictionService(mlflow_tracking_uri='http://mlflow:5000')
model = service.load_production_model()
print(f'Model loaded: {type(model)}')
"

# 5. 预热缓存
python -c "
from src.cache.redis_manager import RedisManager
redis = RedisManager()
# 预热常用数据
redis.warmup_cache()
print('Cache warmed up successfully')
"
```

---

## 🚀 部署步骤

### 1. Docker Compose 部署

#### ✅ 检查清单：部署准备

- [ ] **镜像准备**: 所有服务镜像已构建并推送
- [ ] **配置文件**: 所有配置文件已准备就绪
- [ ] **存储准备**: 数据目录和备份目录已创建
- [ ] **网络准备**: Docker网络配置正确
- [ ] **权限准备**: 文件系统权限正确设置

#### 🐳 Docker Compose 部署命令

```bash
# =============================================================================
# 1. 环境准备
# =============================================================================

# 设置环境变量
export COMPOSE_PROJECT_NAME=football-prediction-production
export DOCKER_DEFAULT_PLATFORM=linux/amd64

# 创建必要目录
mkdir -p data/{db-backups,football_lake,logs/{postgresql,redis,app}}
mkdir -p models/{trained,experiments,retrain_reports}

# 设置权限
chmod 755 data/ models/
chown -R 999:999 data/db-backups/  # PostgreSQL用户权限

# =============================================================================
# 2. 启动基础设施服务
# =============================================================================

# 启动数据库和缓存（按依赖顺序）
docker-compose up -d db redis

# 等待数据库启动完成
echo "Waiting for database to be ready..."
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'

# 启动消息队列
docker-compose up -d zookeeper kafka

# 等待Kafka启动完成
echo "Waiting for Kafka to be ready..."
timeout 60 bash -c 'until docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list; do sleep 5; done'

# =============================================================================
# 3. 启动存储和ML服务
# =============================================================================

# 启动对象存储
docker-compose up -d minio

# 等待MinIO启动完成
echo "Waiting for MinIO to be ready..."
timeout 30 bash -c 'until curl -f http://localhost:9000/minio/health/live; do sleep 2; done'

# 启动MLflow
docker-compose up -d mlflow-db mlflow

# 等待MLflow启动完成
echo "Waiting for MLflow to be ready..."
timeout 60 bash -c 'until curl -f http://localhost:5002/health; do sleep 5; done'

# =============================================================================
# 4. 启动监控服务
# =============================================================================

# 启动监控系统
docker-compose up -d prometheus grafana alertmanager

# 启动指标导出器
docker-compose up -d node-exporter postgres-exporter redis-exporter

# =============================================================================
# 5. 启动应用服务
# =============================================================================

# 启动数据血缘服务
docker-compose up -d marquez-db marquez

# 启动任务队列
docker-compose up -d celery-worker celery-beat celery-flower

# 启动应用服务
docker-compose up -d app

# 启动负载均衡
docker-compose up -d nginx

# =============================================================================
# 6. 验证启动状态
# =============================================================================

# 检查所有服务状态
docker-compose ps

# 检查服务健康状态
docker-compose exec app curl -f http://localhost:8000/health
docker-compose exec db pg_isready -U football_user
docker-compose exec redis redis-cli ping
```

### 2. Kubernetes 部署

#### ✅ 检查清单：K8s准备

- [ ] **集群连接**: kubectl配置正确
- [ ] **命名空间**: 生产命名空间已创建
- [ ] **密钥配置**: Kubernetes secrets已创建
- [ ] **配置映射**: ConfigMaps已创建
- [ ] **存储类**: PersistentVolume配置正确

#### ☸️ Kubernetes 部署命令

```bash
# =============================================================================
# 1. 命名空间准备
# =============================================================================

# 创建生产命名空间
kubectl create namespace football-production

# 设置默认命名空间
kubectl config set-context --current --namespace=football-production

# =============================================================================
# 2. 密钥和配置
# =============================================================================

# 创建数据库密钥
kubectl create secret generic db-secrets \
  --from-literal=db-user=football_user \
  --from-literal=db-password=your_secure_db_password_here \
  --from-literal=postgres-password=your_secure_postgres_password_here

# 创建Redis密钥
kubectl create secret generic redis-secrets \
  --from-literal=redis-password=your_secure_redis_password_here

# 创建应用密钥
kubectl create secret generic app-secrets \
  --from-literal=jwt-secret-key=your_super_secure_jwt_secret_key_here \
  --from-literal=minio-secret-key=your_minio_secret_key_here

# 创建ConfigMap
kubectl create configmap app-config \
  --from-file=configs/ \
  --from-literal=environment=production \
  --from-literal=log-level=INFO

# =============================================================================
# 3. 存储配置
# =============================================================================

# 创建PersistentVolumeClaims
kubectl apply -f k8s/storage/postgres-pvc.yaml
kubectl apply -f k8s/storage/redis-pvc.yaml
kubectl apply -f k8s/storage/minio-pvc.yaml

# =============================================================================
# 4. 数据库部署
# =============================================================================

# 部署PostgreSQL
kubectl apply -f k8s/database/postgres-deployment.yaml
kubectl apply -f k8s/database/postgres-service.yaml

# 等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

# 部署Redis
kubectl apply -f k8s/cache/redis-deployment.yaml
kubectl apply -f k8s/cache/redis-service.yaml

# 等待Redis就绪
kubectl wait --for=condition=ready pod -l app=redis --timeout=120s

# =============================================================================
# 5. 消息队列部署
# =============================================================================

# 部署Kafka
kubectl apply -f k8s/messaging/zookeeper-deployment.yaml
kubectl apply -f k8s/messaging/zookeeper-service.yaml
kubectl apply -f k8s/messaging/kafka-deployment.yaml
kubectl apply -f k8s/messaging/kafka-service.yaml

# =============================================================================
# 6. 存储和ML服务
# =============================================================================

# 部署MinIO
kubectl apply -f k8s/storage/minio-deployment.yaml
kubectl apply -f k8s/storage/minio-service.yaml

# 部署MLflow
kubectl apply -f k8s/ml/mlflow-deployment.yaml
kubectl apply -f k8s/ml/mlflow-service.yaml

# =============================================================================
# 7. 监控系统部署
# =============================================================================

# 部署Prometheus
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml
kubectl apply -f k8s/monitoring/prometheus-service.yaml

# 部署Grafana
kubectl apply -f k8s/monitoring/grafana-deployment.yaml
kubectl apply -f k8s/monitoring/grafana-service.yaml

# 部署AlertManager
kubectl apply -f k8s/monitoring/alertmanager-deployment.yaml
kubectl apply -f k8s/monitoring/alertmanager-service.yaml

# =============================================================================
# 8. 应用服务部署
# =============================================================================

# 部署应用
kubectl apply -f k8s/app/football-prediction-deployment.yaml
kubectl apply -f k8s/app/football-prediction-service.yaml

# 部署任务队列
kubectl apply -f k8s/tasks/celery-worker-deployment.yaml
kubectl apply -f k8s/tasks/celery-beat-deployment.yaml

# 部署Ingress
kubectl apply -f k8s/ingress/football-prediction-ingress.yaml

# =============================================================================
# 9. 验证部署
# =============================================================================

# 检查所有Pod状态
kubectl get pods -o wide

# 检查服务状态
kubectl get services

# 检查Ingress状态
kubectl get ingress
```

### 3. 服务启动顺序说明

#### 📋 启动顺序依赖图

```
1. 基础设施层
   ├── PostgreSQL (db)
   ├── Redis (redis)
   └── MinIO (minio)

2. 消息队列层
   ├── Zookeeper (zookeeper)
   └── Kafka (kafka)

3. 数据服务层
   ├── MLflow DB (mlflow-db)
   ├── Marquez DB (marquez-db)
   └── Feature Store (feast)

4. 应用服务层
   ├── MLflow (mlflow)
   ├── Marquez (marquez)
   └── Prometheus (prometheus)

5. 监控展示层
   ├── Grafana (grafana)
   ├── AlertManager (alertmanager)
   └── Exporters (node-exporter, postgres-exporter, redis-exporter)

6. 任务队列层
   ├── Celery Worker (celery-worker)
   ├── Celery Beat (celery-beat)
   └── Celery Flower (celery-flower)

7. 应用层
   ├── FastAPI App (app)
   └── Nginx (nginx)
```

### 4. 健康检查验证

#### 🏥 健康检查端点验证

```bash
# =============================================================================
# 1. 应用服务健康检查
# =============================================================================

# 主应用健康检查
curl -f http://localhost:8000/health
curl -f http://localhost:8000/health/liveness
curl -f http://localhost:8000/health/readiness

# API文档检查
curl -f http://localhost:8000/docs
curl -f http://localhost:8000/openapi.json

# =============================================================================
# 2. 数据库健康检查
# =============================================================================

# PostgreSQL健康检查
docker exec football_prediction_db pg_isready -U football_user -d football_prediction_dev

# Redis健康检查
docker exec football_prediction_redis redis-cli ping

# MLflow数据库检查
docker exec football_prediction_mlflow-db pg_isready -U mlflow_user -d mlflow

# =============================================================================
# 3. 消息队列健康检查
# =============================================================================

# Kafka健康检查
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list

# Zookeeper健康检查
docker exec football_prediction_zookeeper echo "ruok" | nc localhost 2181

# =============================================================================
# 4. 存储服务健康检查
# =============================================================================

# MinIO健康检查
curl -f http://localhost:9000/minio/health/live
curl -f http://localhost:9001/minio/health/live

# MLflow健康检查
curl -f http://localhost:5002/health

# Marquez健康检查
curl -f http://localhost:5000/api/v1/namespaces

# =============================================================================
# 5. 监控服务健康检查
# =============================================================================

# Prometheus健康检查
curl -f http://localhost:9090/-/ready

# Grafana健康检查
curl -f http://localhost:3000/api/health

# AlertManager健康检查
curl -f http://localhost:9093/-/ready

# =============================================================================
# 6. 任务队列健康检查
# =============================================================================

# Celery Flower健康检查
curl -f http://localhost:5555/

# 检查Celery工作状态
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect active
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect scheduled
```

### 5. 日志检查要点

#### 📋 日志检查清单和关键错误模式

```bash
# =============================================================================
# 1. 应用服务日志检查
# =============================================================================

# 查看应用启动日志
docker-compose logs --tail=100 app

# 关键启动信息查找
docker-compose logs app | grep -E "(Starting|Started|Ready|Listening|Database connected|Cache connected)"

# 错误日志检查
docker-compose logs app | grep -E "(ERROR|CRITICAL|Exception|Failed|Connection refused|Timeout)"

# =============================================================================
# 2. 数据库日志检查
# =============================================================================

# PostgreSQL日志
docker-compose logs --tail=50 db

# 关键数据库信息
docker-compose logs db | grep -E "(ready|accepting connections|authentication|database system is ready)"

# 数据库错误检查
docker-compose logs db | grep -E "(FATAL|ERROR|connection|authentication|permission)"

# =============================================================================
# 3. 缓存和队列日志检查
# =============================================================================

# Redis日志
docker-compose logs --tail=50 redis

# Kafka日志
docker-compose logs --tail=50 kafka

# Celery日志
docker-compose logs --tail=50 celery-worker

# =============================================================================
# 4. 监控系统日志检查
# =============================================================================

# Prometheus日志
docker-compose logs --tail=30 prometheus

# Grafana日志
docker-compose logs --tail=30 grafana

# =============================================================================
# 5. 性能指标日志检查
# =============================================================================

# 查看性能相关日志
docker-compose logs app | grep -E "(latency|response time|memory|cpu|slow query)"

# 检查数据库查询性能
docker-compose logs app | grep -E "(slow query|query.*ms|execution time)"
```

#### 🚨 关键错误模式和解决方案

| 错误模式 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `Connection refused` | 服务未启动或端口被占用 | 检查服务状态和端口配置 |
| `Database connection failed` | 数据库连接字符串错误或数据库未启动 | 验证数据库配置和状态 |
| `Authentication failed` | 用户名密码错误 | 检查环境变量和密钥配置 |
| `Module not found` | 依赖包缺失 | 检查Docker镜像构建过程 |
| `Port already in use` | 端口冲突 | 检查端口配置和占用情况 |
| `Out of memory` | 内存不足 | 增加内存限制或优化应用 |
| `Permission denied` | 文件权限问题 | 检查文件系统权限 |

---

## ✅ 部署后验证

### 1. 功能验证

#### ✅ 检查清单：功能验证

- [ ] **API服务响应**: 所有核心API接口正常响应
- [ ] **数据库读写**: 数据库连接正常，读写操作成功
- [ ] **缓存功能**: Redis缓存读写正常
- [ ] **模型预测**: 模型加载和预测功能正常
- [ ] **任务队列**: Celery任务正常执行
- [ ] **文件存储**: MinIO文件上传下载正常

#### 🧪 API 核心接口调用测试

```bash
# =============================================================================
# 1. 基础API测试
# =============================================================================

# 服务信息测试
curl -X GET http://localhost:8000/ \
  -H "Content-Type: application/json" \
  | jq .

# 健康检查测试
curl -X GET http://localhost:8000/health \
  -H "Content-Type: application/json" \
  | jq .

# API文档访问测试
curl -X GET http://localhost:8000/docs \
  -I

# =============================================================================
# 2. 预测功能测试
# =============================================================================

# 获取预测接口文档
curl -X GET http://localhost:8000/api/v1/predictions/ \
  -H "Content-Type: application/json" \
  | jq .

# 创建预测请求
curl -X POST http://localhost:8000/api/v1/predictions/ \
  -H "Content-Type: application/json" \
  -d '{
    "match_id": "test_match_001",
    "home_team_id": 1,
    "away_team_id": 2,
    "league_id": 1,
    "match_date": "2025-09-25T15:00:00Z"
  }' \
  | jq .

# 获取预测结果
curl -X GET http://localhost:8000/api/v1/predictions/test_prediction_001 \
  -H "Content-Type: application/json" \
  | jq .

# =============================================================================
# 3. 数据接口测试
# =============================================================================

# 获取比赛数据
curl -X GET http://localhost:8000/api/v1/data/matches?limit=5 \
  -H "Content-Type: application/json" \
  | jq .

# 获取队伍数据
curl -X GET http://localhost:8000/api/v1/data/teams?limit=5 \
  -H "Content-Type: application/json" \
  | jq .

# 获取特征数据
curl -X GET http://localhost:8000/api/v1/features/ \
  -H "Content-Type: application/json" \
  | jq .

# 获取队伍特征
curl -X GET http://localhost:8000/api/v1/features/teams/1 \
  -H "Content-Type: application/json" \
  | jq .

# =============================================================================
# 4. 监控接口测试
# =============================================================================

# 获取系统指标
curl -X GET http://localhost:8000/api/v1/monitoring/metrics \
  -H "Content-Type: application/json" \
  | jq .

# 获取Prometheus指标
curl -X GET http://localhost:8000/metrics \
  | head -20
```

#### 🗄️ 数据库读写验证

```bash
# =============================================================================
# 1. 数据库连接验证
# =============================================================================

# 创建数据库连接测试脚本
cat > db_test.py << 'EOF'
import asyncio
import sys
import os
sys.path.append('/home/user/projects/FootballPrediction')

from src.database.connection import get_async_session
from src.database.models import League, Team, Match

async def test_database_operations():
    """测试数据库读写操作"""
    try:
        async with get_async_session() as session:
            # 测试读取
            result = await session.execute("SELECT COUNT(*) FROM leagues")
            league_count = result.scalar()
            print(f"✅ Leagues count: {league_count}")

            result = await session.execute("SELECT COUNT(*) FROM teams")
            team_count = result.scalar()
            print(f"✅ Teams count: {team_count}")

            result = await session.execute("SELECT COUNT(*) FROM matches")
            match_count = result.scalar()
            print(f"✅ Matches count: {match_count}")

            # 测试写入
            await session.execute("INSERT INTO audit_logs (action, table_name, record_id, success, duration_ms) VALUES ('TEST', 'test_table', 'test_id', true, 100)")
            await session.commit()
            print("✅ Test write successful")

            return True

    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_operations())
    sys.exit(0 if success else 1)
EOF

# 运行数据库测试
python db_test.py

# =============================================================================
# 2. 数据一致性验证
# =============================================================================

# 检查数据库表完整性
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"

# 检查索引完整性
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
"

# =============================================================================
# 3. 缓存读写验证
# =============================================================================

# 创建缓存测试脚本
cat > cache_test.py << 'EOF'
import asyncio
import sys
import os
sys.path.append('/home/user/projects/FootballPrediction')

from src.cache.redis_manager import RedisManager

async def test_cache_operations():
    """测试缓存读写操作"""
    try:
        redis = RedisManager()

        # 测试写入
        await redis.set("test_key", "test_value", ttl=300)
        print("✅ Cache write successful")

        # 测试读取
        value = await redis.get("test_key")
        print(f"✅ Cache read successful: {value}")

        # 测试删除
        await redis.delete("test_key")
        print("✅ Cache delete successful")

        # 测试缓存命中率
        await redis.set("hit_test", "hit_value", ttl=300)
        await redis.get("hit_test")  # Hit
        await redis.get("miss_test")  # Miss
        print("✅ Cache hit/miss test completed")

        return True

    except Exception as e:
        print(f"❌ Cache test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_cache_operations())
    sys.exit(0 if success else 1)
EOF

# 运行缓存测试
python cache_test.py
```

#### 🤖 模型预测结果正确性检查

```bash
# =============================================================================
# 1. 模型加载验证
# =============================================================================

# 创建模型测试脚本
cat > model_test.py << 'EOF'
import asyncio
import sys
import os
sys.path.append('/home/user/projects/FootballPrediction')

from src.models.prediction_service import PredictionService

async def test_model_prediction():
    """测试模型预测功能"""
    try:
        # 初始化预测服务
        service = PredictionService(
            mlflow_tracking_uri="http://localhost:5002",
            feature_store_redis_url="redis://:your_redis_password@redis:6379/0"
        )

        # 加载生产模型
        model = service.load_production_model()
        print(f"✅ Model loaded: {type(model)}")

        # 准备测试数据
        test_features = {
            "home_team_goals_recent": 2.5,
            "away_team_goals_recent": 1.2,
            "home_team_wins_recent": 0.7,
            "away_team_wins_recent": 0.4,
            "home_team_xg": 1.8,
            "away_team_xg": 1.1,
            "league_importance": 0.8,
            "home_advantage": 0.2
        }

        # 执行预测
        prediction = await service.predict_match(
            match_id="test_match_001",
            home_team_id=1,
            away_team_id=2,
            features=test_features
        )

        print(f"✅ Prediction successful: {prediction}")

        # 验证预测结果格式
        assert "prediction_id" in prediction
        assert "home_win_probability" in prediction
        assert "draw_probability" in prediction
        assert "away_win_probability" in prediction
        assert "confidence" in prediction

        # 验证概率总和
        total_prob = (prediction["home_win_probability"] +
                     prediction["draw_probability"] +
                     prediction["away_win_probability"])
        assert abs(total_prob - 1.0) < 0.01, f"Probabilities sum to {total_prob}"

        print("✅ Prediction format validation passed")

        return True

    except Exception as e:
        print(f"❌ Model prediction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_model_prediction())
    sys.exit(0 if success else 1)
EOF

# 运行模型测试
python model_test.py

# =============================================================================
# 2. 模型性能验证
# =============================================================================

# 检查模型版本和元数据
curl -s http://localhost:5002/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[] | {version, status, creation_timestamp}'

# 验证模型文件存在
docker exec football_prediction_mlflow ls -la /mlflow-artifacts/

# 检查模型性能指标
curl -s http://localhost:5002/api/2.0/mlflow/runs/search | jq '.runs[] | select(.tags.mlflow.runName | contains("production")) | {run_id, metrics}'
```

### 2. 性能验证

#### ✅ 检查清单：性能验证

- [ ] **响应时间**: API响应时间在可接受范围内
- [ ] **吞吐量**: 系统支持预期的并发请求量
- [ ] **资源使用**: CPU、内存、磁盘使用正常
- [ ] **数据库性能**: 查询响应时间正常
- [ ] **缓存效率**: 缓存命中率符合预期
- [ ] **错误率**: 系统错误率低于阈值

#### ⚡ 基础压力测试

```bash
# =============================================================================
# 1. 使用Apache Bench进行API压力测试
# =============================================================================

# 健康检查接口测试
ab -n 1000 -c 10 -t 30 http://localhost:8000/health

# API接口测试
ab -n 500 -c 20 -t 60 -H "Content-Type: application/json" \
  -p test_payload.json \
  http://localhost:8000/api/v1/predictions/

# 创建测试负载文件
cat > test_payload.json << 'EOF'
{
  "match_id": "stress_test_001",
  "home_team_id": 1,
  "away_team_id": 2,
  "league_id": 1,
  "match_date": "2025-09-25T15:00:00Z"
}
EOF

# 并发测试不同并发级别
for concurrency in 5 10 20 50; do
  echo "Testing with $concurrency concurrent users..."
  ab -n 200 -c $concurrency -t 30 http://localhost:8000/health
  echo "---"
done

# =============================================================================
# 2. 使用Locust进行分布式负载测试
# =============================================================================

# 创建Locust测试文件
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between
import json

class FootballPredictionUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        """用户开始时的初始化"""
        self.headers = {"Content-Type": "application/json"}

    @task(3)
    def health_check(self):
        """健康检查任务"""
        self.client.get("/health")

    @task(2)
    def get_predictions(self):
        """获取预测任务"""
        self.client.get("/api/v1/predictions/")

    @task(1)
    def create_prediction(self):
        """创建预测任务"""
        payload = {
            "match_id": f"locust_test_{self.environment}",
            "home_team_id": 1,
            "away_team_id": 2,
            "league_id": 1,
            "match_date": "2025-09-25T15:00:00Z"
        }
        self.client.post("/api/v1/predictions/", json=payload)

    @task(1)
    def get_features(self):
        """获取特征任务"""
        self.client.get("/api/v1/features/")
EOF

# 启动Locust测试（需要先安装locust）
# locust -f locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=5m

# =============================================================================
# 3. 使用k6进行现代化性能测试
# =============================================================================

# 创建k6测试脚本
cat > k6_test.js << 'EOF'
import http from 'k6/http';
import { check, sleep } from 'k6';

export let options = {
    stages: [
        { duration: '30s', target: 10 },  // 预热
        { duration: '1m', target: 30 },   // 负载增加
        { duration: '2m', target: 50 },   // 稳定负载
        { duration: '30s', target: 0 },   // 冷却
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95%请求响应时间<500ms
        http_req_failed: ['rate<0.01'],   // 错误率<1%
    },
};

export default function () {
    // 健康检查
    let healthRes = http.get('http://localhost:8000/health');
    check(healthRes, {
        'health status is 200': (r) => r.status === 200,
    });

    // 获取预测列表
    let predictionsRes = http.get('http://localhost:8000/api/v1/predictions/');
    check(predictionsRes, {
        'predictions status is 200': (r) => r.status === 200,
    });

    // 创建预测
    let payload = JSON.stringify({
        match_id: `k6_test_${__VU}`,
        home_team_id: 1,
        away_team_id: 2,
        league_id: 1,
        match_date: "2025-09-25T15:00:00Z"
    });

    let createRes = http.post('http://localhost:8000/api/v1/predictions/', payload);
    check(createRes, {
        'create prediction status is 200': (r) => r.status === 200,
    });

    sleep(1);
}
EOF

# 运行k6测试（需要先安装k6）
# k6 run k6_test.js

# =============================================================================
# 4. 数据库性能测试
# =============================================================================

# 数据库查询性能测试
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
EXPLAIN ANALYZE SELECT * FROM matches LIMIT 100;
"

docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
EXPLAIN ANALYZE SELECT * FROM predictions WHERE confidence > 0.8 LIMIT 50;
"

# 连接池测试
cat > db_pool_test.py << 'EOF'
import asyncio
import time
import sys
sys.path.append('/home/user/projects/FootballPrediction')

from src.database.connection import get_async_session

async def test_database_pool():
    """测试数据库连接池性能"""
    start_time = time.time()

    # 并发查询测试
    tasks = []
    for i in range(50):
        task = asyncio.create_task(test_query(f"test_query_{i}"))
        tasks.append(task)

    results = await asyncio.gather(*tasks, return_exceptions=True)

    end_time = time.time()
    duration = end_time - start_time

    successful = sum(1 for r in results if not isinstance(r, Exception))
    failed = len(results) - successful

    print(f"✅ Database pool test completed:")
    print(f"   Total queries: {len(results)}")
    print(f"   Successful: {successful}")
    print(f"   Failed: {failed}")
    print(f"   Duration: {duration:.2f}s")
    print(f"   QPS: {len(results)/duration:.2f}")

    return failed == 0

async def test_query(query_id):
    """执行单个查询"""
    try:
        async with get_async_session() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        print(f"Query {query_id} failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_database_pool())
    sys.exit(0 if success else 1)
EOF

# 运行数据库池测试
python db_pool_test.py
```

#### 📊 性能基准指标

| 指标 | 健康检查 | 预测接口 | 特征接口 | 阈值 |
|------|---------|---------|---------|------|
| **响应时间** | < 50ms | < 500ms | < 200ms | 95% < 500ms |
| **吞吐量** | > 1000 RPM | > 200 RPM | > 500 RPM | 根据业务需求 |
| **错误率** | < 0.1% | < 1% | < 0.5% | < 1% |
| **CPU使用率** | < 30% | < 70% | < 50% | < 80% |
| **内存使用** | < 512MB | < 1GB | < 768MB | < 2GB |
| **数据库连接** | < 50 | < 100 | < 80 | < 150 |

### 3. 监控验证

#### ✅ 检查清单：监控验证

- [ ] **Grafana仪表盘**: 所有仪表盘加载正常
- [ ] **Prometheus指标**: 指标数据正常采集
- [ **AlertManager配置**: 告警规则和通知配置正确
- [ ] **告警推送**: 告警通知正常发送
- [ ] **日志聚合**: 日志收集和查询正常
- [ ] **业务指标**: 业务监控指标正常显示

#### 📈 Grafana 仪表盘验证

```bash
# =============================================================================
# 1. Grafana服务访问验证
# =============================================================================

# 检查Grafana服务状态
curl -f http://localhost:3000/api/health

# 检查数据源配置
curl -u admin:your_grafana_password http://localhost:3000/api/datasources | jq '.[].name'

# 检查仪表盘列表
curl -u admin:your_grafana_password http://localhost:3000/api/search | jq '.[].title'

# =============================================================================
# 2. 仪表盘加载测试
# =============================================================================

# 检查主要仪表盘
DASHBOARDS=(
    "足球预测系统监控仪表盘"
    "系统概览"
    "API性能"
    "数据库性能"
    "缓存性能"
    "任务队列"
    "模型性能"
)

for dashboard in "${DASHBOARDS[@]}"; do
    echo "Checking dashboard: $dashboard"
    dashboard_uid=$(curl -s -u admin:your_grafana_password \
        "http://localhost:3000/api/search?query=$dashboard" | \
        jq -r '.[0].uid')

    if [ "$dashboard_uid" != "null" ]; then
        # 检查仪表盘加载
        curl -s -u admin:your_grafana_password \
            "http://localhost:3000/api/dashboards/uid/$dashboard_uid" | \
            jq '.dashboard.title'
        echo "✅ Dashboard loaded successfully"
    else
        echo "❌ Dashboard not found: $dashboard"
    fi
done

# =============================================================================
# 3. 面板数据验证
# =============================================================================

# 检查关键指标是否正常显示
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=up" | \
    jq '.data.result[]'

# 检查API响应时间指标
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=football_prediction_latency_seconds_sum" | \
    jq '.data.result[]'

# 检查数据库连接指标
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=pg_stat_database_numbackends" | \
    jq '.data.result[]'
```

#### 🚨 Prometheus 规则触发测试

```bash
# =============================================================================
# 1. Prometheus 服务验证
# =============================================================================

# 检查Prometheus健康状态
curl -f http://localhost:9090/-/ready

# 检查目标状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {health, labels}'

# 检查规则配置
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | {name, rules}'

# =============================================================================
# 2. 告警规则测试
# =============================================================================

# 检查告警规则状态
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {name, state, labels}'

# 检查告警规则加载
curl -s http://localhost:9090/api/v1/rules?type=alert | jq '.data.groups[].rules[] | {name, health, lastError}'

# =============================================================================
# 3. 模拟告警触发
# =============================================================================

# 创建高CPU使用率告警测试
docker exec football_prediction_app sh -c "dd if=/dev/zero of=/dev/null bs=1G count=10 &"

# 检查CPU使用率告警是否触发
sleep 30
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="HighCpuUsage")'

# 停止CPU压力测试
docker exec football_prediction_app pkill dd

# =============================================================================
# 4. AlertManager 通知测试
# =============================================================================

# 检查AlertManager配置
curl -f http://localhost:9093/-/ready

# 检查告警路由配置
curl -s http://localhost:9093/api/v1/alerts/groups | jq '.[] | {receiver, alerts}'

# 发送测试告警
curl -X POST http://localhost:9093/api/v1/alerts \
  -H "Content-Type: application/json" \
  -d '[
    {
      "labels": {
        "alertname": "TestAlert",
        "severity": "warning",
        "component": "test"
      },
      "annotations": {
        "summary": "This is a test alert",
        "description": "Test alert notification"
      }
    }
  ]'

# =============================================================================
# 5. 监控指标验证
# =============================================================================

# 检查应用指标
curl -s http://localhost:8000/metrics | grep -E "football_predictions_total|football_prediction_latency_seconds"

# 检查系统指标
curl -s http://localhost:9100/metrics | grep node_cpu_seconds_total

# 检查数据库指标
curl -s http://localhost:9187/metrics | grep pg_stat_database

# 检查Redis指标
curl -s http://localhost:9121/metrics | grep redis_keyspace_hits_total
```

---

## 🔄 回滚演练

### 1. 容器回滚

#### ✅ 检查清单：容器回滚准备

- [ ] **镜像备份**: 确保有可用的回滚镜像
- [ ] **版本记录**: 记录当前部署版本信息
- [ ] **回滚脚本**: 回滚脚本准备就绪
- [ ] **数据备份**: 数据库和缓存已备份
- [ ] **回滚验证**: 回滚验证步骤明确

#### 🐳 使用上一版本镜像快速回退

```bash
# =============================================================================
# 1. 回滚准备
# =============================================================================

# 记录当前版本信息
echo "=== Current Deployment Information ===" > rollback_log.txt
echo "Timestamp: $(date)" >> rollback_log.txt
echo "Current Git SHA: $(git rev-parse HEAD)" >> rollback_log.txt
echo "Current Docker Images:" >> rollback_log.txt
docker-compose images >> rollback_log.txt

# 保存当前配置
cp docker-compose.yml docker-compose.yml.current
cp .env.production .env.production.backup

# 获取上一个可用的Git SHA
PREVIOUS_SHA=$(git rev-parse HEAD^)
echo "Previous SHA: $PREVIOUS_SHA" >> rollback_log.txt

# =============================================================================
# 2. Docker Compose 回滚
# =============================================================================

# 方法1: 使用Makefile回滚
make rollback TAG=$PREVIOUS_SHA

# 方法2: 手动回滚步骤
echo "=== Starting Docker Compose Rollback ===" >> rollback_log.txt

# 停止当前服务
docker-compose down

# 拉取上一个版本的镜像
docker pull football-predict:phase6-$PREVIOUS_SHA

# 修改docker-compose.yml使用上一个版本
sed -i "s/football-predict:phase6-.*/football-predict:phase6-$PREVIOUS_SHA/g" docker-compose.yml

# 重新启动服务
docker-compose up -d

# 等待服务启动
sleep 30

# 验证服务状态
docker-compose ps >> rollback_log.txt

# =============================================================================
# 3. 验证回滚成功
# =============================================================================

echo "=== Verifying Rollback ===" >> rollback_log.txt

# 检查服务健康状态
curl -f http://localhost:8000/health >> rollback_log.txt 2>&1

# 检查API版本信息
curl -s http://localhost:8000/ | jq -r '.version' >> rollback_log.txt 2>&1

# 验证数据库连接
docker exec football_prediction_db pg_isready -U football_user >> rollback_log.txt 2>&1

# 运行基本功能测试
python -c "
import asyncio
import sys
sys.path.append('/home/user/projects/FootballPrediction')
from src.database.connection import get_async_session

async def test_connection():
    try:
        async with get_async_session() as session:
            result = await session.execute('SELECT 1')
            print('✅ Database connection successful')
            return True
    except Exception as e:
        print(f'❌ Database connection failed: {e}')
        return False

asyncio.run(test_connection())
" >> rollback_log.txt 2>&1

echo "Rollback completed at $(date)" >> rollback_log.txt
echo "Rollback log saved to rollback_log.txt"
```

#### ☸️ Kubernetes 回滚

```bash
# =============================================================================
# 1. Kubernetes 回滚准备
# =============================================================================

# 记录当前状态
echo "=== Current Kubernetes State ===" > k8s_rollback_log.txt
echo "Timestamp: $(date)" >> k8s_rollback_log.txt
kubectl get pods -o wide >> k8s_rollback_log.txt
kubectl get deployments >> k8s_rollback_log.txt

# 获取当前部署版本
CURRENT_REVISION=$(kubectl rollout history deployment/football-prediction | grep "REVISION" | tail -1 | awk '{print $1}')
echo "Current revision: $CURRENT_REVISION" >> k8s_rollback_log.txt

# =============================================================================
# 2. 执行回滚
# =============================================================================

echo "=== Starting Kubernetes Rollback ===" >> k8s_rollback_log.txt

# 方法1: 回滚到上一个版本
kubectl rollout undo deployment/football-prediction

# 方法2: 回滚到特定版本
# kubectl rollout undo deployment/football-prediction --to-revision=2

# 等待回滚完成
kubectl rollout status deployment/football-prediction --timeout=300s

# =============================================================================
# 3. 验证回滚
# =============================================================================

echo "=== Verifying Kubernetes Rollback ===" >> k8s_rollback_log.txt

# 检查Pod状态
kubectl get pods -l app=football-prediction >> k8s_rollback_log.txt

# 检查新版本
NEW_REVISION=$(kubectl rollout history deployment/football-prediction | grep "REVISION" | tail -1 | awk '{print $1}')
echo "New revision: $NEW_REVISION" >> k8s_rollback_log.txt

# 检查服务访问
SERVICE_IP=$(kubectl get service football-prediction -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$SERVICE_IP" ]; then
    SERVICE_IP=$(kubectl get service football-prediction -o jsonpath='{.status.clusterIP}')
fi

curl -f http://$SERVICE_IP:8000/health >> k8s_rollback_log.txt 2>&1

echo "Kubernetes rollback completed at $(date)" >> k8s_rollback_log.txt
```

### 2. 数据库回滚

#### ✅ 检查清单：数据库回滚准备

- [ ] **完整备份**: 有时间点最近的完整数据库备份
- [ **WAL归档**: WAL日志归档正常
- [ ] **回滚脚本**: 数据库回滚脚本准备就绪
- [ ] **迁移记录**: 数据库迁移版本记录完整
- [ ] **数据一致性**: 回滚后数据一致性验证方法

#### 🗄️ 从备份恢复

```bash
# =============================================================================
# 1. 数据库备份检查
# =============================================================================

# 检查最新备份
ls -la data/db-backups/full/ | tail -5

# 检查备份完整性
docker exec football_prediction_dbBackup sh -c "
ls -la /backups/full/ | tail -5
for backup in /backups/full/*.sql; do
    echo \"Checking \$backup\"
    head -10 \"\$backup\"
done
"

# =============================================================================
# 2. 数据库回滚步骤
# =============================================================================

# 创建数据库回滚脚本
cat > db_rollback.sh << 'EOF'
#!/bin/bash
set -e  # 遇到错误立即退出

echo "=== Database Rollback Started at $(date) ==="

# 停止应用服务以避免写入
echo "Stopping application services..."
docker-compose stop app celery-worker celery-beat

# 等待应用完全停止
sleep 10

# 记录回滚前状态
echo "Recording pre-rollback state..."
docker exec football_prediction_db pg_dump -U football_user -d football_prediction_dev > pre_rollback_backup_$(date +%Y%m%d_%H%M%S).sql

# 选择回滚点
echo "Available backups:"
ls -la data/db-backups/full/ | tail -10

# 提示用户选择备份文件
read -p "Enter backup file to restore (e.g., football_prediction_dev_20250925_120000.sql): " BACKUP_FILE

if [ ! -f "data/db-backups/full/$BACKUP_FILE" ]; then
    echo "❌ Backup file not found: $BACKUP_FILE"
    exit 1
fi

# 执行回滚
echo "Starting database restore from $BACKUP_FILE..."

# 创建临时数据库
docker exec football_prediction_db psql -U postgres -c "DROP DATABASE IF EXISTS football_prediction_dev_temp;"
docker exec football_prediction_db psql -U postgres -c "CREATE DATABASE football_prediction_dev_temp WITH TEMPLATE football_prediction_dev;"

# 恢复到临时数据库
docker exec -i football_prediction_db psql -U football_user -d football_prediction_dev_temp < data/db-backups/full/$BACKUP_FILE

# 验证恢复的数据
echo "Verifying restored data..."
docker exec football_prediction_db psql -U football_user -d football_prediction_dev_temp -c "SELECT COUNT(*) FROM matches;"

# 如果验证成功，替换原数据库
echo "Replacing production database..."
docker exec football_prediction_db psql -U postgres -c "DROP DATABASE football_prediction_dev;"
docker exec football_prediction_db psql -U postgres -c "ALTER DATABASE football_prediction_dev_temp RENAME TO football_prediction_dev;"

# 重新启动应用服务
echo "Restarting application services..."
docker-compose up -d app celery-worker celery-beat

# 等待服务启动
sleep 30

# 验证服务状态
echo "Verifying service health..."
curl -f http://localhost:8000/health

echo "✅ Database rollback completed successfully at $(date)"
EOF

# 使脚本可执行
chmod +x db_rollback.sh

# =============================================================================
# 3. 执行数据库回滚
# =============================================================================

# 注意：这是一个危险操作，请谨慎执行
# ./db_rollback.sh

# =============================================================================
# 4. 使用时间点恢复 (PITR)
# =============================================================================

# 如果启用了WAL归档，可以使用时间点恢复
cat > point_in_time_recovery.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Point-in-Time Recovery Started ==="

# 停止应用
docker-compose stop app celery-worker celery-beat

# 创建恢复目录
mkdir -p recovery/$(date +%Y%m%d_%H%M%S)
cd recovery/$(date +%Y%m%d_%H%M%S)

# 复制备份文件
cp ../../data/db-backups/full/football_prediction_dev_20250925_120000.sql .

# 设置恢复时间
read -p "Enter recovery time (YYYY-MM-DD HH:MM:SS): " RECOVERY_TIME

# 创建恢复配置文件
cat > recovery.conf << EOF
restore_command = 'cp /backups/wal/%f %p'
recovery_target_time = '$RECOVERY_TIME'
recovery_target_action = 'promote'
EOF

# 执行恢复
echo "Starting point-in-time recovery..."
docker exec football_prediction_db sh -c "
    # 停止PostgreSQL
    pg_ctl stop -D /var/lib/postgresql/data

    # 恢复基础备份
    rm -rf /var/lib/postgresql/data/*
    initdb -D /var/lib/postgresql/data

    # 配置恢复
    cp recovery.conf /var/lib/postgresql/data/

    # 启动恢复模式
    pg_ctl start -D /var/lib/postgresql/data

    # 等待恢复完成
    while [ ! -f /var/lib/postgresql/data/recovery.done ]; do
        sleep 5
    done

    # 重启为正常模式
    pg_ctl restart -D /var/lib/postgresql/data
"

echo "✅ Point-in-time recovery completed"
EOF

chmod +x point_in_time_recovery.sh
```

#### 🔄 Alembic Downgrade 示例

```bash
# =============================================================================
# 1. 检查当前迁移状态
# =============================================================================

# 查看当前迁移版本
alembic current

# 查看迁移历史
alembic history --verbose

# =============================================================================
# 2. 执行回滚迁移
# =============================================================================

# 回滚到上一个版本
alembic downgrade -1

# 回滚到特定版本
alembic downgrade d56c8d0d5aa0  # 回滚到初始版本

# 查看回滚后的状态
alembic current

# =============================================================================
# 3. 验证回滚结果
# =============================================================================

# 检查数据库表结构
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"

# 检查索引
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
"

# =============================================================================
# 4. 批量迁移回滚脚本
# =============================================================================

cat > migration_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Migration Rollback Script ==="

# 记录当前状态
echo "Current migration status:"
alembic current > migration_status_before.txt

# 获取目标版本（回滚3个版本）
TARGET_VERSION=$(alembic history | head -4 | tail -1 | awk '{print $1}')
echo "Target version: $TARGET_VERSION"

# 执行回滚
echo "Executing migration rollback..."
alembic downgrade $TARGET_VERSION

# 验证回滚
echo "Verifying rollback..."
alembic current > migration_status_after.txt

# 比较回滚前后状态
echo "Migration status comparison:"
echo "Before: $(cat migration_status_before.txt)"
echo "After: $(cat migration_status_after.txt)"

# 数据库结构验证
echo "Database structure verification:"
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public';
"

echo "✅ Migration rollback completed"
EOF

chmod +x migration_rollback.sh
```

### 3. 配置回滚

#### ✅ 检查清单：配置回滚准备

- [ ] **配置备份**: 当前环境配置文件已备份
- [ ] **版本控制**: 配置文件在版本控制中
- [ ] **回滚脚本**: 配置回滚脚本准备就绪
- [ ] **环境变量**: 环境变量回滚方案明确
- [ ] **配置验证**: 配置回滚后的验证方法

#### 🔄 环境变量恢复流程

```bash
# =============================================================================
# 1. 配置文件备份
# =============================================================================

# 创建配置备份目录
mkdir -p config_backup/$(date +%Y%m%d_%H%M%S)

# 备份当前配置
cp .env.production config_backup/$(date +%Y%m%d_%H%M%S)/
cp docker-compose.yml config_backup/$(date +%Y%m%d_%H%M%S)/
cp configs/* config_backup/$(date +%Y%m%d_%H%M%S)/

echo "Configuration backed up to config_backup/$(date +%Y%m%d_%H%M%S)/"

# =============================================================================
# 2. 配置回滚脚本
# =============================================================================

cat > config_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Configuration Rollback Script ==="

# 记录当前配置
echo "Current configuration backup:"
ls -la config_backup/ | tail -5

# 选择回滚点
read -p "Enter backup timestamp to restore (e.g., 20250925_120000): " BACKUP_TIMESTAMP

BACKUP_DIR="config_backup/$BACKUP_TIMESTAMP"

if [ ! -d "$BACKUP_DIR" ]; then
    echo "❌ Backup directory not found: $BACKUP_DIR"
    exit 1
fi

# 验证备份文件
echo "Verifying backup files..."
for file in .env.production docker-compose.yml; do
    if [ ! -f "$BACKUP_DIR/$file" ]; then
        echo "❌ Missing backup file: $file"
        exit 1
    fi
done

# 停止服务
echo "Stopping services..."
docker-compose down

# 恢复配置文件
echo "Restoring configuration files..."
cp "$BACKUP_DIR/.env.production" .env.production
cp "$BACKUP_DIR/docker-compose.yml" docker-compose.yml

if [ -d "$BACKUP_DIR/configs" ]; then
    cp -r "$BACKUP_DIR/configs/"* configs/
fi

# 验证恢复的配置
echo "Verifying restored configuration..."
echo "Environment file:"
grep -E "ENVIRONMENT|DB_PASSWORD|REDIS_PASSWORD" .env.production

echo "Docker Compose configuration:"
grep -E "image.*football-predict" docker-compose.yml

# 重新启动服务
echo "Restarting services with restored configuration..."
docker-compose up -d

# 等待服务启动
sleep 30

# 验证服务状态
echo "Verifying service health..."
curl -f http://localhost:8000/health

echo "✅ Configuration rollback completed successfully"
EOF

chmod +x config_rollback.sh

# =============================================================================
# 3. 部分配置回滚
# =============================================================================

cat > partial_config_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Partial Configuration Rollback ==="

# 备份当前特定配置
echo "Backing up specific configurations..."
cp .env.production .env.production.backup_$(date +%Y%m%d_%H%M%S)

# 选择回滚项目
echo "Available configuration items to rollback:"
echo "1. Database passwords"
echo "2. Redis configuration"
echo "3. API endpoints"
echo "4. Monitoring settings"
echo "5. Model settings"

read -p "Enter item number to rollback (1-5): " ITEM_NUMBER

case $ITEM_NUMBER in
    1)
        echo "Rolling back database passwords..."
        # 从备份恢复数据库密码
        sed -i 's/DB_PASSWORD=.*/DB_PASSWORD=previous_password_here/' .env.production
        sed -i 's/POSTGRES_PASSWORD=.*/POSTGRES_PASSWORD=previous_postgres_password_here/' .env.production
        ;;
    2)
        echo "Rolling back Redis configuration..."
        sed -i 's/REDIS_PASSWORD=.*/REDIS_PASSWORD=previous_redis_password_here/' .env.production
        sed -i 's/REDIS_URL=.*/REDIS_URL=redis://:previous_redis_password_here@redis:6379\/0/' .env.production
        ;;
    3)
        echo "Rolling back API endpoints..."
        sed -i 's/API_HOST=.*/API_HOST=0.0.0.0/' .env.production
        sed -i 's/API_PORT=.*/API_PORT=8000/' .env.production
        ;;
    4)
        echo "Rolling back monitoring settings..."
        sed -i 's/GRAFANA_ADMIN_PASSWORD=.*/GRAFANA_ADMIN_PASSWORD=previous_grafana_password/' .env.production
        ;;
    5)
        echo "Rolling back model settings..."
        sed -i 's/MODEL_CACHE_TTL_HOURS=.*/MODEL_CACHE_TTL_HOURS=1/' .env.production
        sed -i 's/PRODUCTION_MODEL_VERSION=.*/PRODUCTION_MODEL_VERSION=previous_version/' .env.production
        ;;
    *)
        echo "Invalid item number"
        exit 1
        ;;
esac

# 重启相关服务
echo "Restarting affected services..."
docker-compose restart app celery-worker celery-beat

# 验证更改
echo "Verifying configuration changes..."
curl -f http://localhost:8000/health

echo "✅ Partial configuration rollback completed"
EOF

chmod +x partial_config_rollback.sh
```

### 4. 验证回滚成功的检查步骤

#### ✅ 检查清单：回滚验证

- [ ] **服务状态**: 所有服务正常运行
- [ ] **数据一致性**: 数据回滚后一致性验证
- [ ] **功能验证**: 核心功能正常工作
- [ ] **性能指标**: 性能指标恢复到正常范围
- [ ] **监控告警**: 监控系统正常工作
- [ ] **日志检查**: 错误日志在正常范围内

#### 🧪 回滚后验证脚本

```bash
# =============================================================================
# 1. 综合回滚验证脚本
# =============================================================================

cat > verify_rollback.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Rollback Verification Script ==="
echo "Verification started at $(date)"

# 创建验证报告文件
REPORT_FILE="rollback_verification_$(date +%Y%m%d_%H%M%S).txt"
echo "Rollback Verification Report" > $REPORT_FILE
echo "Timestamp: $(date)" >> $REPORT_FILE
echo "================================" >> $REPORT_FILE

# 初始化验证计数器
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0

# 验证函数
verify() {
    local check_name="$1"
    local check_command="$2"

    echo "Verifying: $check_name"
    echo "Checking: $check_name" >> $REPORT_FILE

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if eval "$check_command" >> $REPORT_FILE 2>&1; then
        echo "✅ PASSED: $check_name"
        echo "Status: PASSED" >> $REPORT_FILE
        echo "" >> $REPORT_FILE
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
    else
        echo "❌ FAILED: $check_name"
        echo "Status: FAILED" >> $REPORT_FILE
        echo "" >> $REPORT_FILE
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
    fi
}

# =============================================================================
# 1. 服务状态验证
# =============================================================================

verify "Docker services status" "docker-compose ps | grep -q 'Up'"
verify "Application service health" "curl -f http://localhost:8000/health"
verify "Database connectivity" "docker exec football_prediction_db pg_isready -U football_user"
verify "Redis connectivity" "docker exec football_prediction_redis redis-cli ping"
verify "MLflow service" "curl -f http://localhost:5002/health"
verify "Grafana service" "curl -f http://localhost:3000/api/health"

# =============================================================================
# 2. 数据一致性验证
# =============================================================================

verify "Database tables exist" "docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '\\\"public\\\";' | grep -q '[0-9]'"

verify "Essential data present" "
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM leagues;' | grep -q '[0-9]'
"

verify "No data corruption" "
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c 'SELECT COUNT(*) FROM matches WHERE match_date > now() + interval '1 year';' | grep -q '^0$'
"

# =============================================================================
# 3. 功能验证
# =============================================================================

verify "API endpoints accessible" "curl -f http://localhost:8000/docs"
verify "Prediction API functional" "
curl -X POST http://localhost:8000/api/v1/predictions/ \
  -H 'Content-Type: application/json' \
  -d '{\"match_id\": \"rollback_test\", \"home_team_id\": 1, \"away_team_id\": 2, \"league_id\": 1, \"match_date\": \"2025-09-25T15:00:00Z\"}' | grep -q 'prediction_id'
"

verify "Data retrieval working" "curl -f http://localhost:8000/api/v1/data/teams?limit=5"
verify "Feature access working" "curl -f http://localhost:8000/api/v1/features/"

# =============================================================================
# 4. 性能验证
# =============================================================================

verify "Response time acceptable" "
response_time=\$(curl -o /dev/null -s -w '%{time_total}' http://localhost:8000/health)
echo \"Response time: \$response_time seconds\"
if (( \$(echo \"\$response_time < 0.5\" | bc -l) )); then
    exit 0
else
    exit 1
fi
"

verify "Memory usage normal" "
memory_usage=\$(docker stats football_prediction_app --no-stream --format '{{.MemUsage}}' | head -1 | cut -d'%' -f1 | tr -d ' ')
echo \"Memory usage: \$memory_usage%\"
if [ \"\$memory_usage\" -lt 80 ]; then
    exit 0
else
    exit 1
fi
"

verify "CPU usage normal" "
cpu_usage=\$(docker stats football_prediction_app --no-stream --format '{{.CPUPerc}}' | head -1 | tr -d '%')
echo \"CPU usage: \$cpu_usage%\"
if (( \$(echo \"\$cpu_usage < 80\" | bc -l) )); then
    exit 0
else
    exit 1
fi
"

# =============================================================================
# 5. 监控验证
# =============================================================================

verify "Prometheus metrics available" "curl -f http://localhost:8000/metrics | grep -q 'football_predictions_total'"
verify "Grafana accessible" "curl -f http://localhost:3000/api/health"
verify "AlertManager functioning" "curl -f http://localhost:9093/-/ready"

# =============================================================================
# 6. 日志验证
# =============================================================================

verify "No critical errors in logs" "
! docker-compose logs app | tail -100 | grep -E '(ERROR|CRITICAL|Exception)' | grep -v 'test'
"

verify "Database connection stable" "
! docker-compose logs app | tail -100 | grep -E '(Connection refused|Database.*failed|authentication.*failed)'
"

# =============================================================================
# 7. 生成验证报告
# =============================================================================

echo "================================" >> $REPORT_FILE
echo "Verification Summary" >> $REPORT_FILE
echo "Total checks: $TOTAL_CHECKS" >> $REPORT_FILE
echo "Passed: $PASSED_CHECKS" >> $REPORT_FILE
echo "Failed: $FAILED_CHECKS" >> $REPORT_FILE
echo "Success rate: $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%" >> $REPORT_FILE
echo "Verification completed at $(date)" >> $REPORT_FILE

# 显示结果
echo ""
echo "=== Rollback Verification Summary ==="
echo "Total checks: $TOTAL_CHECKS"
echo "Passed: $PASSED_CHECKS"
echo "Failed: $FAILED_CHECKS"
echo "Success rate: $(( PASSED_CHECKS * 100 / TOTAL_CHECKS ))%"

if [ $FAILED_CHECKS -eq 0 ]; then
    echo "✅ All checks passed! Rollback successful."
    exit 0
else
    echo "❌ $FAILED_CHECKS checks failed. Manual intervention required."
    echo "Detailed report saved to: $REPORT_FILE"
    exit 1
fi
EOF

chmod +x verify_rollback.sh

# =============================================================================
# 2. 执行验证
# =============================================================================

# 注意：在执行回滚后运行此脚本
# ./verify_rollback.sh
```

---

## 🚨 常见问题与应急预案

### 1. 服务无法启动

#### 🔍 问题诊断步骤

```bash
# =============================================================================
# 1. 检查服务状态
# =============================================================================

# 查看所有服务状态
docker-compose ps

# 检查特定服务状态
docker-compose ps app

# 查看服务日志
docker-compose logs app
docker-compose logs --tail=50 app

# =============================================================================
# 2. 检查依赖服务
# =============================================================================

# 检查数据库连接
docker exec football_prediction_db pg_isready -U football_user

# 检查Redis连接
docker exec football_prediction_redis redis-cli ping

# 检查网络连接
docker network ls
docker network inspect football-network

# =============================================================================
# 3. 检查资源使用
# =============================================================================

# 检查内存使用
docker stats football_prediction_app

# 检查磁盘空间
df -h

# 检查端口占用
netstat -tulpn | grep :8000

# =============================================================================
# 4. 常见启动问题解决
# =============================================================================

# 问题1: 数据库连接失败
if docker-compose logs app | grep -q "Connection refused"; then
    echo "解决方案: 检查数据库服务状态和网络配置"
    docker-compose restart db
    sleep 10
    docker-compose restart app
fi

# 问题2: Redis连接失败
if docker-compose logs app | grep -q "Redis connection"; then
    echo "解决方案: 检查Redis服务状态和密码配置"
    docker-compose restart redis
    sleep 5
    docker-compose restart app
fi

# 问题3: 端口冲突
if docker-compose logs app | grep -q "Address already in use"; then
    echo "解决方案: 检查端口占用情况"
    lsof -i :8000
    # 杀死占用端口的进程
    # kill -9 <PID>
fi

# 问题4: 权限问题
if docker-compose logs app | grep -q "Permission denied"; then
    echo "解决方案: 检查文件权限和环境变量"
    chown -R 999:999 data/
    docker-compose restart app
fi
```

#### 🛠️ 应急解决方案

```bash
# =============================================================================
# 1. 紧急重启脚本
# =============================================================================

cat > emergency_restart.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Emergency Service Restart ==="

# 记录当前状态
echo "Current service status:" > emergency_restart.log
docker-compose ps >> emergency_restart.log

# 停止所有服务
echo "Stopping all services..."
docker-compose down

# 清理资源
echo "Cleaning up resources..."
docker system prune -f
docker volume prune -f

# 重新启动基础设施
echo "Starting infrastructure services..."
docker-compose up -d db redis

# 等待基础设施就绪
echo "Waiting for infrastructure..."
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'
timeout 30 bash -c 'until docker exec football_prediction_redis redis-cli ping; do sleep 2; done'

# 启动应用服务
echo "Starting application services..."
docker-compose up -d app

# 等待应用启动
echo "Waiting for application..."
sleep 30

# 验证服务状态
echo "Verifying service status..."
docker-compose ps >> emergency_restart.log
curl -f http://localhost:8000/health >> emergency_restart.log 2>&1

echo "Emergency restart completed"
echo "Log saved to emergency_restart.log"
EOF

chmod +x emergency_restart.sh

# =============================================================================
# 2. 单独服务重启
# =============================================================================

# 重启特定服务
docker-compose restart app
docker-compose restart db
docker-compose restart redis

# 强制重启
docker-compose restart --timeout 60 app

# =============================================================================
# 3. 配置重置
# =============================================================================

# 重置到默认配置
cp .env.production.example .env.production
docker-compose down
docker-compose up -d
```

### 2. API 请求 500

#### 🔍 问题诊断步骤

```bash
# =============================================================================
# 1. 检查错误日志
# =============================================================================

# 查看应用错误日志
docker-compose logs app | grep -E "(500|ERROR|Exception|Traceback)" | tail -20

# 查看最新错误
docker-compose logs --tail=100 app | grep -A 5 -B 5 "ERROR"

# =============================================================================
# 2. 检查模型文件
# =============================================================================

# 检查MLflow模型注册
curl -s http://localhost:5002/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[]'

# 检查模型文件存在
docker exec football_prediction_mlflow ls -la /mlflow-artifacts/

# 检查模型加载日志
docker-compose logs app | grep -i "model\|mlflow"

# =============================================================================
# 3. 检查缓存状态
# =============================================================================

# 检查Redis连接
docker exec football_prediction_redis redis-cli ping

# 检查缓存命中率
docker exec football_prediction_redis redis-cli info | grep keyspace

# 检查缓存键
docker exec football_prediction_redis redis-cli keys "model:*" | head -10

# =============================================================================
# 4. 检查数据库连接
# =============================================================================

# 测试数据库连接
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "SELECT 1;"

# 检查数据库连接池
docker-compose logs app | grep -i "connection\|pool"

# 检查慢查询
docker-compose logs app | grep -i "slow\|query.*ms"
```

#### 🛠️ 应急解决方案

```bash
# =============================================================================
# 1. 模型重新加载
# =============================================================================

cat > reload_model.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Model Reload Script ==="

# 重启MLflow服务
echo "Restarting MLflow..."
docker-compose restart mlflow

# 等待MLflow就绪
sleep 20

# 清理应用缓存
echo "Clearing application cache..."
docker exec football_prediction_app rm -rf /tmp/model_cache/*

# 重启应用服务
echo "Restarting application..."
docker-compose restart app

# 等待应用启动
sleep 15

# 验证模型加载
echo "Verifying model loading..."
curl -f http://localhost:8000/health

echo "Model reload completed"
EOF

chmod +x reload_model.sh

# =============================================================================
# 2. 缓存重置
# =============================================================================

cat > reset_cache.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Cache Reset Script ==="

# 重启Redis服务
echo "Restarting Redis..."
docker-compose restart redis

# 等待Redis就绪
sleep 10

# 清理应用缓存连接
echo "Clearing application cache..."
docker-compose restart app

# 验证缓存连接
echo "Verifying cache connection..."
docker exec football_prediction_redis redis-cli ping

echo "Cache reset completed"
EOF

chmod +x reset_cache.sh

# =============================================================================
# 3. 数据库连接池重置
# =============================================================================

cat > reset_db_pool.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Database Pool Reset Script ==="

# 重启数据库服务
echo "Restarting database..."
docker-compose restart db

# 等待数据库就绪
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'

# 重启应用服务
echo "Restarting application..."
docker-compose restart app

# 验证数据库连接
echo "Verifying database connection..."
curl -f http://localhost:8000/health

echo "Database pool reset completed"
EOF

chmod +x reset_db_pool.sh
```

### 3. 消息队列阻塞

#### 🔍 问题诊断步骤

```bash
# =============================================================================
# 1. 检查Kafka状态
# =============================================================================

# 检查Kafka服务状态
docker-compose ps kafka

# 检查Kafka日志
docker-compose logs kafka | tail -20

# 检查Kafka主题
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list

# 检查主题状态
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --describe

# =============================================================================
# 2. 检查Celery状态
# =============================================================================

# 检查Celery工作进程
docker-compose ps celery-worker

# 检查Celery日志
docker-compose logs celery-worker | tail -20

# 检查Celery任务状态
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect active
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect scheduled
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats

# =============================================================================
# 3. 检查消息积压
# =============================================================================

# 检查队列长度
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect queued

# 检查消费者延迟
docker-compose logs celery-worker | grep -i "delay\|latency"

# 检查ZooKeeper状态
docker exec football_prediction_zookeeper echo "ruok" | nc localhost 2181
```

#### 🛠️ 应急解决方案

```bash
# =============================================================================
# 1. 消息队列重置
# =============================================================================

cat > reset_message_queue.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Message Queue Reset Script ==="

# 停止消息队列服务
echo "Stopping message queue services..."
docker-compose stop kafka zookeeper celery-worker celery-beat

# 清理Kafka数据
echo "Cleaning Kafka data..."
docker volume rm football_prediction_kafka_data
docker volume create football_prediction_kafka_data

# 重启ZooKeeper
echo "Restarting ZooKeeper..."
docker-compose up -d zookeeper

# 等待ZooKeeper就绪
sleep 20

# 重启Kafka
echo "Restarting Kafka..."
docker-compose up -d kafka

# 等待Kafka就绪
timeout 60 bash -c 'until docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list; do sleep 5; done'

# 重建主题
echo "Recreating topics..."
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 \
  --create --topic football-predictions --partitions 3 --replication-factor 1

# 重启Celery服务
echo "Restarting Celery services..."
docker-compose up -d celery-worker celery-beat

# 验证服务状态
echo "Verifying services..."
docker-compose ps celery-worker celery-beat kafka
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats

echo "Message queue reset completed"
EOF

chmod +x reset_message_queue.sh

# =============================================================================
# 2. Celery任务清理
# =============================================================================

cat > clear_celery_tasks.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Celery Tasks Cleanup Script ==="

# 停止Celery工作进程
echo "Stopping Celery workers..."
docker-compose stop celery-worker celery-beat

# 清理Redis中的任务数据
echo "Clearing Redis task data..."
docker exec football_prediction_redis redis-cli flushdb

# 重启Celery服务
echo "Restarting Celery services..."
docker-compose up -d celery-worker celery-beat

# 等待服务启动
sleep 10

# 验证Celery状态
echo "Verifying Celery status..."
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect stats

echo "Celery tasks cleanup completed"
EOF

chmod +x clear_celery_tasks.sh
```

### 4. 告警风暴

#### 🔍 问题诊断步骤

```bash
# =============================================================================
# 1. 检查告警状态
# =============================================================================

# 检查当前告警
curl -s http://localhost:9093/api/v1/alerts | jq '.data.alerts[] | {name, state, labels}'

# 检查告警规则状态
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].rules[] | {name, health, lastError}'

# 检查Prometheus目标状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {health, labels}'

# =============================================================================
# 2. 检查系统资源
# =============================================================================

# 检查CPU使用率
docker stats football_prediction_app --no-stream --format '{{.CPUPerc}}'

# 检查内存使用率
docker stats football_prediction_app --no-stream --format '{{.MemUsage}}'

# 检查磁盘使用
df -h

# 检查网络连接
netstat -an | grep :8000 | wc -l

# =============================================================================
# 3. 检查业务指标
# =============================================================================

# 检查API错误率
curl -s http://localhost:8000/metrics | grep "http_requests_total{status=\"5..\"}"

# 检查响应时间
curl -s http://localhost:8000/metrics | grep "football_prediction_latency_seconds"

# 检查数据库连接数
curl -s http://localhost:9187/metrics | grep "pg_stat_database_numbackends"
```

#### 🛠️ 应急解决方案

```bash
# =============================================================================
# 1. 告警静默脚本
# =============================================================================

cat > silence_alerts.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Alert Silence Script ==="

# 静默所有告警
curl -X POST http://localhost:9093/api/v1/silences \
  -H "Content-Type: application/json" \
  -d '{
    "matchers": [
      {
        "name": "severity",
        "value": ".*",
        "isRegex": true
      }
    ],
    "startsAt": "'$(date -Iseconds)'",
    "endsAt": "'$(date -d '+1 hour' -Iseconds)'",
    "comment": "Emergency silence during incident",
    "createdBy": "emergency_script"
  }'

echo "All alerts silenced for 1 hour"
EOF

chmod +x silence_alerts.sh

# =============================================================================
# 2. 告警阈值调整
# =============================================================================

cat > adjust_alert_thresholds.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Alert Threshold Adjustment Script ==="

# 备份当前告警规则
cp configs/prometheus/alert_rules.yml configs/prometheus/alert_rules.yml.backup_$(date +%Y%m%d_%H%M%S)

# 调整告警阈值（提高阈值以减少告警）
sed -i 's/> 0.01/> 0.05/g' configs/prometheus/alert_rules.yml
sed -i 's/> 1/> 5/g' configs/prometheus/alert_rules.yml
sed -i 's/> 80/> 90/g' configs/prometheus/alert_rules.yml
sed -i 's/> 90/> 95/g' configs/prometheus/alert_rules.yml

# 重新加载Prometheus配置
curl -X POST http://localhost:9090/-/reload

echo "Alert thresholds adjusted and Prometheus reloaded"
EOF

chmod +x adjust_alert_thresholds.sh

# =============================================================================
# 3. 系统资源优化
# =============================================================================

cat > optimize_resources.sh << 'EOF'
#!/bin/bash
set -e

echo "=== Resource Optimization Script ==="

# 重启高内存使用服务
echo "Restarting high-memory services..."
docker-compose restart app celery-worker

# 清理Docker资源
echo "Cleaning Docker resources..."
docker system prune -f
docker volume prune -f

# 优化数据库连接池
echo "Optimizing database connection pool..."
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
ALTER SYSTEM SET max_connections = 200;
SELECT pg_reload_conf();
"

# 重启数据库
echo "Restarting database..."
docker-compose restart db

echo "Resource optimization completed"
EOF

chmod +x optimize_resources.sh
```

---

## 📋 附录

### A. 部署命令示例

#### 🐳 Docker Compose 部署命令

```bash
# =============================================================================
# 基础部署命令
# =============================================================================

# 完整部署
docker-compose up -d

# 分步部署
docker-compose up -d db redis
docker-compose up -d zookeeper kafka
docker-compose up -d minio mlflow
docker-compose up -d prometheus grafana
docker-compose up -d app celery-worker celery-beat
docker-compose up -d nginx

# 特定服务部署
docker-compose up -d app
docker-compose up -d db
docker-compose up -d redis

# =============================================================================
# 服务管理命令
# =============================================================================

# 启动服务
docker-compose up -d

# 停止服务
docker-compose down

# 重启服务
docker-compose restart app

# 查看日志
docker-compose logs -f app

# 查看服务状态
docker-compose ps

# =============================================================================
# 清理命令
# =============================================================================

# 停止并删除容器
docker-compose down

# 停止并删除容器和网络
docker-compose down --rmi all

# 停止并删除容器、网络、卷
docker-compose down -v

# 清理未使用的资源
docker system prune -a
docker volume prune
```

#### ☸️ Kubernetes 部署命令

```bash
# =============================================================================
# 基础部署命令
# =============================================================================

# 应用所有配置
kubectl apply -f k8s/

# 分步应用
kubectl apply -f k8s/storage/
kubectl apply -f k8s/database/
kubectl apply -f k8s/cache/
kubectl apply -f k8s/messaging/
kubectl apply -f k8s/ml/
kubectl apply -f k8s/monitoring/
kubectl apply -f k8s/app/
kubectl apply -f k8s/ingress/

# =============================================================================
# 服务管理命令
# =============================================================================

# 查看Pod状态
kubectl get pods -o wide

# 查看服务状态
kubectl get services

# 查看Ingress状态
kubectl get ingress

# 查看部署状态
kubectl get deployments

# =============================================================================
# 故障排查命令
# =============================================================================

# 查看Pod日志
kubectl logs -f deployment/football-prediction

# 查看特定Pod日志
kubectl logs -f <pod-name>

# 进入Pod调试
kubectl exec -it <pod-name> -- /bin/bash

# 描述Pod详细信息
kubectl describe pod <pod-name>

# =============================================================================
# 扩缩容命令
# =============================================================================

# 扩容应用
kubectl scale deployment football-prediction --replicas=3

# 扩容工作节点
kubectl scale deployment celery-worker --replicas=2

# =============================================================================
# 更新命令
# =============================================================================

# 滚动更新
kubectl rollout restart deployment football-prediction

# 回滚到上一个版本
kubectl rollout undo deployment football-prediction

# 查看更新状态
kubectl rollout status deployment football-prediction
```

### B. 常用运维命令

#### 📊 日志和状态命令

```bash
# =============================================================================
# 应用日志
# =============================================================================

# 实时查看应用日志
docker-compose logs -f app

# 查看最近的100行日志
docker-compose logs --tail=100 app

# 查看特定时间段的日志
docker-compose logs --since=1h app

# 查看错误日志
docker-compose logs app | grep ERROR

# =============================================================================
# 系统状态
# =============================================================================

# 查看所有容器状态
docker ps -a

# 查看资源使用情况
docker stats

# 查看网络状态
docker network ls
docker network inspect football-network

# 查看卷状态
docker volume ls
docker volume inspect football_prediction_db_data

# =============================================================================
# 数据库操作
# =============================================================================

# 连接到数据库
docker exec -it football_prediction_db psql -U football_user -d football_prediction_dev

# 数据库备份
docker exec football_prediction_db pg_dump -U football_user -d football_prediction_dev > backup.sql

# 数据库恢复
docker exec -i football_prediction_db psql -U football_user -d football_prediction_dev < backup.sql

# =============================================================================
# 缓存操作
# =============================================================================

# 连接到Redis
docker exec -it football_prediction_redis redis-cli

# 查看缓存统计
docker exec football_prediction_redis redis-cli info

# 清空缓存
docker exec football_prediction_redis redis-cli flushdb

# =============================================================================
# 监控命令
# =============================================================================

# 查看Prometheus目标状态
curl -s http://localhost:9090/api/v1/targets | jq

# 查看告警状态
curl -s http://localhost:9093/api/v1/alerts | jq

# 重载Prometheus配置
curl -X POST http://localhost:9090/-/reload

# 重载AlertManager配置
curl -X POST http://localhost:9093/-/reload
```

#### 🔄 扩缩容命令

```bash
# =============================================================================
# Docker Compose 扩缩容
# =============================================================================

# 扩容应用服务
docker-compose up -d --scale app=3

# 扩容工作节点
docker-compose up -d --scale celery-worker=2

# 缩容服务
docker-compose up -d --scale app=1

# 查看扩容状态
docker-compose ps

# =============================================================================
# Kubernetes 扩缩容
# =============================================================================

# 水平扩容应用
kubectl autoscale deployment football-prediction --min=2 --max=10 --cpu-percent=70

# 手动扩容
kubectl scale deployment football-prediction --replicas=5

# 查看扩容状态
kubectl get hpa
kubectl get deployments

# =============================================================================
# 负载测试扩容
# =============================================================================

# 启动负载测试
kubectl apply -f k8s/loadtest/locust-deployment.yaml

# 监控扩容效果
kubectl get hpa -w
kubectl get pods -w

# 停止负载测试
kubectl delete deployment locust
```

### C. 联系人/责任人清单

| 角色 | 姓名 | 联系方式 | 职责范围 |
|------|------|---------|---------|
| **技术负责人** | [待填写] | [待填写] | 技术决策和架构设计 |
| **运维负责人** | [待填写] | [待填写] | 生产环境部署和维护 |
| **开发负责人** | [待填写] | [待填写] | 应用开发和bug修复 |
| **数据库管理员** | [待填写] | [待填写] | 数据库管理和优化 |
| **安全负责人** | [待填写] | [待填写] | 安全配置和审计 |
| **测试负责人** | [待填写] | [待填写] | 测试和质量保证 |

### D. 部署检查清单模板

```markdown
# 足球预测系统部署检查清单

## 部署前准备
- [ ] 代码已合并至主分支
- [ ] CI/CD流程通过
- [ ] 环境变量配置完成
- [ ] 数据库备份已创建
- [ ] 版本号已确认

## 部署过程
- [ ] 基础设施服务启动
- [ ] 数据库服务启动
- [ ] 消息队列启动
- [ ] 应用服务启动
- [ ] 监控服务启动

## 部署后验证
- [ ] 服务健康检查
- [ ] 功能测试通过
- [ ] 性能测试通过
- [ ] 监控告警正常
- [ ] 日志检查正常

## 回滚准备
- [ ] 回滚脚本已准备
- [ ] 备份数据可用
- [ ] 回滚验证步骤明确

## 部署完成确认
- [ ] 部署报告已生成
- [ ] 相关人员已通知
- [ ] 监控告警已设置
- [ ] 文档已更新
```

---

## 📞 紧急联系方式

在部署过程中遇到紧急问题时，请联系：

- **技术支持热线**: [待填写]
- **运维值班电话**: [待填写]
- **项目管理**: [待填写]
- **安全事件**: [待填写]

---

**文档版本**: v1.0
**最后更新**: 2025-09-25
**维护人员**: 系统运维团队

*本手册为足球预测系统生产部署的标准操作指南，请严格按照步骤执行。如有疑问，请及时联系相关负责人。*
