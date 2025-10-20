#=============================================================================

=============================================================================
#
#部署MinIO
kubectl apply -f k8s/storage/minio-deployment.yaml
kubectl apply -f k8s/storage/minio-service.yaml

部署MinIO
kubectl apply -f k8s/storage/minio-deployment.yaml
kubectl apply -f k8s/storage/minio-service.yaml
#
#部署MLflow
kubectl apply -f k8s/ml/mlflow-deployment.yaml
kubectl apply -f k8s/ml/mlflow-service.yaml

部署MLflow
kubectl apply -f k8s/ml/mlflow-deployment.yaml
kubectl apply -f k8s/ml/mlflow-service.yaml
#
#=============================================================================
=============================================================================#
#7. 监控系统部署
7. 监控系统部署#
#=============================================================================

=============================================================================
#
#部署Prometheus
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml
kubectl apply -f k8s/monitoring/prometheus-service.yaml

部署Prometheus
kubectl apply -f k8s/monitoring/prometheus-deployment.yaml
kubectl apply -f k8s/monitoring/prometheus-service.yaml
#
#部署Grafana
kubectl apply -f k8s/monitoring/grafana-deployment.yaml
kubectl apply -f k8s/monitoring/grafana-service.yaml

部署Grafana
kubectl apply -f k8s/monitoring/grafana-deployment.yaml
kubectl apply -f k8s/monitoring/grafana-service.yaml
#
#部署AlertManager
kubectl apply -f k8s/monitoring/alertmanager-deployment.yaml
kubectl apply -f k8s/monitoring/alertmanager-service.yaml

部署AlertManager
kubectl apply -f k8s/monitoring/alertmanager-deployment.yaml
kubectl apply -f k8s/monitoring/alertmanager-service.yaml
#
#=============================================================================
=============================================================================#
#8. 应用服务部署
8. 应用服务部署#
#=============================================================================

=============================================================================
#
#部署应用
kubectl apply -f k8s/app/football-prediction-deployment.yaml
kubectl apply -f k8s/app/football-prediction-service.yaml

部署应用
kubectl apply -f k8s/app/football-prediction-deployment.yaml
kubectl apply -f k8s/app/football-prediction-service.yaml
#
#部署任务队列
kubectl apply -f k8s/tasks/celery-worker-deployment.yaml
kubectl apply -f k8s/tasks/celery-beat-deployment.yaml

部署任务队列
kubectl apply -f k8s/tasks/celery-worker-deployment.yaml
kubectl apply -f k8s/tasks/celery-beat-deployment.yaml
#
#部署Ingress
kubectl apply -f k8s/ingress/football-prediction-ingress.yaml

部署Ingress
kubectl apply -f k8s/ingress/football-prediction-ingress.yaml
#
#=============================================================================
=============================================================================#
#9. 验证部署
9. 验证部署#
#=============================================================================

=============================================================================
#
#检查所有Pod状态
kubectl get pods -o wide

检查所有Pod状态
kubectl get pods -o wide
#
#检查服务状态
kubectl get services

检查服务状态
kubectl get services
#
#检查Ingress状态
kubectl get ingress
```

检查Ingress状态
kubectl get ingress
```
###
###3. 服务启动顺序说明

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

3. 服务启动顺序说明

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
###
###4. 健康检查验证

#### 🏥 健康检查端点验证

```bash
4. 健康检查验证

#### 🏥 健康检查端点验证

```bash#
#=============================================================================
=============================================================================#
#1. 应用服务健康检查
1. 应用服务健康检查#
#=============================================================================

=============================================================================
#
#主应用健康检查
curl -f http://localhost:8000/health
curl -f http://localhost:8000/health/liveness
curl -f http://localhost:8000/health/readiness

主应用健康检查
curl -f http://localhost:8000/health
curl -f http://localhost:8000/health/liveness
curl -f http://localhost:8000/health/readiness
#
#API文档检查
curl -f http://localhost:8000/docs
curl -f http://localhost:8000/openapi.json

