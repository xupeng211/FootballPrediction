# 🚀 Football Prediction System - 开发者指南

## 📖 目录

- [系统概述](#系统概述)
- [技术架构](#技术架构)
- [开发环境设置](#开发环境设置)
- [API开发指南](#api开发指南)
- [SDK使用指南](#sdk使用指南)
- [数据库设计](#数据库设计)
- [缓存策略](#缓存策略)
- [测试体系](#测试体系)
- [部署指南](#部署指南)
- [性能优化](#性能优化)
- [故障排除](#故障排除)
- [贡献指南](#贡献指南)

---

## 🎯 系统概述

### 系统简介
Football Prediction System是一个企业级的足球比赛结果预测系统，采用现代化的微服务架构和机器学习技术，为用户提供准确、可靠的比赛预测服务。

### 核心功能
- **比赛预测**: 基于历史数据和机器学习算法的比赛结果预测
- **实时数据**: 支持实时比赛数据更新和推送
- **用户管理**: 完整的用户认证和权限管理系统
- **数据分析**: 丰富的数据可视化和分析工具
- **API服务**: RESTful API和WebSocket实时通信

### 技术特色
- **异步架构**: 基于FastAPI的高性能异步Web框架
- **机器学习**: 集成多种预测算法和模型
- **缓存优化**: Redis多层缓存策略
- **容器化**: Docker容器化部署
- **监控体系**: 全面的性能监控和日志管理

---

## 🏗️ 技术架构

### 架构概览
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   前端应用      │    │   API网关       │    │   微服务集群    │
│                 │◄──►│                 │◄──►│                 │
│ - React/Vue     │    │ - Kong/Nginx    │    │ - 预测服务      │
│ - 移动端        │    │ - 负载均衡      │    │ - 数据服务      │
│ - 管理后台      │    │ - API限流       │    │ - 用户服务      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────┐            │
                       │   数据存储      │◄───────────┤
                       │                 │            │
                       │ - PostgreSQL    │            │
                       │ - Redis         │            │
                       │ - InfluxDB      │            │
                       │ - 文件存储      │            │
                       └─────────────────┘            │
                                                       │
                       ┌─────────────────┐            │
                       │   外部服务      │◄───────────┤
                       │                 │            │
                       │ - 足球数据API   │            │
                       │ - 天气服务      │            │
                       │ - 消息队列      │            │
                       └─────────────────┘
```

### 核心技术栈

#### 后端技术
- **Web框架**: FastAPI 0.104+
- **数据库**: PostgreSQL 15+ (主数据库)
- **缓存**: Redis 7+ (缓存和会话)
- **时序数据库**: InfluxDB 2+ (性能指标)
- **消息队列**: Apache Kafka (事件流)
- **搜索引擎**: Elasticsearch (日志搜索)

#### 开发工具
- **语言**: Python 3.11+
- **异步框架**: asyncio, uvloop
- **ORM**: SQLAlchemy 2.0+ (异步)
- **验证**: Pydantic 2.0+
- **测试**: pytest + pytest-asyncio
- **代码质量**: ruff, mypy, black

#### 部署技术
- **容器化**: Docker + Docker Compose
- **编排**: Kubernetes (生产环境)
- **CI/CD**: GitHub Actions
- **监控**: Prometheus + Grafana
- **日志**: ELK Stack
- **安全**: OAuth2 + JWT

---

## 🛠️ 开发环境设置

### 环境要求
- Python 3.11+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Git

### 快速启动

#### 1. 克隆项目
```bash
git clone https://github.com/your-org/football-prediction.git
cd football-prediction
```

#### 2. 环境配置
```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows

# 安装依赖
make install

# 环境检查
make env-check
```

#### 3. 数据库设置
```bash
# 启动数据库服务
docker-compose up -d postgres redis

# 运行数据库迁移
make db-migrate

# 创建初始数据
make db-seed
```

#### 4. 启动开发服务器
```bash
# 启动API服务器
make dev

# 或使用uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 5. 验证安装
```bash
# 运行测试
make test.unit

# 检查API健康状态
curl http://localhost:8000/health
```

### 开发工具配置

#### VS Code配置
```json
{
  "python.defaultInterpreterPath": "./venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

#### Pre-commit配置
```bash
# 安装pre-commit
pre-commit install

# 手动运行
pre-commit run --all-files
```

---

## 🔌 API开发指南

### API设计原则

#### RESTful设计
- 使用标准HTTP方法 (GET, POST, PUT, DELETE)
- 资源导向的URL设计
- 统一的响应格式
- 适当的HTTP状态码

#### 版本控制
```python
# API版本通过URL路径控制
/v1/predictions
/v2/predictions

# 或通过Header
Accept: application/vnd.api+json;version=1
```

### API端点开发

#### 1. 创建路由模块
```python
# src/api/predictions.py
from fastapi import APIRouter, Depends, HTTPException
from src.schemas.prediction import PredictionRequest, PredictionResponse
from src.services.prediction_service import PredictionService

router = APIRouter(prefix="/predictions", tags=["predictions"])

@router.post("/", response_model=PredictionResponse)
async def create_prediction(
    request: PredictionRequest,
    service: PredictionService = Depends(get_prediction_service)
):
    """创建新的比赛预测"""
    try:
        prediction = await service.create_prediction(request)
        return prediction
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

#### 2. 数据模型定义
```python
# src/schemas/prediction.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, Dict, Any

class PredictionRequest(BaseModel):
    match_id: str = Field(..., description="比赛ID")
    home_team: str = Field(..., description="主队名称")
    away_team: str = Field(..., description="客队名称")
    match_date: datetime = Field(..., description="比赛时间")
    features: Optional[Dict[str, Any]] = Field(None, description="特征数据")

    class Config:
        schema_extra = {
            "example": {
                "match_id": "match_123",
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "match_date": "2025-11-15T20:00:00Z",
                "features": {
                    "team_form": {"home_last_5": [3, 1, 0, 3, 1]}
                }
            }
        }
```

#### 3. 业务服务层
```python
# src/services/prediction_service.py
from src.domain.models.prediction import Prediction
from src.repositories.prediction_repository import PredictionRepository
from src.ml.models.prediction_model import PredictionModel

class PredictionService:
    def __init__(
        self,
        repository: PredictionRepository,
        model: PredictionModel
    ):
        self.repository = repository
        self.model = model

    async def create_prediction(self, request: PredictionRequest) -> Prediction:
        """创建预测"""
        # 数据验证
        await self._validate_request(request)

        # 生成预测
        prediction_data = await self.model.predict(request)

        # 保存结果
        prediction = await self.repository.create(prediction_data)

        return prediction
```

### API文档增强

#### OpenAPI配置
```python
# src/config/openapi.py
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Football Prediction API",
        version="1.0.0",
        description="企业级足球比赛预测API",
        routes=app.routes,
    )

    # 添加认证配置
    openapi_schema["components"]["securitySchemes"] = {
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }

    app.openapi_schema = openapi_schema
    return app.openapi_schema
```

---

## 🐍 SDK使用指南

### Python SDK安装

#### 1. 安装SDK
```bash
# 从PyPI安装
pip install football-prediction-sdk

# 或从源码安装
git clone https://github.com/your-org/football-prediction-sdk.git
cd football-prediction-sdk
pip install -e .
```

#### 2. 基本使用
```python
from football_prediction_sdk import FootballPredictionClient

# 创建客户端
client = FootballPredictionClient(
    api_key="your_api_key",
    base_url="https://api.football-prediction.com/v1"
)

# 创建预测
prediction = await client.predictions.create(
    match_id="match_123",
    home_team="Manchester United",
    away_team="Liverpool",
    match_date="2025-11-15T20:00:00Z"
)

print(f"预测结果: {prediction.winner}")
print(f"置信度: {prediction.confidence}")
```

### 高级功能

#### 1. 批量预测
```python
# 批量创建预测
predictions_data = [
    {
        "match_id": "match_1",
        "home_team": "Team A",
        "away_team": "Team B",
        "match_date": "2025-11-15T20:00:00Z"
    },
    {
        "match_id": "match_2",
        "home_team": "Team C",
        "away_team": "Team D",
        "match_date": "2025-11-16T19:00:00Z"
    }
]

predictions = await client.predictions.create_batch(predictions_data)
for prediction in predictions:
    print(f"比赛 {prediction.match_id}: {prediction.winner}")
```

#### 2. 实时数据订阅
```python
# WebSocket实时数据
async for update in client.matches.subscribe(match_id="match_123"):
    print(f"实时更新: {update}")
    if update.type == "goal":
        print(f"进球! {update.team}")
```

#### 3. 错误处理
```python
from football_prediction_sdk.exceptions import (
    AuthenticationError,
    ValidationError,
    RateLimitError
)

try:
    prediction = await client.predictions.create(data)
except AuthenticationError:
    print("认证失败，请检查API密钥")
except ValidationError as e:
    print(f"数据验证错误: {e}")
except RateLimitError as e:
    print(f"请求频率限制，{e.retry_after}秒后重试")
```

---

## 🗄️ 数据库设计

### 数据库架构

#### 核心表结构
```sql
-- 比赛表
CREATE TABLE matches (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_team_id UUID REFERENCES teams(id),
    away_team_id UUID REFERENCES teams(id),
    league_id UUID REFERENCES leagues(id),
    match_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled',
    home_score INTEGER,
    away_score INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 预测表
CREATE TABLE predictions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id UUID REFERENCES matches(id),
    user_id UUID REFERENCES users(id),
    model_version VARCHAR(20) NOT NULL,
    predicted_winner VARCHAR(100),
    confidence DECIMAL(5,4),
    home_win_prob DECIMAL(5,4),
    draw_prob DECIMAL(5,4),
    away_win_prob DECIMAL(5,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 用户表
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    subscription_plan VARCHAR(20) DEFAULT 'free',
    api_key VARCHAR(255) UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_login TIMESTAMP WITH TIME ZONE
);
```

#### 索引策略
```sql
-- 性能优化索引
CREATE INDEX idx_matches_date ON matches(match_date);
CREATE INDEX idx_matches_status ON matches(status);
CREATE INDEX idx_predictions_match ON predictions(match_id);
CREATE INDEX idx_predictions_user ON predictions(user_id);
CREATE INDEX idx_users_email ON users(email);

-- 复合索引
CREATE INDEX idx_matches_league_date ON matches(league_id, match_date);
CREATE INDEX idx_predictions_user_date ON predictions(user_id, created_at);
```

### 数据访问层

#### Repository模式
```python
# src/repositories/match_repository.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from src.database.models.match import Match
from src.schemas.match import MatchCreate, MatchUpdate

class MatchRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, match_data: MatchCreate) -> Match:
        """创建比赛记录"""
        match = Match(**match_data.dict())
        self.db.add(match)
        await self.db.commit()
        await self.db.refresh(match)
        return match

    async def get_by_id(self, match_id: str) -> Optional[Match]:
        """根据ID获取比赛"""
        result = await self.db.execute(
            select(Match).where(Match.id == match_id)
        )
        return result.scalar_one_or_none()

    async def get_upcoming_matches(
        self,
        limit: int = 100
    ) -> List[Match]:
        """获取即将进行的比赛"""
        result = await self.db.execute(
            select(Match)
            .where(Match.status == 'scheduled')
            .order_by(Match.match_date)
            .limit(limit)
        )
        return result.scalars().all()
```

---

## 💾 缓存策略

### Redis缓存架构

#### 多层缓存设计
```python
# src/cache/cache_manager.py
import redis.asyncio as redis
import json
from typing import Optional, Any
from src.config.settings import settings

class CacheManager:
    def __init__(self):
        self.redis = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        data = await self.redis.get(key)
        return json.loads(data) if data else None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600
    ) -> None:
        """设置缓存"""
        await self.redis.setex(
            key,
            expire,
            json.dumps(value, default=str)
        )

    async def delete(self, key: str) -> None:
        """删除缓存"""
        await self.redis.delete(key)

    async def invalidate_pattern(self, pattern: str) -> None:
        """批量删除缓存"""
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)
```

#### 缓存策略应用
```python
# src/services/prediction_service.py
from src.cache.cache_manager import CacheManager
from src.cache.decorators import cache_result

class PredictionService:
    def __init__(self, cache_manager: CacheManager):
        self.cache = cache_manager

    @cache_result(expire=1800)  # 30分钟缓存
    async def get_prediction(self, match_id: str) -> Optional[Prediction]:
        """获取预测结果（带缓存）"""
        cache_key = f"prediction:{match_id}"

        # 尝试从缓存获取
        cached = await self.cache.get(cache_key)
        if cached:
            return Prediction(**cached)

        # 从数据库获取
        prediction = await self.repository.get_by_match_id(match_id)
        if prediction:
            await self.cache.set(cache_key, prediction.dict())

        return prediction

    async def invalidate_prediction_cache(self, match_id: str) -> None:
        """清除预测缓存"""
        await self.cache.delete(f"prediction:{match_id}")
        await self.cache.invalidate_pattern(f"predictions:*")
```

---

## 🧪 测试体系

### 测试架构

#### 测试分层
```
tests/
├── unit/                 # 单元测试 (70%)
│   ├── domain/          # 领域层测试
│   ├── services/        # 服务层测试
│   ├── repositories/    # 数据访问层测试
│   └── utils/           # 工具函数测试
├── integration/          # 集成测试 (25%)
│   ├── api/             # API集成测试
│   ├── database/        # 数据库集成测试
│   └── external/        # 外部服务集成测试
└── e2e/                 # 端到端测试 (5%)
    ├── scenarios/       # 用户场景测试
    └── performance/     # 性能测试
```

#### 单元测试示例
```python
# tests/unit/services/test_prediction_service.py
import pytest
from unittest.mock import AsyncMock, Mock
from src.services.prediction_service import PredictionService
from src.schemas.prediction import PredictionRequest

@pytest.mark.asyncio
async def test_create_prediction_success():
    """测试成功创建预测"""
    # Arrange
    mock_repository = AsyncMock()
    mock_model = AsyncMock()
    service = PredictionService(mock_repository, mock_model)

    request = PredictionRequest(
        match_id="match_123",
        home_team="Team A",
        away_team="Team B",
        match_date="2025-11-15T20:00:00Z"
    )

    expected_prediction = Mock()
    mock_model.predict.return_value = expected_prediction
    mock_repository.create.return_value = expected_prediction

    # Act
    result = await service.create_prediction(request)

    # Assert
    assert result == expected_prediction
    mock_model.predict.assert_called_once_with(request)
    mock_repository.create.assert_called_once_with(expected_prediction)
```

#### 集成测试示例
```python
# tests/integration/api/test_predictions.py
import pytest
from httpx import AsyncClient
from src.main import app

@pytest.mark.asyncio
async def test_create_prediction_api():
    """测试创建预测API端点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/v1/predictions",
            json={
                "match_id": "match_123",
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "match_date": "2025-11-15T20:00:00Z"
            },
            headers={"Authorization": "Bearer test_token"}
        )

    assert response.status_code == 201
    data = response.json()
    assert data["match_id"] == "match_123"
    assert "prediction_id" in data
```

### 测试配置

#### pytest配置
```ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --cov=src
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    -v
markers =
    unit: 单元测试
    integration: 集成测试
    e2e: 端到端测试
    slow: 慢速测试
    api: API相关测试
    database: 数据库相关测试
```

#### 测试数据库配置
```python
# tests/conftest.py
import pytest
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from src.database.base import Base
from src.config.settings import test_settings

@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def test_engine():
    """创建测试数据库引擎"""
    engine = create_async_engine(
        test_settings.database_url,
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()

@pytest.fixture
async def test_session(test_engine):
    """创建测试数据库会话"""
    async_session = sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session
```

---

## 🚀 部署指南

### Docker部署

#### 开发环境
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile.dev
    ports:
      - "8000:8000"
    volumes:
      - .:/app
      - /app/venv
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/football_pred
      - REDIS_URL=redis://redis:6379
    depends_on:
      - postgres
      - redis
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: football_pred
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

#### 生产环境
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - SECRET_KEY=${SECRET_KEY}
    depends_on:
      - postgres
      - redis
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/ssl
    depends_on:
      - app
    restart: unless-stopped

  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes部署

#### 应用部署
```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: football-prediction-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: football-prediction-api
  template:
    metadata:
      labels:
        app: football-prediction-api
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
              name: app-secrets
              key: database-url
        - name: REDIS_URL
          valueFrom:
            secretKeyRef:
              name: app-secrets
              key: redis-url
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
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

---

## ⚡ 性能优化

### 数据库优化

#### 查询优化
```python
# 使用查询优化
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

# 预加载关联数据
result = await session.execute(
    select(Match)
    .options(selectinload(Match.home_team))
    .options(selectinload(Match.away_team))
    .where(Match.status == 'scheduled')
)

# 批量操作
from sqlalchemy import insert

predictions_data = [
    {"match_id": "1", "user_id": "1", "predicted_winner": "home"},
    {"match_id": "2", "user_id": "1", "predicted_winner": "away"},
]

stmt = insert(Prediction).returning(Prediction)
result = await session.execute(stmt, predictions_data)
```

#### 连接池配置
```python
# src/config/database.py
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import QueuePool

engine = create_async_engine(
    settings.database_url,
    poolclass=QueuePool,
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug
)
```

### 应用优化

#### 异步优化
```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

class PredictionService:
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def batch_predict(self, requests: List[PredictionRequest]) -> List[Prediction]:
        """批量预测处理"""
        # 使用异步并发处理
        tasks = [
            self._predict_single(request)
            for request in requests
        ]
        return await asyncio.gather(*tasks)

    async def _predict_single(self, request: PredictionRequest) -> Prediction:
        """单个预测处理（CPU密集型任务）"""
        # CPU密集型任务使用线程池
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._cpu_predict,
            request
        )
```

#### 缓存优化
```python
from functools import lru_cache
import asyncio

class CacheOptimizedService:
    @lru_cache(maxsize=1000)
    def _get_static_data(self, key: str):
        """缓存静态数据"""
        return self._load_static_data(key)

    async def get_cached_data(self, key: str):
        """异步获取缓存数据"""
        # 在线程池中执行缓存操作
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._get_static_data,
            key
        )
```

---

## 🔧 故障排除

### 常见问题

#### 1. 数据库连接问题
```python
# 检查数据库连接
async def check_database_health():
    try:
        result = await session.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"数据库连接失败: {e}")
        return False

# 连接重试机制
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def get_database_connection():
    return await create_async_engine(settings.database_url)
```

#### 2. 缓存问题
```python
# 缓存降级策略
async def get_data_with_fallback(key: str):
    try:
        # 尝试从缓存获取
        cached = await cache.get(key)
        if cached:
            return cached
    except Exception as e:
        logger.warning(f"缓存获取失败: {e}")

    # 从数据库获取
    data = await database.get_data(key)

    try:
        # 尝试写入缓存
        await cache.set(key, data)
    except Exception as e:
        logger.warning(f"缓存写入失败: {e}")

    return data
```

#### 3. API限流处理
```python
# 限流重试机制
from tenacity import retry, retry_if_exception_type
from src.exceptions import RateLimitError

@retry(
    retry=retry_if_exception_type(RateLimitError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=4, max=10)
)
async def call_api_with_retry(client, endpoint, data):
    try:
        return await client.post(endpoint, json=data)
    except RateLimitError as e:
        logger.warning(f"API限流，{e.retry_after}秒后重试")
        raise
```

### 监控和日志

#### 结构化日志
```python
import structlog

logger = structlog.get_logger()

async def create_prediction(request: PredictionRequest):
    logger.info(
        "开始创建预测",
        match_id=request.match_id,
        home_team=request.home_team,
        away_team=request.away_team
    )

    try:
        prediction = await service.create_prediction(request)
        logger.info(
            "预测创建成功",
            prediction_id=prediction.id,
            confidence=prediction.confidence
        )
        return prediction
    except Exception as e:
        logger.error(
            "预测创建失败",
            match_id=request.match_id,
            error=str(e),
            exc_info=True
        )
        raise
```

#### 性能监控
```python
import time
from functools import wraps

def monitor_performance(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = await func(*args, **kwargs)
            duration = time.time() - start_time

            logger.info(
                "函数执行完成",
                function=func.__name__,
                duration=duration,
                success=True
            )
            return result
        except Exception as e:
            duration = time.time() - start_time

            logger.error(
                "函数执行失败",
                function=func.__name__,
                duration=duration,
                error=str(e)
            )
            raise
    return wrapper
```

---

## 🤝 贡献指南

### 开发流程

#### 1. 创建功能分支
```bash
git checkout -b feature/new-prediction-model
```

#### 2. 开发和测试
```bash
# 运行测试
make test.unit
make test.integration

# 代码质量检查
make lint
make fmt
make type-check
```

#### 3. 提交代码
```bash
git add .
git commit -m "feat: 添加新的预测模型

- 实现基于LSTM的时序预测
- 添加模型评估指标
- 更新单元测试

Closes #123"
```

#### 4. 推送和创建PR
```bash
git push origin feature/new-prediction-model
# 在GitHub上创建Pull Request
```

### 代码规范

#### Python代码风格
```python
# 使用类型注解
def process_prediction_data(
    data: Dict[str, Any],
    config: ProcessingConfig
) -> ProcessedResult:
    """处理预测数据"""
    pass

# 使用异步/await
async def fetch_match_data(match_id: str) -> MatchData:
    """获取比赛数据"""
    pass

# 错误处理
try:
    result = await process_data(data)
except ValidationError as e:
    logger.error(f"数据验证失败: {e}")
    raise
```

#### 提交信息规范
```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

类型：
- `feat`: 新功能
- `fix`: 修复bug
- `docs`: 文档更新
- `style`: 代码格式
- `refactor`: 重构
- `test`: 测试
- `chore`: 构建工具、依赖更新

### 测试要求

#### 测试覆盖率
- 单元测试覆盖率 > 80%
- 集成测试覆盖率 > 60%
- 关键路径覆盖率 100%

#### 测试编写
```python
# AAA模式：Arrange, Act, Assert
@pytest.mark.asyncio
async def test_prediction_service_create():
    # Arrange - 准备测试数据
    mock_repository = AsyncMock()
    service = PredictionService(mock_repository)
    request = PredictionRequest(...)

    # Act - 执行测试
    result = await service.create_prediction(request)

    # Assert - 验证结果
    assert result is not None
    mock_repository.create.assert_called_once()
```

---

## 📞 支持和联系

### 技术支持
- 📧 Email: support@football-prediction.com
- 💬 Discord: [链接]
- 📖 文档: https://docs.football-prediction.com
- 🐛 问题反馈: GitHub Issues

### 社区
- 🎯 官方网站: https://football-prediction.com
- 📱 Twitter: @FootballPredAI
- 💡 功能建议: GitHub Discussions

---

**文档版本**: v1.0.0
**最后更新**: 2025-11-10
**维护团队**: Football Prediction System Team
