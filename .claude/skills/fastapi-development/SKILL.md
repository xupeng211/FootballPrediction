---
name: fastapi-development
description: Build high-performance async APIs using FastAPI for football prediction system. Use when creating REST endpoints, optimizing API performance, implementing authentication, or handling async database operations.
---

# FastAPI Development Skill

## 技能概述
专业的FastAPI开发技能模块，专注于高性能异步API设计、优化和最佳实践。

## 核心能力
- **异步编程**: FastAPI异步最佳实践、性能优化
- **API设计**: RESTful API设计、版本控制、文档生成
- **性能优化**: 响应时间优化、并发处理、内存管理
- **中间件开发**: 自定义中间件、CORS、认证授权
- **错误处理**: 统一错误处理、异常管理、日志记录
- **测试策略**: 单元测试、集成测试、性能测试

## 当前应用场景：足球预测API优化
- **目标**: 优化预测API响应时间至 <100ms
- **框架**: FastAPI + async/await
- **当前端点**: `/api/predict`, `/health`, `/monitoring`
- **数据库**: PostgreSQL (async)
- **缓存**: Redis (异步)

## 工具和库
- **FastAPI**: 高性能异步Web框架
- **uvicorn**: ASGI服务器
- **pydantic**: 数据验证和序列化
- **asyncio**: 异步编程支持
- **SQLAlchemy**: 异步ORM
- **Redis**: 异步缓存客户端
- **httpx**: 异步HTTP客户端
- **prometheus_client**: 指标收集

## 快速开始（第一层）
```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import asyncio

app = FastAPI(title="Football Prediction API", version="2.0.0")

# 基础中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": "2024-01-01T00:00:00Z"}
```

## 深入优化（第二层）
```python
from fastapi import FastAPI, Depends, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
import time

app = FastAPI()

# 异步依赖注入
async def get_db_session():
    """异步数据库连接"""
    async with async_session() as session:
        yield session

# 带缓存的预测端点
@app.get("/api/predict/{match_id}")
async def predict_match(
    match_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_session)
):
    """比赛预测端点 - 异步优化版本"""

    # 并行获取数据和模型
    match_data, model = await asyncio.gather(
        get_match_data(db, match_id),
        load_model_async()
    )

    # 后台任务：记录预测日志
    background_tasks.add_task(log_prediction, match_id, "pending")

    # 运行预测
    prediction = await run_in_threadpool(
        predict_single_match, match_data, model
    )

    # 更新缓存
    await cache_prediction(match_id, prediction)

    return {"prediction": prediction, "cached": False}
```

## 高级应用（第三层）
```python
from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware
import time
import uuid

class PerformanceMiddleware(BaseHTTPMiddleware):
    """性能监控中间件"""

    async def dispatch(self, request: Request, call_next):
        # 生成请求ID
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id

        # 记录开始时间
        start_time = time.time()

        # 处理请求
        response = await call_next(request)

        # 计算响应时间
        process_time = time.time() - start_time

        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        # 记录指标
        await record_metrics(
            endpoint=request.url.path,
            method=request.method,
            status_code=response.status_code,
            duration=process_time
        )

        return response

app.add_middleware(PerformanceMiddleware)
```

## 异步数据库操作

### 连接池配置
```python
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

# 异步数据库引擎
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,          # 连接池大小
    max_overflow=30,       # 最大溢出连接
    pool_pre_ping=True,    # 连接前检查
    pool_recycle=3600,     # 连接回收时间
    echo=False             # 生产环境关闭SQL日志
)

# 会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)
```

### 异步查询优化
```python
from sqlalchemy import select
from sqlalchemy.orm import selectinload

async def get_match_with_teams(match_id: int):
    """异步获取比赛及其球队信息"""
    async with AsyncSessionLocal() as session:
        # 使用selectinload优化关联查询
        stmt = select(Match).options(
            selectinload(Match.home_team),
            selectinload(Match.away_team)
        ).where(Match.id == match_id)

        result = await session.execute(stmt)
        return result.scalar_one_or_none()
```

## 缓存策略

### Redis异步缓存
```python
import aioredis
import json
from typing import Optional, Any

class AsyncCacheManager:
    """异步缓存管理器"""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None

    async def connect(self):
        """连接到Redis"""
        self.redis = aioredis.from_url(
            "redis://localhost:6379",
            encoding="utf-8",
            decode_responses=True
        )

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存"""
        if not self.redis:
            await self.connect()

        value = await self.redis.get(key)
        if value:
            return json.loads(value)
        return None

    async def set(
        self,
        key: str,
        value: Any,
        expire: int = 3600
    ):
        """设置缓存"""
        if not self.redis:
            await self.connect()

        await self.redis.setex(
            key,
            expire,
            json.dumps(value, default=str)
        )

cache_manager = AsyncCacheManager()
```

## 性能优化策略

### 1. 并发控制
```python
import asyncio
from asyncio import Semaphore

# 创建信号量控制并发
prediction_semaphore = Semaphore(100)  # 限制100个并发预测

async def predict_with_limit(match_data, model):
    """带并发限制的预测"""
    async with prediction_semaphore:
        return await run_in_threadpool(
            predict_single_match, match_data, model
        )
```