API文档检查
curl -f http://localhost:8000/docs
curl -f http://localhost:8000/openapi.json
#
#=============================================================================
=============================================================================#
#2. 数据库健康检查
2. 数据库健康检查#
#=============================================================================

=============================================================================
#
#PostgreSQL健康检查
docker exec football_prediction_db pg_isready -U football_user -d football_prediction_dev

PostgreSQL健康检查
docker exec football_prediction_db pg_isready -U football_user -d football_prediction_dev
#
#Redis健康检查
docker exec football_prediction_redis redis-cli ping

Redis健康检查
docker exec football_prediction_redis redis-cli ping
#
#MLflow数据库检查
docker exec football_prediction_mlflow-db pg_isready -U mlflow_user -d mlflow

MLflow数据库检查
docker exec football_prediction_mlflow-db pg_isready -U mlflow_user -d mlflow
#
#=============================================================================
=============================================================================#
#3. 消息队列健康检查
3. 消息队列健康检查#
#=============================================================================

=============================================================================
#
#Kafka健康检查
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list

Kafka健康检查
docker exec football_prediction_kafka kafka-topics --bootstrap-server localhost:9092 --list
#
#Zookeeper健康检查
docker exec football_prediction_zookeeper echo "ruok" | nc localhost 2181

Zookeeper健康检查
docker exec football_prediction_zookeeper echo "ruok" | nc localhost 2181
#
#=============================================================================
=============================================================================#
#4. 存储服务健康检查
4. 存储服务健康检查#
#=============================================================================

=============================================================================
#
#MinIO健康检查
curl -f http://localhost:9000/minio/health/live
curl -f http://localhost:9001/minio/health/live

MinIO健康检查
curl -f http://localhost:9000/minio/health/live
curl -f http://localhost:9001/minio/health/live
#
#MLflow健康检查
curl -f http://localhost:5002/health

MLflow健康检查
curl -f http://localhost:5002/health
#
#Marquez健康检查
curl -f http://localhost:5000/api/v1/namespaces

Marquez健康检查
curl -f http://localhost:5000/api/v1/namespaces
#
#=============================================================================
=============================================================================#
#5. 监控服务健康检查
5. 监控服务健康检查#
#=============================================================================

=============================================================================
#
#Prometheus健康检查
curl -f http://localhost:9090/-/ready

Prometheus健康检查
curl -f http://localhost:9090/-/ready
#
#Grafana健康检查
curl -f http://localhost:3000/api/health

Grafana健康检查
curl -f http://localhost:3000/api/health
#
#AlertManager健康检查
curl -f http://localhost:9093/-/ready

AlertManager健康检查
curl -f http://localhost:9093/-/ready
#
#=============================================================================
=============================================================================#
#6. 任务队列健康检查
6. 任务队列健康检查#
#=============================================================================

=============================================================================
#
#Celery Flower健康检查
curl -f http://localhost:5555/

Celery Flower健康检查
curl -f http://localhost:5555/
#
#检查Celery工作状态
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect active
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect scheduled
```

检查Celery工作状态
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect active
docker exec football_prediction_celery-worker celery -A football_prediction.celery inspect scheduled
```
###
###5. 日志检查要点

#### 📋 日志检查清单和关键错误模式

```bash
5. 日志检查要点

#### 📋 日志检查清单和关键错误模式

```bash#
#=============================================================================
=============================================================================#
#1. 应用服务日志检查
1. 应用服务日志检查#
#=============================================================================

=============================================================================
#
#查看应用启动日志
docker-compose logs --tail=100 app

查看应用启动日志
docker-compose logs --tail=100 app
#
#关键启动信息查找
docker-compose logs app | grep -E "(Starting|Started|Ready|Listening|Database connected|Cache connected)"

关键启动信息查找
docker-compose logs app | grep -E "(Starting|Started|Ready|Listening|Database connected|Cache connected)"
#
#错误日志检查
docker-compose logs app | grep -E "(ERROR|CRITICAL|Exception|Failed|Connection refused|Timeout)"

