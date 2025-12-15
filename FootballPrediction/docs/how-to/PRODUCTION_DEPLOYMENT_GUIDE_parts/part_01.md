# 🚀 足球预测系统生产部署执行手册

**系统名称**: 足球预测系统 (Football Prediction System)
**版本**: Phase 6 Production Ready
**最后更新**: 2025-09-25
**文档目标**: 提供标准化、可执行的生产部署手册，确保部署过程安全、可控、可回滚

---

##📋 执行摘要

📋 执行摘要
###
###🎯 手册目标

本手册旨在为足球预测系统的生产部署提供标准化的执行流程，涵盖从部署准备到验证再到回滚演练的完整环节。通过遵循本手册，确保系统部署过程的安全性、可控性和可回滚性。

🎯 手册目标

本手册旨在为足球预测系统的生产部署提供标准化的执行流程，涵盖从部署准备到验证再到回滚演练的完整环节。通过遵循本手册，确保系统部署过程的安全性、可控性和可回滚性。
###
###🏗️ 上线涉及的核心组件

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

🏗️ 上线涉及的核心组件

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
##
##🔧 部署前准备

🔧 部署前准备
###
###1. 代码和CI/CD验证

#### ✅ 检查清单：代码准备

- [ ] **主分支状态**: 确认代码已合并至 `main` 分支
- [ ] **CI/CD通过**: 最新提交的CI/CD流程全部通过
- [ ] **版本标记**: 使用正确的版本标签格式 `football-predict:phase6`
- [ ] **测试覆盖率**: 确认测试覆盖率 ≥70%
- [ ] **安全扫描**: Bandit和Safety安全扫描通过

#### 🔄 版本号规范

```bash
1. 代码和CI/CD验证

#### ✅ 检查清单：代码准备

- [ ] **主分支状态**: 确认代码已合并至 `main` 分支
- [ ] **CI/CD通过**: 最新提交的CI/CD流程全部通过
- [ ] **版本标记**: 使用正确的版本标签格式 `football-predict:phase6`
- [ ] **测试覆盖率**: 确认测试覆盖率 ≥70%
- [ ] **安全扫描**: Bandit和Safety安全扫描通过

#### 🔄 版本号规范

```bash#
#版本命名规范
football-predict:phase6              # Phase 6 生产版本
football-predict:phase6-v1.0.0       # 语义化版本
football-predict:phase6-<git-sha>    # Git SHA版本
football-predict:phase6-<timestamp>  # 时间戳版本
```

#### 📋 验证命令

```bash
版本命名规范
football-predict:phase6              # Phase 6 生产版本
football-predict:phase6-v1.0.0       # 语义化版本
football-predict:phase6-<git-sha>    # Git SHA版本
football-predict:phase6-<timestamp>  # 时间戳版本
```

#### 📋 验证命令

```bash#
#1. 检查代码状态
git status
git log --oneline -5

1. 检查代码状态
git status
git log --oneline -5
#
#2. 验证CI/CD状态
gh run list --limit=5

2. 验证CI/CD状态
gh run list --limit=5
#
#3. 检查测试覆盖率
./venv/bin/pytest tests/unit --cov=src --cov-report=term --cov-fail-under=70

3. 检查测试覆盖率
./venv/bin/pytest tests/unit --cov=src --cov-report=term --cov-fail-under=70
#
#4. 安全扫描验证
bandit -r src/ -f json -o bandit-latest.json
safety check --json --output safety-latest.json
```

4. 安全扫描验证
bandit -r src/ -f json -o bandit-latest.json
safety check --json --output safety-latest.json
```
###
###2. 环境变量准备

#### 🔐 环境变量清单

```bash
2. 环境变量准备

#### 🔐 环境变量清单

```bash#
#=============================================================================
=============================================================================#
#应用基础配置
应用基础配置#
#=============================================================================
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com

=============================================================================
ENVIRONMENT=production
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
CORS_ORIGINS=https://your-domain.com,https://api.your-domain.com
#
#=============================================================================
=============================================================================#
#安全配置
安全配置#
#=============================================================================
JWT_SECRET_KEY=your_super_secure_jwt_secret_key_here_minimum_32_characters
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

=============================================================================
JWT_SECRET_KEY=your_super_secure_jwt_secret_key_here_minimum_32_characters
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
#
#=============================================================================
=============================================================================#
#数据库配置 - 主数据库
数据库配置 - 主数据库#
#=============================================================================
DB_HOST=db
DB_PORT=5432
DB_NAME=football_prediction_dev
DB_USER=football_user
DB_PASSWORD=your_secure_db_password_here

