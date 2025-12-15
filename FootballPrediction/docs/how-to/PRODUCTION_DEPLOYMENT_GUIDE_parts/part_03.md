#创建模型测试脚本
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

创建模型测试脚本
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
#
#运行模型测试
python model_test.py

运行模型测试
python model_test.py
#
#=============================================================================
=============================================================================#
#2. 模型性能验证
2. 模型性能验证#
#=============================================================================

=============================================================================
#
#检查模型版本和元数据
curl -s http://localhost:5002/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[] | {version, status, creation_timestamp}'

检查模型版本和元数据
curl -s http://localhost:5002/api/2.0/registered-models/get?name=football-match-predictor | jq '.latest_versions[] | {version, status, creation_timestamp}'
#
#验证模型文件存在
docker exec football_prediction_mlflow ls -la /mlflow-artifacts/

验证模型文件存在
docker exec football_prediction_mlflow ls -la /mlflow-artifacts/
#
#检查模型性能指标
curl -s http://localhost:5002/api/2.0/mlflow/runs/search | jq '.runs[] | select(.tags.mlflow.runName | contains("production")) | {run_id, metrics}'
```

检查模型性能指标
curl -s http://localhost:5002/api/2.0/mlflow/runs/search | jq '.runs[] | select(.tags.mlflow.runName | contains("production")) | {run_id, metrics}'
```
###
###2. 性能验证

#### ✅ 检查清单：性能验证

- [ ] **响应时间**: API响应时间在可接受范围内
- [ ] **吞吐量**: 系统支持预期的并发请求量
- [ ] **资源使用**: CPU、内存、磁盘使用正常
- [ ] **数据库性能**: 查询响应时间正常
- [ ] **缓存效率**: 缓存命中率符合预期
- [ ] **错误率**: 系统错误率低于阈值

#### ⚡ 基础压力测试

```bash
2. 性能验证

#### ✅ 检查清单：性能验证

- [ ] **响应时间**: API响应时间在可接受范围内
- [ ] **吞吐量**: 系统支持预期的并发请求量
- [ ] **资源使用**: CPU、内存、磁盘使用正常
- [ ] **数据库性能**: 查询响应时间正常
- [ ] **缓存效率**: 缓存命中率符合预期
- [ ] **错误率**: 系统错误率低于阈值

#### ⚡ 基础压力测试

```bash#
#=============================================================================
=============================================================================#
#1. 使用Apache Bench进行API压力测试
1. 使用Apache Bench进行API压力测试#
#=============================================================================

=============================================================================
#
#健康检查接口测试
ab -n 1000 -c 10 -t 30 http://localhost:8000/health

健康检查接口测试
ab -n 1000 -c 10 -t 30 http://localhost:8000/health
#
#API接口测试
ab -n 500 -c 20 -t 60 -H "Content-Type: application/json" \
  -p test_payload.json \
  http://localhost:8000/api/v1/predictions/

API接口测试
ab -n 500 -c 20 -t 60 -H "Content-Type: application/json" \
  -p test_payload.json \
  http://localhost:8000/api/v1/predictions/
#
#创建测试负载文件
cat > test_payload.json << 'EOF'
{
  "match_id": "stress_test_001",
  "home_team_id": 1,
  "away_team_id": 2,
  "league_id": 1,
  "match_date": "2025-09-25T15:00:00Z"
}
EOF

创建测试负载文件
cat > test_payload.json << 'EOF'
{
  "match_id": "stress_test_001",
  "home_team_id": 1,
  "away_team_id": 2,
  "league_id": 1,
  "match_date": "2025-09-25T15:00:00Z"
}
EOF
#
#并发测试不同并发级别
for concurrency in 5 10 20 50; do
  echo "Testing with $concurrency concurrent users..."
  ab -n 200 -c $concurrency -t 30 http://localhost:8000/health
  echo "---"
done

并发测试不同并发级别
for concurrency in 5 10 20 50; do
  echo "Testing with $concurrency concurrent users..."
  ab -n 200 -c $concurrency -t 30 http://localhost:8000/health
  echo "---"
done
#
#=============================================================================
=============================================================================#
#2. 使用Locust进行分布式负载测试
2. 使用Locust进行分布式负载测试#
#=============================================================================

=============================================================================
#
#创建Locust测试文件
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