错误日志检查
docker-compose logs app | grep -E "(ERROR|CRITICAL|Exception|Failed|Connection refused|Timeout)"
#
#=============================================================================
=============================================================================#
#2. 数据库日志检查
2. 数据库日志检查#
#=============================================================================

=============================================================================
#
#PostgreSQL日志
docker-compose logs --tail=50 db

PostgreSQL日志
docker-compose logs --tail=50 db
#
#关键数据库信息
docker-compose logs db | grep -E "(ready|accepting connections|authentication|database system is ready)"

关键数据库信息
docker-compose logs db | grep -E "(ready|accepting connections|authentication|database system is ready)"
#
#数据库错误检查
docker-compose logs db | grep -E "(FATAL|ERROR|connection|authentication|permission)"

数据库错误检查
docker-compose logs db | grep -E "(FATAL|ERROR|connection|authentication|permission)"
#
#=============================================================================
=============================================================================#
#3. 缓存和队列日志检查
3. 缓存和队列日志检查#
#=============================================================================

=============================================================================
#
#Redis日志
docker-compose logs --tail=50 redis

Redis日志
docker-compose logs --tail=50 redis
#
#Kafka日志
docker-compose logs --tail=50 kafka

Kafka日志
docker-compose logs --tail=50 kafka
#
#Celery日志
docker-compose logs --tail=50 celery-worker

Celery日志
docker-compose logs --tail=50 celery-worker
#
#=============================================================================
=============================================================================#
#4. 监控系统日志检查
4. 监控系统日志检查#
#=============================================================================

=============================================================================
#
#Prometheus日志
docker-compose logs --tail=30 prometheus

Prometheus日志
docker-compose logs --tail=30 prometheus
#
#Grafana日志
docker-compose logs --tail=30 grafana

Grafana日志
docker-compose logs --tail=30 grafana
#
#=============================================================================
=============================================================================#
#5. 性能指标日志检查
5. 性能指标日志检查#
#=============================================================================

=============================================================================
#
#查看性能相关日志
docker-compose logs app | grep -E "(latency|response time|memory|cpu|slow query)"

查看性能相关日志
docker-compose logs app | grep -E "(latency|response time|memory|cpu|slow query)"
#
#检查数据库查询性能
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

检查数据库查询性能
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
##
##✅ 部署后验证

✅ 部署后验证
###
###1. 功能验证

#### ✅ 检查清单：功能验证

- [ ] **API服务响应**: 所有核心API接口正常响应
- [ ] **数据库读写**: 数据库连接正常，读写操作成功
- [ ] **缓存功能**: Redis缓存读写正常
- [ ] **模型预测**: 模型加载和预测功能正常
- [ ] **任务队列**: Celery任务正常执行
- [ ] **文件存储**: MinIO文件上传下载正常

#### 🧪 API 核心接口调用测试

```bash
1. 功能验证

#### ✅ 检查清单：功能验证

- [ ] **API服务响应**: 所有核心API接口正常响应
- [ ] **数据库读写**: 数据库连接正常，读写操作成功
- [ ] **缓存功能**: Redis缓存读写正常
- [ ] **模型预测**: 模型加载和预测功能正常
- [ ] **任务队列**: Celery任务正常执行
- [ ] **文件存储**: MinIO文件上传下载正常

#### 🧪 API 核心接口调用测试

```bash#
#=============================================================================
=============================================================================#
#1. 基础API测试
1. 基础API测试#
#=============================================================================

=============================================================================
#
#服务信息测试
curl -X GET http://localhost:8000/ \
  -H "Content-Type: application/json" \
  | jq .

服务信息测试
curl -X GET http://localhost:8000/ \
  -H "Content-Type: application/json" \
  | jq .
#
#健康检查测试
curl -X GET http://localhost:8000/health \
  -H "Content-Type: application/json" \
  | jq .

健康检查测试
curl -X GET http://localhost:8000/health \
  -H "Content-Type: application/json" \
  | jq .
#
#API文档访问测试
curl -X GET http://localhost:8000/docs \
  -I

API文档访问测试
curl -X GET http://localhost:8000/docs \
  -I
#
#=============================================================================
=============================================================================#
#2. 预测功能测试
2. 预测功能测试#
#=============================================================================