=============================================================================
DB_HOST=db
DB_PORT=5432
DB_NAME=football_prediction_dev
DB_USER=football_user
DB_PASSWORD=your_secure_db_password_here
#
#PostgreSQL 根用户
POSTGRES_DB=football_prediction_dev
POSTGRES_USER=football_user
POSTGRES_PASSWORD=your_secure_postgres_password_here

PostgreSQL 根用户
POSTGRES_DB=football_prediction_dev
POSTGRES_USER=football_user
POSTGRES_PASSWORD=your_secure_postgres_password_here
#
#多用户架构
DB_READER_USER=football_reader
DB_READER_PASSWORD=your_reader_password_here
DB_WRITER_USER=football_writer
DB_WRITER_PASSWORD=your_writer_password_here
DB_ADMIN_USER=football_admin
DB_ADMIN_PASSWORD=your_admin_password_here

多用户架构
DB_READER_USER=football_reader
DB_READER_PASSWORD=your_reader_password_here
DB_WRITER_USER=football_writer
DB_WRITER_PASSWORD=your_writer_password_here
DB_ADMIN_USER=football_admin
DB_ADMIN_PASSWORD=your_admin_password_here
#
#=============================================================================
=============================================================================#
#缓存配置
缓存配置#
#=============================================================================
REDIS_PASSWORD=your_secure_redis_password_here
REDIS_URL=redis://:your_secure_redis_password_here@redis:6379/0

=============================================================================
REDIS_PASSWORD=your_secure_redis_password_here
REDIS_URL=redis://:your_secure_redis_password_here@redis:6379/0
#
#Celery 任务队列
CELERY_BROKER_URL=redis://:your_secure_redis_password_here@redis:6379/0
CELERY_RESULT_BACKEND=redis://:your_secure_redis_password_here@redis:6379/0

Celery 任务队列
CELERY_BROKER_URL=redis://:your_secure_redis_password_here@redis:6379/0
CELERY_RESULT_BACKEND=redis://:your_secure_redis_password_here@redis:6379/0
#
#=============================================================================
=============================================================================#
#对象存储配置
对象存储配置#
#=============================================================================
MINIO_ROOT_USER=football_minio_admin
MINIO_ROOT_PASSWORD=your_secure_minio_password_here
MINIO_SECRET_KEY=your_minio_secret_key_here

=============================================================================
MINIO_ROOT_USER=football_minio_admin
MINIO_ROOT_PASSWORD=your_secure_minio_password_here
MINIO_SECRET_KEY=your_minio_secret_key_here
#
#AWS (for MinIO compatibility)
AWS_ACCESS_KEY_ID=football_minio_admin
AWS_SECRET_ACCESS_KEY=your_secure_minio_password_here
AWS_DEFAULT_REGION=us-east-1

AWS (for MinIO compatibility)
AWS_ACCESS_KEY_ID=football_minio_admin
AWS_SECRET_ACCESS_KEY=your_secure_minio_password_here
AWS_DEFAULT_REGION=us-east-1
#
#=============================================================================
=============================================================================#
#MLflow 配置
MLflow 配置#
#=============================================================================
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_EXPERIMENT_NAME=football_prediction
MLFLOW_REGISTRY_URI=http://mlflow:5000
MLFLOW_BACKEND_STORE_URI=postgresql://mlflow_user:mlflow_password@mlflow-db:5432/mlflow
MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://football-models/mlflow-artifacts
MLFLOW_S3_ENDPOINT_URL=http://minio:9000

=============================================================================
MLFLOW_TRACKING_URI=http://mlflow:5000
MLFLOW_EXPERIMENT_NAME=football_prediction
MLFLOW_REGISTRY_URI=http://mlflow:5000
MLFLOW_BACKEND_STORE_URI=postgresql://mlflow_user:mlflow_password@mlflow-db:5432/mlflow
MLFLOW_DEFAULT_ARTIFACT_ROOT=s3://football-models/mlflow-artifacts
MLFLOW_S3_ENDPOINT_URL=http://minio:9000
#
#MLflow 数据库
MLFLOW_DB_USER=mlflow_user
MLFLOW_DB_PASSWORD=your_mlflow_password_here
MLFLOW_DB_NAME=mlflow

