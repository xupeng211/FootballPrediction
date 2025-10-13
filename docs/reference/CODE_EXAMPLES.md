# 代码示例和使用指南

## 概述

本文档提供了FootballPrediction项目的常见使用场景和代码示例。

## 目录

- [快速开始](#快速开始)
- [API使用](#api使用)
- [数据处理](#数据处理)
- [模型训练](#模型训练)
- [测试](#测试)

## 快速开始

### 1. 环境设置

```bash
# 克隆项目
git clone https://github.com/your-repo/FootballPrediction.git
cd FootballPrediction

# 创建虚拟环境
make venv

# 安装依赖
make install

# 验证安装
make env-check
```

### 2. 启动服务

```bash
# 开发模式
uvicorn src.main:app --reload

# 生产模式
docker-compose up -d
```

### 3. 验证服务

```bash
# 健康检查
curl http://localhost:8000/api/health

# 查看API文档
open http://localhost:8000/docs
```

## API使用

### 健康检查

```python
import requests

# 简单健康检查
response = requests.get("http://localhost:8000/api/health")
print(response.json())

# 输出:
# {
#   "status": "healthy",
#   "timestamp": "2024-01-01T12:00:00Z",
#   "service": "football-prediction-api",
#   "version": "1.0.0"
# }
```

### 创建预测

```python
from datetime import datetime
import requests

# 预测数据
prediction_data = {
    "home_team": "Manchester United",
    "away_team": "Liverpool",
    "match_date": datetime.now().isoformat(),
    "league": "Premier League"
}

# 发送请求
response = requests.post(
    "http://localhost:8000/api/v1/predictions",
    json=prediction_data,
    headers={"Authorization": "Bearer YOUR_TOKEN"}
)

# 获取预测结果
prediction = response.json()
print(f"预测: {prediction['prediction']}")
print(f"置信度: {prediction['confidence']}")
```

### 批量预测

```python
import asyncio
import aiohttp

async def predict_match(session, match_data):
    """异步预测单场比赛"""
    async with session.post(
        "http://localhost:8000/api/v1/predictions",
        json=match_data
    ) as response:
        return await response.json()

async def batch_predictions(matches):
    """批量预测多场比赛"""
    async with aiohttp.ClientSession() as session:
        tasks = [predict_match(session, match) for match in matches]
        results = await asyncio.gather(*tasks)
        return results

# 使用示例
matches = [
    {"home_team": "Team A", "away_team": "Team B", ...},
    {"home_team": "Team C", "away_team": "Team D", ...},
]
predictions = asyncio.run(batch_predictions(matches))
```

## 数据处理

### 导入比赛数据

```python
from src.data.collectors.fixtures_collector import FixturesCollector
import asyncio

async def import_fixtures():
    """导入赛程数据"""
    collector = FixturesCollector()

    # 获取特定日期范围的赛程
    fixtures = await collector.collect_fixtures(
        league="Premier League",
        start_date="2024-01-01",
        end_date="2024-01-31"
    )

    print(f"导入了 {len(fixtures)} 场比赛")
    return fixtures

# 运行
fixtures = asyncio.run(import_fixtures())
```

### 数据清洗

```python
from src.data.processing.football_data_cleaner import FootballDataCleaner
import pandas as pd

# 创建清洗器
cleaner = FootballDataCleaner()

# 加载原始数据
raw_data = pd.read_csv("data/raw_matches.csv")

# 清洗数据
cleaned_data = cleaner.clean(raw_data)

# 验证数据质量
quality_report = cleaner.validate(cleaned_data)
print(f"数据质量得分: {quality_report['score']}")

# 保存清洗后的数据
cleaned_data.to_csv("data/clean_matches.csv", index=False)
```

### 特征工程

```python
from src.features.feature_calculator import FeatureCalculator

# 创建特征计算器
calculator = FeatureCalculator()

# 计算单场比赛的特征
match_features = calculator.calculate_match_features(
    home_team="Manchester United",
    away_team="Liverpool",
    match_date="2024-01-15"
)

print("计算的特征:")
for feature, value in match_features.items():
    print(f"  {feature}: {value}")

# 批量计算特征
matches_df = pd.read_csv("data/matches.csv")
features_df = calculator.calculate_batch_features(matches_df)
```

## 模型训练

### 训练新模型

```python
from src.models.prediction_service import PredictionService
from sklearn.model_selection import train_test_split
import pandas as pd

# 加载训练数据
data = pd.read_csv("data/training_data.csv")
X = data.drop(['result'], axis=1)
y = data['result']

# 分割数据集
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 训练模型
service = PredictionService()
model = service.train_model(X_train, y_train)

# 评估模型
metrics = service.evaluate_model(model, X_test, y_test)
print(f"准确率: {metrics['accuracy']:.2%}")
print(f"F1分数: {metrics['f1_score']:.2f}")

# 保存模型
service.save_model(model, "models/prediction_model_v1.pkl")
```

### 模型推理

```python
from src.models.prediction_service import PredictionService

# 加载模型
service = PredictionService()
model = service.load_model("models/prediction_model_v1.pkl")

# 预测单场比赛
prediction = service.predict(
    home_team="Team A",
    away_team="Team B",
    features={...}
)

print(f"预测结果: {prediction['outcome']}")
print(f"各结果概率:")
print(f"  主胜: {prediction['probabilities']['home_win']:.2%}")
print(f"  平局: {prediction['probabilities']['draw']:.2%}")
print(f"  客胜: {prediction['probabilities']['away_win']:.2%}")
```

## 缓存使用

### Redis缓存

```python
from src.cache.redis_manager import RedisManager
import asyncio

async def cache_example():
    """Redis缓存使用示例"""
    redis = RedisManager()

    # 设置缓存
    await redis.set("team:1", {"name": "Manchester United", "league": "EPL"})

    # 获取缓存
    team = await redis.get("team:1")
    print(team)

    # 设置带过期时间的缓存
    await redis.set("temp:data", "value", ttl=3600)  # 1小时过期

    # 批量操作
    await redis.mset({
        "team:1": "Man Utd",
        "team:2": "Liverpool",
        "team:3": "Chelsea"
    })

    teams = await redis.mget(["team:1", "team:2", "team:3"])

    # 删除缓存
    await redis.delete("temp:data")

asyncio.run(cache_example())
```

## 数据库操作

### 基础CRUD

```python
from src.database.connection import get_database_manager
from src.database.models.match import Match
from sqlalchemy import select

# 获取数据库连接
db_manager = get_database_manager()

async def database_example():
    """数据库操作示例"""
    async with db_manager.get_async_session() as session:
        # 创建
        new_match = Match(
            home_team="Team A",
            away_team="Team B",
            date="2024-01-15",
            league="Premier League"
        )
        session.add(new_match)
        await session.commit()

        # 查询
        result = await session.execute(
            select(Match).where(Match.league == "Premier League")
        )
        matches = result.scalars().all()

        # 更新
        match = matches[0]
        match.home_score = 2
        match.away_score = 1
        await session.commit()

        # 删除
        await session.delete(match)
        await session.commit()

import asyncio
asyncio.run(database_example())
```

## 监控和日志

### 添加日志

```python
import logging
from src.core.logger import get_logger

# 获取logger
logger = get_logger(__name__)

def process_data(data):
    """处理数据并记录日志"""
    logger.info(f"开始处理 {len(data)} 条数据")

    try:
        # 处理逻辑
        result = perform_processing(data)
        logger.info(f"成功处理 {len(result)} 条数据")
        return result
    except Exception as e:
        logger.error(f"处理数据失败: {str(e)}", exc_info=True)
        raise
```

### 性能监控

```python
from src.monitoring.metrics_collector import MetricsCollector
import time

# 创建metrics收集器
metrics = MetricsCollector()

def monitored_function():
    """带监控的函数"""
    start_time = time.time()

    try:
        # 业务逻辑
        result = expensive_operation()

        # 记录成功
        metrics.record_success('operation_name')
        return result

    except Exception as e:
        # 记录失败
        metrics.record_error('operation_name', str(e))
        raise

    finally:
        # 记录执行时间
        duration = time.time() - start_time
        metrics.record_duration('operation_name', duration)
```

## 测试

### 单元测试

```python
import pytest
from src.utils.string_utils import StringUtils

class TestStringUtils:
    """字符串工具测试"""

    def test_capitalize(self):
        """测试首字母大写"""
        result = StringUtils.capitalize_first_letter("hello")
        assert result == "Hello"

    @pytest.mark.parametrize("input,expected", [
        ("test", "Test"),
        ("", ""),
        ("HELLO", "HELLO"),
    ])
    def test_capitalize_multiple(self, input, expected):
        """测试多种情况"""
        assert StringUtils.capitalize_first_letter(input) == expected
```

### API集成测试

```python
import pytest
from fastapi.testclient import TestClient
from src.main import app

@pytest.fixture
def client():
    """测试客户端"""
    return TestClient(app)

def test_health_check(client):
    """测试健康检查端点"""
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"

def test_create_prediction(client):
    """测试创建预测"""
    prediction_data = {
        "home_team": "Team A",
        "away_team": "Team B",
        "match_date": "2024-01-15"
    }
    response = client.post("/api/v1/predictions", json=prediction_data)
    assert response.status_code == 201
```

## 配置管理

### 环境配置

```python
from src.core.config import get_settings

# 获取配置
settings = get_settings()

# 使用配置
database_url = settings.DATABASE_URL
redis_url = settings.REDIS_URL
debug_mode = settings.DEBUG

# 配置示例
print(f"环境: {settings.ENVIRONMENT}")
print(f"数据库: {settings.DATABASE_URL}")
print(f"日志级别: {settings.LOG_LEVEL}")
```

### 自定义配置

```python
import os
from pydantic import BaseSettings

class CustomConfig(BaseSettings):
    """自定义配置"""
    API_KEY: str
    MAX_RETRIES: int = 3
    TIMEOUT: int = 30

    class Config:
        env_file = ".env"

# 使用
config = CustomConfig()
```

## 实用工具

### 重试机制

```python
from src.utils.retry import retry_with_backoff
import aiohttp

@retry_with_backoff(max_attempts=3, backoff_factor=2)
async def fetch_data(url):
    """带重试的数据获取"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# 使用
data = await fetch_data("https://api.example.com/data")
```

### 数据验证

```python
from src.utils.data_validator import DataValidator

validator = DataValidator()

# 验证数据
data = {
    "email": "user@example.com",
    "age": 25,
    "name": "John Doe"
}

is_valid, errors = validator.validate(data, schema={
    "email": "email",
    "age": "integer",
    "name": "string"
})

if not is_valid:
    print(f"验证失败: {errors}")
```

## 部署

### Docker部署

```bash
# 构建镜像
docker build -t football-prediction:latest .

# 运行容器
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql://user:pass@db:5432/football" \
  -e REDIS_URL="redis://redis:6379/0" \
  football-prediction:latest

# 使用docker-compose
docker-compose up -d
```

### Kubernetes部署

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: football-prediction
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
      - name: api
        image: football-prediction:latest
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: db-secret
              key: url
```

## 常见问题

### 连接数据库失败

```python
# 检查连接
from src.database.connection import get_database_manager

db = get_database_manager()
try:
    db.test_connection()
    print("数据库连接成功")
except Exception as e:
    print(f"连接失败: {e}")
```

### 缓存失效

```python
# 清除所有缓存
from src.cache.redis_manager import RedisManager

redis = RedisManager()
await redis.flushall()
```

### 性能优化

```python
# 使用批量操作
# ❌ 不好 - 多次查询
for match_id in match_ids:
    match = await db.get_match(match_id)

# ✅ 好 - 批量查询
matches = await db.get_matches(match_ids)
```

## 更多资源

- [API文档](./API_DOCUMENTATION.md)
- [测试指南](./TESTING_GUIDE.md)
- [架构设计](./ARCHITECTURE.md)
- [贡献指南](../CONTRIBUTING.md)