创建Locust测试文件
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
#
#启动Locust测试（需要先安装locust）
启动Locust测试（需要先安装locust）#
#locust -f locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=5m

locust -f locustfile.py --host=http://localhost:8000 --users=50 --spawn-rate=5 --run-time=5m
#
#=============================================================================
=============================================================================#
#3. 使用k6进行现代化性能测试
3. 使用k6进行现代化性能测试#
#=============================================================================

=============================================================================
#
#创建k6测试脚本
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

创建k6测试脚本
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
#
#运行k6测试（需要先安装k6）
运行k6测试（需要先安装k6）#
#k6 run k6_test.js

k6 run k6_test.js
#
#=============================================================================
=============================================================================#
#4. 数据库性能测试
4. 数据库性能测试#
#=============================================================================

=============================================================================
#
#数据库查询性能测试
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
EXPLAIN ANALYZE SELECT * FROM matches LIMIT 100;
"

docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
EXPLAIN ANALYZE SELECT * FROM predictions WHERE confidence > 0.8 LIMIT 50;
"

数据库查询性能测试
docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
EXPLAIN ANALYZE SELECT * FROM matches LIMIT 100;
"

docker exec football_prediction_db psql -U football_user -d football_prediction_dev -c "
EXPLAIN ANALYZE SELECT * FROM predictions WHERE confidence > 0.8 LIMIT 50;
"
#
#连接池测试
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

连接池测试
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
#
#运行数据库池测试
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

运行数据库池测试
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
###
###3. 监控验证

#### ✅ 检查清单：监控验证

- [ ] **Grafana仪表盘**: 所有仪表盘加载正常
- [ ] **Prometheus指标**: 指标数据正常采集
- [ **AlertManager配置**: 告警规则和通知配置正确
- [ ] **告警推送**: 告警通知正常发送
- [ ] **日志聚合**: 日志收集和查询正常
- [ ] **业务指标**: 业务监控指标正常显示

#### 📈 Grafana 仪表盘验证

```bash
3. 监控验证

#### ✅ 检查清单：监控验证

- [ ] **Grafana仪表盘**: 所有仪表盘加载正常
- [ ] **Prometheus指标**: 指标数据正常采集
- [ **AlertManager配置**: 告警规则和通知配置正确
- [ ] **告警推送**: 告警通知正常发送
- [ ] **日志聚合**: 日志收集和查询正常
- [ ] **业务指标**: 业务监控指标正常显示

#### 📈 Grafana 仪表盘验证

```bash#
#=============================================================================
=============================================================================#
#1. Grafana服务访问验证
1. Grafana服务访问验证#
#=============================================================================

=============================================================================
#
#检查Grafana服务状态
curl -f http://localhost:3000/api/health

检查Grafana服务状态
curl -f http://localhost:3000/api/health
#
#检查数据源配置
curl -u admin:your_grafana_password http://localhost:3000/api/datasources | jq '.[].name'

检查数据源配置
curl -u admin:your_grafana_password http://localhost:3000/api/datasources | jq '.[].name'
#
#检查仪表盘列表
curl -u admin:your_grafana_password http://localhost:3000/api/search | jq '.[].title'

检查仪表盘列表
curl -u admin:your_grafana_password http://localhost:3000/api/search | jq '.[].title'
#
#=============================================================================
=============================================================================#
#2. 仪表盘加载测试
2. 仪表盘加载测试#
#=============================================================================

=============================================================================
#
#检查主要仪表盘
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

检查主要仪表盘
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
#
#=============================================================================
=============================================================================#
#3. 面板数据验证
3. 面板数据验证#
#=============================================================================

=============================================================================
#
#检查关键指标是否正常显示
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=up" | \
    jq '.data.result[]'

检查关键指标是否正常显示
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=up" | \
    jq '.data.result[]'
#
#检查API响应时间指标
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=football_prediction_latency_seconds_sum" | \
    jq '.data.result[]'

检查API响应时间指标
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=football_prediction_latency_seconds_sum" | \
    jq '.data.result[]'
#
#检查数据库连接指标
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=pg_stat_database_numbackends" | \
    jq '.data.result[]'
```

#### 🚨 Prometheus 规则触发测试

```bash
检查数据库连接指标
curl -s -u admin:your_grafana_password \
    "http://localhost:3000/api/datasources/proxy/1/api/v1/query?query=pg_stat_database_numbackends" | \
    jq '.data.result[]'
```

#### 🚨 Prometheus 规则触发测试

```bash#
#=============================================================================
=============================================================================#
#1. Prometheus 服务验证
1. Prometheus 服务验证#
#=============================================================================

=============================================================================
#
#检查Prometheus健康状态
curl -f http://localhost:9090/-/ready

检查Prometheus健康状态
curl -f http://localhost:9090/-/ready
#
#检查目标状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {health, labels}'

检查目标状态
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {health, labels}'
#
#检查规则配置
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | {name, rules}'

检查规则配置
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[] | {name, rules}'
#
#=============================================================================
=============================================================================#
#2. 告警规则测试
2. 告警规则测试#
#=============================================================================

=============================================================================
#
#检查告警规则状态
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {name, state, labels}'

检查告警规则状态
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | {name, state, labels}'
#
#检查告警规则加载
curl -s http://localhost:9090/api/v1/rules?type=alert | jq '.data.groups[].rules[] | {name, health, lastError}'

检查告警规则加载
curl -s http://localhost:9090/api/v1/rules?type=alert | jq '.data.groups[].rules[] | {name, health, lastError}'
#
#=============================================================================
=============================================================================#
#3. 模拟告警触发
3. 模拟告警触发#
#=============================================================================

=============================================================================
#
#创建高CPU使用率告警测试
docker exec football_prediction_app sh -c "dd if=/dev/zero of=/dev/null bs=1G count=10 &"

创建高CPU使用率告警测试
docker exec football_prediction_app sh -c "dd if=/dev/zero of=/dev/null bs=1G count=10 &"
#
#检查CPU使用率告警是否触发
sleep 30
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="HighCpuUsage")'