MLflow 数据库
MLFLOW_DB_USER=mlflow_user
MLFLOW_DB_PASSWORD=your_mlflow_password_here
MLFLOW_DB_NAME=mlflow
#
#=============================================================================
=============================================================================#
#数据血缘配置
数据血缘配置#
#=============================================================================
MARQUEZ_DB_USER=marquez_user
MARQUEZ_DB_PASSWORD=your_marquez_password_here
MARQUEZ_DB_NAME=marquez

=============================================================================
MARQUEZ_DB_USER=marquez_user
MARQUEZ_DB_PASSWORD=your_marquez_password_here
MARQUEZ_DB_NAME=marquez
#
#=============================================================================
=============================================================================#
#监控配置
监控配置#
#=============================================================================
GRAFANA_ADMIN_PASSWORD=your_grafana_password_here

=============================================================================
GRAFANA_ADMIN_PASSWORD=your_grafana_password_here
#
#=============================================================================
=============================================================================#
#模型配置
模型配置#
#=============================================================================
MODEL_CACHE_TTL_HOURS=1
PREDICTION_CACHE_TTL_MINUTES=30
PRODUCTION_MODEL_NAME=football-match-predictor
PRODUCTION_MODEL_VERSION=latest
```

#### 📁 环境文件创建

```bash
=============================================================================
MODEL_CACHE_TTL_HOURS=1
PREDICTION_CACHE_TTL_MINUTES=30
PRODUCTION_MODEL_NAME=football-match-predictor
PRODUCTION_MODEL_VERSION=latest
```

#### 📁 环境文件创建

```bash#
#1. 创建生产环境文件
cp .env.production.example .env.production

1. 创建生产环境文件
cp .env.production.example .env.production
#
#2. 编辑环境变量（使用安全的方式）
2. 编辑环境变量（使用安全的方式）#
#推荐使用密钥管理服务或加密的环境变量
推荐使用密钥管理服务或加密的环境变量#
#或者使用安全配置管理工具

或者使用安全配置管理工具
#
#3. 验证环境变量
grep -E "PASSWORD|SECRET|KEY" .env.production
```

3. 验证环境变量
grep -E "PASSWORD|SECRET|KEY" .env.production
```
###
###3. 数据库迁移检查

#### ✅ 检查清单：数据库准备

- [ ] **迁移文件完整**: 确认所有12个Alembic迁移文件存在
- [ ] **数据库备份**: 生产数据库有完整备份
- [ ] **连接测试**: 数据库连接配置正确
- [ ] **权限验证**: 数据库用户权限正确设置
- [ ] **性能配置**: 数据库性能参数优化

#### 🗄️ 数据库迁移命令

```bash
3. 数据库迁移检查

#### ✅ 检查清单：数据库准备

- [ ] **迁移文件完整**: 确认所有12个Alembic迁移文件存在
- [ ] **数据库备份**: 生产数据库有完整备份
- [ ] **连接测试**: 数据库连接配置正确
- [ ] **权限验证**: 数据库用户权限正确设置
- [ ] **性能配置**: 数据库性能参数优化

#### 🗄️ 数据库迁移命令

```bash#
#1. 检查迁移状态
alembic current
alembic history --verbose