### 2. 批量处理
```python
from typing import List

@app.post("/api/predict/batch")
async def batch_predict(request: BatchPredictRequest):
    """批量预测 - 优化版本"""

    # 分批处理
    batch_size = 10
    results = []

    for i in range(0, len(request.matches), batch_size):
        batch = request.matches[i:i + batch_size]

        # 并发处理每个批次
        batch_results = await asyncio.gather(
            *[predict_match_async(match) for match in batch]
        )

        results.extend(batch_results)

    return {"predictions": results}
```

### 3. 流式响应
```python
from fastapi.responses import StreamingResponse
import json
import asyncio

@app.get("/api/predict/stream")
async def stream_predictions():
    """流式预测结果"""

    async def generate():
        matches = await get_upcoming_matches()

        for match in matches:
            # 异步预测
            prediction = await predict_match_async(match)

            # 生成JSON行
            yield json.dumps({
                "match_id": match.id,
                "prediction": prediction
            }) + "\n"

            # 避免阻塞
            await asyncio.sleep(0.01)

    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson"
    )
```

## 错误处理和日志

### 统一异常处理
```python
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """HTTP异常处理"""
    logger.error(
        f"HTTP {exc.status_code}: {exc.detail}",
        extra={
            "request_id": getattr(request.state, "request_id", None),
            "path": str(request.url.path)
        }
    )

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """通用异常处理"""
    logger.error(
        f"Unhandled exception: {str(exc)}",
        exc_info=True,
        extra={"request_id": getattr(request.state, "request_id", None)}
    )

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "request_id": getattr(request.state, "request_id", None)
        }
    )
```

## API文档和验证

### Pydantic模型
```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class PredictionRequest(BaseModel):
    """预测请求模型"""
    home_team: str = Field(..., min_length=1, max_length=100)
    away_team: str = Field(..., min_length=1, max_length=100)
    match_date: Optional[datetime] = None

    @validator('match_date')
    def validate_date(cls, v):
        if v and v < datetime.now():
            raise ValueError('Match date cannot be in the past')
        return v

class PredictionResponse(BaseModel):
    """预测响应模型"""
    match_id: Optional[int]
    home_team: str
    away_team: str
    prediction: str  # HOME, DRAW, AWAY
    confidence: float = Field(..., ge=0, le=1)
    probabilities: dict
    timestamp: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
```

## 监控和指标

### Prometheus指标
```python
from prometheus_client import Counter, Histogram, Gauge
import time

# 定义指标
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
    'Active database connections'
)

async def record_metrics(endpoint, method, status_code, duration):
    """记录指标"""
    REQUEST_COUNT.labels(
        method=method,
        endpoint=endpoint,
        status_code=status_code
    ).inc()

    REQUEST_DURATION.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)
```

## 测试策略

### 异步测试
```python
import pytest
from httpx import AsyncClient
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_prediction_endpoint():
    """测试预测端点"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/predict",
            json={
                "home_team": "Manchester United",
                "away_team": "Arsenal"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "prediction" in data
        assert "confidence" in data

@pytest.mark.asyncio
async def test_concurrent_predictions():
    """测试并发预测"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # 创建10个并发请求
        tasks = [
            client.post("/api/predict", json=test_data)
            for _ in range(10)
        ]

        responses = await asyncio.gather(*tasks)

        # 验证所有响应
        for response in responses:
            assert response.status_code == 200
```

## 部署配置

### 生产环境配置
```python
# uvicorn配置
uvicorn_config = {
    "app": "src.main:app",
    "host": "0.0.0.0",
    "port": 8000,
    "workers": 4,  # CPU核心数
    "worker_class": "uvicorn.workers.UvicornWorker",
    "max_requests": 1000,
    "max_requests_jitter": 100,
    "preload_app": True,
    "timeout": 30,
    "keep_alive": 2
}
```

## 性能基准

### 目标性能指标
- **响应时间**: < 100ms (P95)
- **并发处理**: > 1000 req/s
- **内存使用**: < 512MB
- **CPU使用**: < 70%
- **错误率**: < 0.1%

### 性能测试
```bash
# 使用k6进行负载测试
k6 run --vus 100 --duration 30s load_test.js

# 使用locust进行分布式测试
locust -f load_test.py --host=http://localhost:8000
```

## 最佳实践

1. **使用异步代码**: 所有I/O操作使用async/await
2. **连接池优化**: 合理配置数据库和Redis连接池
3. **缓存策略**: 实现多层缓存（内存、Redis、CDN）
4. **错误处理**: 完整的异常处理和日志记录
5. **监控告警**: 关键指标监控和报警
6. **版本控制**: API版本管理和向后兼容
7. **安全防护**: 认证授权、限流、CORS配置

## Related Skills
- `api-testing`: API testing (FastAPI endpoints)
- `code-quality`: Code quality management
- `deployment-management`: Deployment management
- `data-engineering`: Data pipeline engineering

---
*Last updated: 2025-12-28*
*Target: 足球预测API性能优化*