检查CPU使用率告警是否触发
sleep 30
curl -s http://localhost:9090/api/v1/alerts | jq '.data.alerts[] | select(.labels.alertname=="HighCpuUsage")'
#
#停止CPU压力测试
docker exec football_prediction_app pkill dd

停止CPU压力测试
docker exec football_prediction_app pkill dd
#
#=============================================================================
=============================================================================#
#4. AlertManager 通知测试
4. AlertManager 通知测试#
#=============================================================================

=============================================================================
#
#检查AlertManager配置
curl -f http://localhost:9093/-/ready

检查AlertManager配置
curl -f http://localhost:9093/-/ready
#
#检查告警路由配置
curl -s http://localhost:9093/api/v1/alerts/groups | jq '.[] | {receiver, alerts}'

检查告警路由配置
curl -s http://localhost:9093/api/v1/alerts/groups | jq '.[] | {receiver, alerts}'
#
#发送测试告警
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

发送测试告警
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
#
#=============================================================================
=============================================================================#
#5. 监控指标验证
5. 监控指标验证#
#=============================================================================

=============================================================================
#
#检查应用指标
curl -s http://localhost:8000/metrics | grep -E "football_predictions_total|football_prediction_latency_seconds"

检查应用指标
curl -s http://localhost:8000/metrics | grep -E "football_predictions_total|football_prediction_latency_seconds"
#
#检查系统指标
curl -s http://localhost:9100/metrics | grep node_cpu_seconds_total

检查系统指标
curl -s http://localhost:9100/metrics | grep node_cpu_seconds_total
#
#检查数据库指标
curl -s http://localhost:9187/metrics | grep pg_stat_database

检查数据库指标
curl -s http://localhost:9187/metrics | grep pg_stat_database
#
#检查Redis指标
curl -s http://localhost:9121/metrics | grep redis_keyspace_hits_total
```

---

检查Redis指标
curl -s http://localhost:9121/metrics | grep redis_keyspace_hits_total
```

---
##
##🔄 回滚演练

🔄 回滚演练
###
###1. 容器回滚

#### ✅ 检查清单：容器回滚准备

- [ ] **镜像备份**: 确保有可用的回滚镜像
- [ ] **版本记录**: 记录当前部署版本信息
- [ ] **回滚脚本**: 回滚脚本准备就绪
- [ ] **数据备份**: 数据库和缓存已备份
- [ ] **回滚验证**: 回滚验证步骤明确

#### 🐳 使用上一版本镜像快速回退

```bash