=============================================================================
#
#获取预测接口文档
curl -X GET http://localhost:8000/api/v1/predictions/ \
  -H "Content-Type: application/json" \
  | jq .

获取预测接口文档
curl -X GET http://localhost:8000/api/v1/predictions/ \
  -H "Content-Type: application/json" \
  | jq .
#
#创建预测请求
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

创建预测请求
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
#
#获取预测结果
curl -X GET http://localhost:8000/api/v1/predictions/test_prediction_001 \
  -H "Content-Type: application/json" \
  | jq .

获取预测结果
curl -X GET http://localhost:8000/api/v1/predictions/test_prediction_001 \
  -H "Content-Type: application/json" \
  | jq .
#
#=============================================================================
=============================================================================#
#3. 数据接口测试
3. 数据接口测试#
#=============================================================================

=============================================================================
#
#获取比赛数据
curl -X GET http://localhost:8000/api/v1/data/matches?limit=5 \
  -H "Content-Type: application/json" \
  | jq .

获取比赛数据
curl -X GET http://localhost:8000/api/v1/data/matches?limit=5 \
  -H "Content-Type: application/json" \
  | jq .
#
#获取队伍数据
curl -X GET http://localhost:8000/api/v1/data/teams?limit=5 \
  -H "Content-Type: application/json" \
  | jq .

获取队伍数据
curl -X GET http://localhost:8000/api/v1/data/teams?limit=5 \
  -H "Content-Type: application/json" \
  | jq .
#
#获取特征数据
curl -X GET http://localhost:8000/api/v1/features/ \
  -H "Content-Type: application/json" \
  | jq .

获取特征数据
curl -X GET http://localhost:8000/api/v1/features/ \
  -H "Content-Type: application/json" \
  | jq .
#
#获取队伍特征
curl -X GET http://localhost:8000/api/v1/features/teams/1 \
  -H "Content-Type: application/json" \
  | jq .

获取队伍特征
curl -X GET http://localhost:8000/api/v1/features/teams/1 \
  -H "Content-Type: application/json" \
  | jq .
#
#=============================================================================
=============================================================================#
#4. 监控接口测试
4. 监控接口测试#
#=============================================================================

=============================================================================
#
#获取系统指标
curl -X GET http://localhost:8000/api/v1/monitoring/metrics \
  -H "Content-Type: application/json" \
  | jq .

获取系统指标
curl -X GET http://localhost:8000/api/v1/monitoring/metrics \
  -H "Content-Type: application/json" \
  | jq .
#
#获取Prometheus指标
curl -X GET http://localhost:8000/metrics \
  | head -20
```

#### 🗄️ 数据库读写验证

```bash
获取Prometheus指标
curl -X GET http://localhost:8000/metrics \
  | head -20
```

#### 🗄️ 数据库读写验证

```bash#
#=============================================================================
=============================================================================#
#1. 数据库连接验证
1. 数据库连接验证#
#=============================================================================

=============================================================================
#
#创建数据库连接测试脚本
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

创建数据库连接测试脚本
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
#
#运行数据库测试
python db_test.py

运行数据库测试
python db_test.py
#
#=============================================================================
=============================================================================#
#2. 数据一致性验证
2. 数据一致性验证#
#=============================================================================

=============================================================================
#
#检查数据库表完整性
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"

检查数据库表完整性
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;
"
#
#检查索引完整性
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
"

检查索引完整性
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
SELECT indexname, tablename
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY tablename, indexname;
"
#
#=============================================================================
=============================================================================#
#3. 缓存读写验证
3. 缓存读写验证#
#=============================================================================

=============================================================================
#
#创建缓存测试脚本
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

创建缓存测试脚本
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
#
#运行缓存测试
python cache_test.py
```

#### 🤖 模型预测结果正确性检查

```bash
运行缓存测试
python cache_test.py
```

#### 🤖 模型预测结果正确性检查

```bash#
#=============================================================================
=============================================================================#
#1. 模型加载验证
1. 模型加载验证#
#=============================================================================

=============================================================================
#