1. 检查迁移状态
alembic current
alembic history --verbose
#
#2. 验证迁移文件
ls -la src/database/migrations/versions/
wc -l src/database/migrations/versions/*.py

2. 验证迁移文件
ls -la src/database/migrations/versions/
wc -l src/database/migrations/versions/*.py
#
#3. 测试数据库连接
python -c "
import asyncio
from src.database.config import get_database_config
config = get_database_config()
print(f'Database URL: {config.database_url}')
"

3. 测试数据库连接
python -c "
import asyncio
from src.database.config import get_database_config
config = get_database_config()
print(f'Database URL: {config.database_url}')
"
#
#4. 运行迁移（如果需要）
alembic upgrade head

4. 运行迁移（如果需要）
alembic upgrade head
#
#5. 验证数据库表
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

5. 验证数据库表
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
###
###4. 模型文件与缓存预加载

#### ✅ 检查清单：模型准备

- [ ] **模型文件存在**: 确认MLflow中已注册生产模型
- [ ] **模型版本正确**: 使用正确的模型版本标签
- [ ] **Feature Store**: Feast feature store已初始化
- [ ] **缓存预热**: Redis缓存已预热
- [ ] **模型加载**: 模型加载测试通过

#### 🤖 模型验证命令

```bash
4. 模型文件与缓存预加载

#### ✅ 检查清单：模型准备

- [ ] **模型文件存在**: 确认MLflow中已注册生产模型
- [ ] **模型版本正确**: 使用正确的模型版本标签
- [ ] **Feature Store**: Feast feature store已初始化
- [ ] **缓存预热**: Redis缓存已预热
- [ ] **模型加载**: 模型加载测试通过

#### 🤖 模型验证命令

```bash#
#1. 检查MLflow模型注册
curl -s http://mlflow:5000/api/2.0/registered-models/list | jq '.registered_models[].name'

1. 检查MLflow模型注册
curl -s http://mlflow:5000/api/2.0/registered-models/list | jq '.registered_models[].name'
#
#2. 验证生产模型版本
curl -s http://mlflow:5000/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[]'

2. 验证生产模型版本
curl -s http://mlflow:5000/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[]'
#
#3. 初始化Feature Store
python -c "
from src.features.feature_store import FootballFeatureStore
store = FootballFeatureStore()
store.initialize()
print('Feature Store initialized successfully')
"

3. 初始化Feature Store
python -c "
from src.features.feature_store import FootballFeatureStore
store = FootballFeatureStore()
store.initialize()
print('Feature Store initialized successfully')
"
#
#4. 测试模型加载
python -c "
from src.models.prediction_service import PredictionService
service = PredictionService(mlflow_tracking_uri='http://mlflow:5000')
model = service.load_production_model()
print(f'Model loaded: {type(model)}')
"

4. 测试模型加载
python -c "
from src.models.prediction_service import PredictionService
service = PredictionService(mlflow_tracking_uri='http://mlflow:5000')
model = service.load_production_model()
print(f'Model loaded: {type(model)}')
"
#
#5. 预热缓存
python -c "
from src.cache.redis_manager import RedisManager
redis = RedisManager()
5. 预热缓存
python -c "
from src.cache.redis_manager import RedisManager
redis = RedisManager()#
#预热常用数据
redis.warmup_cache()
print('Cache warmed up successfully')
"
```

---

预热常用数据
redis.warmup_cache()
print('Cache warmed up successfully')
"
```

---
##
##🚀 部署步骤

🚀 部署步骤
###
###1. Docker Compose 部署

#### ✅ 检查清单：部署准备

- [ ] **镜像准备**: 所有服务镜像已构建并推送
- [ ] **配置文件**: 所有配置文件已准备就绪
- [ ] **存储准备**: 数据目录和备份目录已创建
- [ ] **网络准备**: Docker网络配置正确
- [ ] **权限准备**: 文件系统权限正确设置

#### 🐳 Docker Compose 部署命令

```bash
1. Docker Compose 部署

#### ✅ 检查清单：部署准备

- [ ] **镜像准备**: 所有服务镜像已构建并推送
- [ ] **配置文件**: 所有配置文件已准备就绪
- [ ] **存储准备**: 数据目录和备份目录已创建
- [ ] **网络准备**: Docker网络配置正确
- [ ] **权限准备**: 文件系统权限正确设置

#### 🐳 Docker Compose 部署命令

```bash#
#=============================================================================
=============================================================================#
#1. 环境准备
1. 环境准备#
#=============================================================================

=============================================================================
#
#设置环境变量
export COMPOSE_PROJECT_NAME=football-prediction-production
export DOCKER_DEFAULT_PLATFORM=linux/amd64

设置环境变量
export COMPOSE_PROJECT_NAME=football-prediction-production
export DOCKER_DEFAULT_PLATFORM=linux/amd64
#
#创建必要目录
mkdir -p data/{db-backups,football_lake,logs/{postgresql,redis,app}}
mkdir -p models/{trained,experiments,retrain_reports}

创建必要目录
mkdir -p data/{db-backups,football_lake,logs/{postgresql,redis,app}}
mkdir -p models/{trained,experiments,retrain_reports}
#
#设置权限
chmod 755 data/ models/
chown -R 999:999 data/db-backups/  # PostgreSQL用户权限

设置权限
chmod 755 data/ models/
chown -R 999:999 data/db-backups/  # PostgreSQL用户权限
#
#=============================================================================
=============================================================================#
#2. 启动基础设施服务
2. 启动基础设施服务#
#=============================================================================

=============================================================================
#
#启动数据库和缓存（按依赖顺序）
docker-compose up -d db redis

启动数据库和缓存（按依赖顺序）
docker-compose up -d db redis
#
#等待数据库启动完成
echo "Waiting for database to be ready..."
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'

等待数据库启动完成
echo "Waiting for database to be ready..."
timeout 60 bash -c 'until docker exec football_prediction_db pg_isready -U football_user; do sleep 2; done'
#
#启动消息队列
docker-compose up -d zookeeper kafka

启动消息队列
docker-compose up -d zookeeper kafka
#
#等待Kafka启动完成
echo "Waiting for Kafka to be ready..."
timeout 60 bash -c 'until docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list; do sleep 5; done'

等待Kafka启动完成
echo "Waiting for Kafka to be ready..."
timeout 60 bash -c 'until docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list; do sleep 5; done'
#
#=============================================================================
=============================================================================#
#3. 启动存储和ML服务
3. 启动存储和ML服务#
#=============================================================================

=============================================================================
#
#启动对象存储
docker-compose up -d minio

启动对象存储
docker-compose up -d minio
#
#等待MinIO启动完成
echo "Waiting for MinIO to be ready..."
timeout 30 bash -c 'until curl -f http://localhost:9000/minio/health/live; do sleep 2; done'

等待MinIO启动完成
echo "Waiting for MinIO to be ready..."
timeout 30 bash -c 'until curl -f http://localhost:9000/minio/health/live; do sleep 2; done'
#
#启动MLflow
docker-compose up -d mlflow-db mlflow

启动MLflow
docker-compose up -d mlflow-db mlflow
#
#等待MLflow启动完成
echo "Waiting for MLflow to be ready..."
timeout 60 bash -c 'until curl -f http://localhost:5002/health; do sleep 5; done'

等待MLflow启动完成
echo "Waiting for MLflow to be ready..."
timeout 60 bash -c 'until curl -f http://localhost:5002/health; do sleep 5; done'
#
#=============================================================================
=============================================================================#
#4. 启动监控服务
4. 启动监控服务#
#=============================================================================

=============================================================================
#
#启动监控系统
docker-compose up -d prometheus grafana alertmanager

启动监控系统
docker-compose up -d prometheus grafana alertmanager
#
#启动指标导出器
docker-compose up -d node-exporter postgres-exporter redis-exporter

启动指标导出器
docker-compose up -d node-exporter postgres-exporter redis-exporter
#
#=============================================================================
=============================================================================#
#5. 启动应用服务
5. 启动应用服务#
#=============================================================================

=============================================================================
#
#启动数据血缘服务
docker-compose up -d marquez-db marquez

启动数据血缘服务
docker-compose up -d marquez-db marquez
#
#启动任务队列
docker-compose up -d celery-worker celery-beat celery-flower

启动任务队列
docker-compose up -d celery-worker celery-beat celery-flower
#
#启动应用服务
docker-compose up -d app

启动应用服务
docker-compose up -d app
#
#启动负载均衡
docker-compose up -d nginx

启动负载均衡
docker-compose up -d nginx
#
#=============================================================================
=============================================================================#
#6. 验证启动状态
6. 验证启动状态#
#=============================================================================

=============================================================================
#
#检查所有服务状态
docker-compose ps

检查所有服务状态
docker-compose ps
#
#检查服务健康状态
docker-compose exec app curl -f http://localhost:8000/health
docker-compose exec db pg_isready -U football_user
docker-compose exec redis redis-cli ping
```

检查服务健康状态
docker-compose exec app curl -f http://localhost:8000/health
docker-compose exec db pg_isready -U football_user
docker-compose exec redis redis-cli ping
```
###
###2. Kubernetes 部署

#### ✅ 检查清单：K8s准备

- [ ] **集群连接**: kubectl配置正确
- [ ] **命名空间**: 生产命名空间已创建
- [ ] **密钥配置**: Kubernetes secrets已创建
- [ ] **配置映射**: ConfigMaps已创建
- [ ] **存储类**: PersistentVolume配置正确

#### ☸️ Kubernetes 部署命令

```bash
2. Kubernetes 部署

#### ✅ 检查清单：K8s准备

- [ ] **集群连接**: kubectl配置正确
- [ ] **命名空间**: 生产命名空间已创建
- [ ] **密钥配置**: Kubernetes secrets已创建
- [ ] **配置映射**: ConfigMaps已创建
- [ ] **存储类**: PersistentVolume配置正确

#### ☸️ Kubernetes 部署命令

```bash#
#=============================================================================
=============================================================================#
#1. 命名空间准备
1. 命名空间准备#
#=============================================================================

=============================================================================
#
#创建生产命名空间
kubectl create namespace football-production

创建生产命名空间
kubectl create namespace football-production
#
#设置默认命名空间
kubectl config set-context --current --namespace=football-production

设置默认命名空间
kubectl config set-context --current --namespace=football-production
#
#=============================================================================
=============================================================================#
#2. 密钥和配置
2. 密钥和配置#
#=============================================================================

=============================================================================
#
#创建数据库密钥
kubectl create secret generic db-secrets \
  --from-literal=db-user=football_user \
  --from-literal=db-password=your_secure_db_password_here \
  --from-literal=postgres-password=your_secure_postgres_password_here

创建数据库密钥
kubectl create secret generic db-secrets \
  --from-literal=db-user=football_user \
  --from-literal=db-password=your_secure_db_password_here \
  --from-literal=postgres-password=your_secure_postgres_password_here
#
#创建Redis密钥
kubectl create secret generic redis-secrets \
  --from-literal=redis-password=your_secure_redis_password_here

创建Redis密钥
kubectl create secret generic redis-secrets \
  --from-literal=redis-password=your_secure_redis_password_here
#
#创建应用密钥
kubectl create secret generic app-secrets \
  --from-literal=jwt-secret-key=your_super_secure_jwt_secret_key_here \
  --from-literal=minio-secret-key=your_minio_secret_key_here

创建应用密钥
kubectl create secret generic app-secrets \
  --from-literal=jwt-secret-key=your_super_secure_jwt_secret_key_here \
  --from-literal=minio-secret-key=your_minio_secret_key_here
#
#创建ConfigMap
kubectl create configmap app-config \
  --from-file=configs/ \
  --from-literal=environment=production \
  --from-literal=log-level=INFO

创建ConfigMap
kubectl create configmap app-config \
  --from-file=configs/ \
  --from-literal=environment=production \
  --from-literal=log-level=INFO
#
#=============================================================================
=============================================================================#
#3. 存储配置
3. 存储配置#
#=============================================================================

=============================================================================
#
#创建PersistentVolumeClaims
kubectl apply -f k8s/storage/postgres-pvc.yaml
kubectl apply -f k8s/storage/redis-pvc.yaml
kubectl apply -f k8s/storage/minio-pvc.yaml

创建PersistentVolumeClaims
kubectl apply -f k8s/storage/postgres-pvc.yaml
kubectl apply -f k8s/storage/redis-pvc.yaml
kubectl apply -f k8s/storage/minio-pvc.yaml
#
#=============================================================================
=============================================================================#
#4. 数据库部署
4. 数据库部署#
#=============================================================================

=============================================================================
#
#部署PostgreSQL
kubectl apply -f k8s/database/postgres-deployment.yaml
kubectl apply -f k8s/database/postgres-service.yaml

部署PostgreSQL
kubectl apply -f k8s/database/postgres-deployment.yaml
kubectl apply -f k8s/database/postgres-service.yaml
#
#等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s

等待数据库就绪
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
#
#部署Redis
kubectl apply -f k8s/cache/redis-deployment.yaml
kubectl apply -f k8s/cache/redis-service.yaml

部署Redis
kubectl apply -f k8s/cache/redis-deployment.yaml
kubectl apply -f k8s/cache/redis-service.yaml
#
#等待Redis就绪
kubectl wait --for=condition=ready pod -l app=redis --timeout=120s

等待Redis就绪
kubectl wait --for=condition=ready pod -l app=redis --timeout=120s
#
#=============================================================================
=============================================================================#
#5. 消息队列部署
5. 消息队列部署#
#=============================================================================

=============================================================================
#
#部署Kafka
kubectl apply -f k8s/messaging/zookeeper-deployment.yaml
kubectl apply -f k8s/messaging/zookeeper-service.yaml
kubectl apply -f k8s/messaging/kafka-deployment.yaml
kubectl apply -f k8s/messaging/kafka-service.yaml

部署Kafka
kubectl apply -f k8s/messaging/zookeeper-deployment.yaml
kubectl apply -f k8s/messaging/zookeeper-service.yaml
kubectl apply -f k8s/messaging/kafka-deployment.yaml
kubectl apply -f k8s/messaging/kafka-service.yaml
#
#=============================================================================
=============================================================================#
#6. 存储和ML服务
6. 存储和ML服务#
