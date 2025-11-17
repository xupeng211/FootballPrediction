# CLAUDE_DETAILED.md

**详细参考文档** - 包含完整的代码示例、配置参数和故障排除指南

> 📖 **快速导航**: 如需核心概念和快速入门，请查看 [CLAUDE.md](./CLAUDE.md)

---

## 📑 目录

- [🔧 代码示例](#-代码示例)
- [⚙️ 配置文件详解](#️-配置文件详解)
- [🚀 性能优化](#-性能优化)
- [🔧 质量修复](#-质量修复)
- [🚨 故障排除](#-故障排除)
- [🔍 高级测试策略](#-高级测试策略)
- [🐳 Docker和部署](#-docker和部署)
- [📊 监控和指标](#-监控和指标)

---

## 🔧 代码示例

### 策略工厂模式

**位置**: `src/domain/strategies/factory.py:35`

```python
from src.domain.strategies.factory import PredictionStrategyFactory
from src.domain.strategies.base import StrategyType
from src.domain.services.prediction_service import PredictionService

async def main():
    # 创建策略工厂（支持配置文件）
    factory = PredictionStrategyFactory(config_path="config/strategies.yaml")

    # 动态选择策略类型
    strategies = [
        ("ml_model", "enhanced_ml_model"),
        ("statistical", "poisson_distribution"),
        ("historical", "head_to_head"),
        ("ensemble", "weighted_voting")
    ]

    for strategy_type, strategy_name in strategies:
        strategy = await factory.create_strategy(strategy_type, strategy_name)
        service = PredictionService(strategy)

        # 执行预测
        prediction_data = {
            "match_id": 123,
            "home_team": "Team A",
            "away_team": "Team B",
            "league": "Premier League",
            "season": "2024-25"
        }
        prediction = await service.create_prediction(prediction_data)
        print(f"Strategy {strategy_name}: {prediction.confidence:.2f}")
```

### 依赖注入容器

**位置**: `src/core/di.py:23`

```python
from src.core.di import DIContainer, ServiceCollection, ServiceLifetime
from src.database.manager import DatabaseManager
from src.database.unit_of_work import UnitOfWork
from src.domain.services.prediction_service import PredictionService
from src.cache.redis_client import RedisClient

# 配置服务容器（三种生命周期）
container = ServiceCollection()

# 单例模式 - 全局唯一实例
container.add_singleton(DatabaseManager)
container.add_singleton(RedisClient)

# 作用域模式 - 每个请求作用域内唯一
container.add_scoped(UnitOfWork)

# 瞬时模式 - 每次请求创建新实例
container.add_transient(PredictionService)

# 构建容器并解析服务
di_container = container.build_container()

# 在应用启动时解析服务
async def initialize_app():
    db_manager = di_container.resolve(DatabaseManager)
    await db_manager.initialize()

    redis_client = di_container.resolve(RedisClient)
    await redis_client.connect()

# 在API端点中使用
async def create_prediction(request: PredictionRequest):
    # 每次请求都会创建新的UnitOfWork和PredictionService
    unit_of_work = di_container.resolve(UnitOfWork)
    prediction_service = di_container.resolve(PredictionService)

    async with unit_of_work:
        return await prediction_service.create_prediction(request)
```

### CQRS模式

**位置**: `src/cqrs/bus.py:17`

```python
from src.cqrs.bus import CommandBus, QueryBus
from src.cqrs.commands import CreatePredictionCommand, UpdatePredictionCommand
from src.cqrs.queries import GetPredictionQuery, ListPredictionsQuery
from src.cqrs.handlers import (
    CreatePredictionHandler,
    UpdatePredictionHandler,
    GetPredictionHandler,
    ListPredictionsHandler
)

# 初始化总线并注册处理器
command_bus = CommandBus()
query_bus = QueryBus()

# 注册命令处理器（写操作）
command_bus.register_handler(CreatePredictionCommand, CreatePredictionHandler())
command_bus.register_handler(UpdatePredictionCommand, UpdatePredictionHandler())

# 注册查询处理器（读操作）
query_bus.register_handler(GetPredictionQuery, GetPredictionHandler())
query_bus.register_handler(ListPredictionsQuery, ListPredictionsHandler())

# 使用示例：创建预测（命令）
async def create_new_prediction(match_data: dict):
    create_cmd = CreatePredictionCommand(
        match_id=match_data["match_id"],
        home_team=match_data["home_team"],
        away_team=match_data["away_team"],
        predicted_home_score=match_data["predicted_home_score"],
        predicted_away_score=match_data["predicted_away_score"],
        confidence=match_data["confidence"],
        strategy_used=match_data["strategy"]
    )

    # 命令执行，返回预测ID
    result = await command_bus.dispatch(create_cmd)
    return result.prediction_id

# 使用示例：查询预测（查询）
async def get_prediction_details(prediction_id: int):
    query = GetPredictionQuery(prediction_id=prediction_id)
    prediction = await query_bus.dispatch(query)
    return prediction

# 批量查询示例
async def get_user_predictions(user_id: int, limit: int = 10):
    query = ListPredictionsQuery(user_id=user_id, limit=limit)
    predictions = await query_bus.dispatch(query)
    return predictions

# 中间件支持（日志、缓存、验证）
command_bus.register_middleware(LoggingMiddleware())
command_bus.register_middleware(ValidationMiddleware())
query_bus.register_middleware(CachingMiddleware(ttl=300))
```

---

## ⚙️ 配置文件详解

### pyproject.toml

```toml
[build-system]
requires = ["setuptools>=45", "wheel", "setuptools_scm[toml]>=6.2"]
build-backend = "setuptools.build_meta"

[project]
name = "football-prediction"
version = "1.0.0"
description = "企业级足球预测系统"
readme = "README.md"
license = {text = "MIT"}
authors = [
    {name = "Football Prediction Team", email = "team@footballprediction.com"}
]
classifiers = [
    "Development Status :: 4 - Beta",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pydantic>=2.5.0",
    "redis>=5.0.0",
    "psycopg2-binary>=2.9.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-dotenv>=1.0.0",
    "httpx>=0.25.0",
    "pandas>=2.1.0",
    "numpy>=1.25.0",
    "scikit-learn>=1.3.0",
]

[project.optional-dependencies]
dev = [
    # 测试工具
    "pytest>=8.4.2",
    "pytest-asyncio>=1.2.0",
    "pytest-cov>=7.0.0",
    "pytest-mock>=3.14.0",
    "pytest-xdist>=3.6.1",
    "factory-boy>=3.3.1",

    # 代码质量和格式化
    "ruff>=0.14.3",
    "mypy>=1.18.2",
    "bandit>=1.8.6",

    # 开发工具
    "pre-commit>=4.0.1",
    "pip-audit>=2.6.0",
    "pip-tools>=7.4.1",
    "ipython>=8.31.0",

    # 文档工具
    "mkdocs>=1.6.1",
    "mkdocs-material>=9.5.49",
]

[tool.setuptools.packages.find]
where = ["src"]

[tool.ruff]
line-length = 88
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "N", "UP", "B", "A", "C4", "T20", "D"]
ignore = ["E501", "B008"]

[tool.ruff.lint.pydocstyle]
# 使用 Google 风格的 docstrings
convention = "google"
exclude = [
    ".bzr", ".direnv", ".eggs", ".git", ".hg", ".mypy_cache",
    ".nox", ".pants.d", ".ruff_cache", ".svn", ".tox", ".venv",
    "__pypackages__", "_build", "buck-out", "dist", "node_modules", "venv",
]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
skip-magic-trailing-comma = false
line-ending = "auto"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
strict_optional = true
warn_no_return = true
warn_redundant_casts = true
warn_unused_ignores = true
check_untyped_defs = true
exclude = [
    "tests/", "scripts/", "docs/", "htmlcov/",
]

[[tool.mypy.overrides]]
module = [
    "pandas.*", "numpy.*", "sklearn.*",
    "redis.*", "psycopg2.*"
]
ignore_missing_imports = true

[tool.bandit]
exclude_dirs = ["tests", "build", "dist"]
skips = ["B101", "B601"]  # 跳过assert_test和shell_injection检查

[tool.pytest.ini_options]
minversion = "7.0"
addopts = "-ra -q --strict-markers --strict-config"
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow running tests",
    "api: API related tests",
    "database: Database related tests",
    "auth: Authentication tests",
    "critical: Critical functionality tests",
    "smoke: Basic functionality verification",
    "regression: Regression tests",
    "performance: Performance tests",
    "metrics: Metrics and measurement tests",
    "edge_cases: Edge cases and boundary conditions",
    "asyncio: Async function tests",
    "external_api: Tests requiring external API calls",
    "docker: Tests requiring Docker environment",
    "network: Tests requiring network connection",
    "domain: Domain layer tests",
    "business: Business logic tests",
    "services: Service layer tests",
    "cache: Cache related tests",
    "monitoring: Monitoring related tests",
    "streaming: Streaming tests",
    "collectors: Data collector tests",
    "middleware: Middleware tests",
    "utils: Utility function tests",
    "core: Core module tests",
    "decorators: Decorator tests",
    "health: Health check tests",
    "validation: Validation tests",
    "ml: Machine learning tests",
    "issue94: Issue #94 API module fixes",
]

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/test_*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/.venv/*",
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
]
```

### pytest.ini

```ini
[pytest]
# Smart Tests优化配置
addopts = --cov=src --cov-fail-under=40 --cov-report=term-missing

# 测试路径配置
testpaths = tests

# Python文件匹配规则
python_files = test_*.py *_test.py
python_classes = Test*
python_functions = test_*

# 严格标记和配置模式
strict-markers = true
strict-config = true

# 40个标准化测试标记定义
markers =
    # 核心类型标记（4个）
    unit: Unit tests (85% of tests)
    integration: Integration tests (12% of tests)
    e2e: End-to-end tests (2% of tests)
    performance: Performance tests (1% of tests)

    # 功能域标记（18个）
    api: API tests - HTTP endpoints and interfaces
    domain: Domain layer tests - Business logic and algorithms
    business: Business rules tests - Business logic and rule engine
    services: Service layer tests - Business services and data processing
    database: Database tests - Requires database connection
    cache: Cache related tests - Redis and caching logic
    auth: Authentication related tests - JWT and permission validation
    monitoring: Monitoring related tests - Metrics and health checks
    streaming: Streaming tests - Kafka and real-time data
    collectors: Collector tests - Data collection and scraping modules
    middleware: Middleware tests - Request processing and pipeline components
    utils: Utility class tests - Common utilities and helper functions
    core: Core module tests - Configuration, dependency injection, infrastructure
    decorators: Decorator tests - Various decorator functions and performance tests
    health: Health check related tests
    validation: Validation and confirmation tests
    ml: Machine learning tests - ML model training, prediction and evaluation tests

    # 执行特征标记（9个）
    slow: Slow tests - Running time >30s
    smoke: Smoke tests - Basic functionality verification
    critical: Critical tests - Must-pass core functionality tests
    regression: Regression tests - Verify fixed issues don't reoccur
    metrics: Metrics and measurement tests - Performance metrics and progress verification
    edge_cases: Edge cases tests - Extreme values and exception handling
    asyncio: Async tests - Test async functions and coroutines

    # 环境依赖标记（3个）
    external_api: Requires external API calls
    docker: Requires Docker container environment
    network: Requires network connection

    # 问题特定标记（1个）
    issue94: Issue #94 API module systematic fixes

# Smart Tests具体配置
[tool:pytest_smart_tests]
# 核心稳定测试模块（执行时间<2分钟）
testpaths_smarts = tests/unit/utils tests/unit/cache tests/unit/core

# 排除的问题测试文件
ignore_files_smarts =
    tests/unit/services/test_prediction_service.py
    tests/unit/core/test_di.py
    tests/unit/core/test_path_manager_enhanced.py

# 性能优化配置
addopts_smarts = -v --tb=short --maxfail=20 -m "not slow"
```

---

## 🚀 性能优化

### 数据库优化

**位置**: `src/core/config/database.py`

```python
from sqlalchemy import create_async_engine
from sqlalchemy.pool import QueuePool
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# 高性能数据库连接配置
DATABASE_CONFIG = {
    "pool_size": 20,           # 连接池大小
    "max_overflow": 30,        # 最大溢出连接数
    "pool_timeout": 30,        # 获取连接超时时间（秒）
    "pool_recycle": 3600,      # 连接回收时间（秒）
    "pool_pre_ping": True,     # 连接前ping检查
    "echo": False,             # 生产环境关闭SQL日志
}

# 创建高性能引擎
engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=QueuePool,
    **DATABASE_CONFIG
)

# 批量操作优化
async def bulk_create_predictions(predictions: List[dict]):
    """批量创建预测，提升插入性能"""
    async with AsyncSession(engine) as session:
        try:
            # 使用批量插入而非单条插入
            await session.execute(
                insert(Prediction).values(predictions)
            )
            await session.commit()
        except Exception as e:
            await session.rollback()
            raise e

# 查询优化
async def get_predictions_with_pagination(
    page: int = 1,
    size: int = 20,
    filters: dict = None
):
    """分页查询优化"""
    query = select(Prediction)

    # 应用过滤器
    if filters:
        if filters.get("team"):
            query = query.where(
                or_(
                    Prediction.home_team == filters["team"],
                    Prediction.away_team == filters["team"]
                )
            )
        if filters.get("date_from"):
            query = query.where(
                Prediction.match_date >= filters["date_from"]
            )

    # 分页
    offset = (page - 1) * size
    query = query.offset(offset).limit(size)

    result = await session.execute(query)
    return result.scalars().all()
```

### Redis缓存优化

**位置**: `src/cache/redis_client.py`

```python
import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from typing import Optional, Any
import json
import pickle

# 高性能Redis连接池配置
REDIS_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "max_connections": 50,     # 最大连接数
    "retry_on_timeout": True,  # 超时重试
    "socket_timeout": 5,       # Socket超时
    "socket_connect_timeout": 5,
    "health_check_interval": 30,  # 健康检查间隔
    "decode_responses": False,  # 保持bytes以便pickle
}

# 创建连接池
pool = ConnectionPool(**REDIS_CONFIG)
redis_client = redis.Redis(connection_pool=pool)

class CacheManager:
    """智能缓存管理器"""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 默认1小时

    async def get_prediction(self, prediction_id: int) -> Optional[dict]:
        """获取预测缓存"""
        key = f"prediction:{prediction_id}"
        data = await self.redis.get(key)
        return pickle.loads(data) if data else None

    async def set_prediction(
        self,
        prediction_id: int,
        prediction_data: dict,
        ttl: int = None
    ):
        """设置预测缓存"""
        key = f"prediction:{prediction_id}"
        ttl = ttl or self.default_ttl
        await self.redis.setex(
            key,
            ttl,
            pickle.dumps(prediction_data)
        )

    async def invalidate_user_cache(self, user_id: int):
        """失效用户相关缓存"""
        pattern = f"user:{user_id}:*"
        keys = await self.redis.keys(pattern)
        if keys:
            await self.redis.delete(*keys)

    async def cache_team_stats(
        self,
        team_id: int,
        stats_data: dict,
        ttl: int = 7200  # 2小时
    ):
        """缓存球队统计数据"""
        key = f"team_stats:{team_id}"
        await self.redis.setex(
            key,
            ttl,
            json.dumps(stats_data)
        )

    async def get_team_stats(self, team_id: int) -> Optional[dict]:
        """获取球队统计缓存"""
        key = f"team_stats:{team_id}"
        data = await self.redis.get(key)
        return json.loads(data) if data else None

# 缓存装饰器优化
def smart_cache(key_template: str, ttl: int = 3600):
    """智能缓存装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = key_template.format(*args, **kwargs)

            # 尝试从缓存获取
            cached = await redis_client.get(cache_key)
            if cached:
                return pickle.loads(cached)

            # 执行函数并缓存结果
            result = await func(*args, **kwargs)
            await redis_client.setex(
                cache_key,
                ttl,
                pickle.dumps(result)
            )
            return result
        return wrapper
    return decorator

# 使用示例
@smart_cache("prediction_stats:{team_id}:{season}", ttl=7200)
async def get_team_prediction_stats(team_id: int, season: str):
    """获取球队预测统计（带缓存）"""
    # 复杂的计算逻辑
    pass
```

### API性能优化

**位置**: `src/api/endpoints/predictions.py`

```python
from fastapi import FastAPI, BackgroundTasks, HTTPException, Depends
from fastapi.concurrency import run_in_threadpool
import asyncio
from typing import List

# 异步批处理端点
@app.post("/predictions/batch")
async def create_batch_predictions(
    predictions: List[PredictionCreate],
    background_tasks: BackgroundTasks,
    prediction_service: PredictionService = Depends(get_prediction_service)
):
    """
    异步批量处理预测，避免阻塞

    - 批量大小：50
    - 后台处理：避免超时
    - 进度跟踪：返回任务ID
    """
    total_predictions = len(predictions)
    batch_size = 50

    # 生成任务ID
    task_id = str(uuid.uuid4())

    # 分批处理
    for i in range(0, total_predictions, batch_size):
        batch = predictions[i:i + batch_size]
        background_tasks.add_task(
            process_prediction_batch,
            task_id,
            i // batch_size + 1,
            batch,
            prediction_service
        )

    return {
        "message": "Batch processing started",
        "task_id": task_id,
        "total_predictions": total_predictions,
        "estimated_batches": (total_predictions + batch_size - 1) // batch_size
    }

async def process_prediction_batch(
    task_id: str,
    batch_number: int,
    predictions: List[PredictionCreate],
    prediction_service: PredictionService
):
    """后台批量处理任务"""
    try:
        results = []
        for pred_data in predictions:
            try:
                prediction = await prediction_service.create_prediction(pred_data)
                results.append({
                    "status": "success",
                    "prediction_id": prediction.id,
                    "match_id": pred_data.match_id
                })
            except Exception as e:
                results.append({
                    "status": "error",
                    "match_id": pred_data.match_id,
                    "error": str(e)
                })

        # 存储批次结果
        await store_batch_results(task_id, batch_number, results)

    except Exception as e:
        logger.error(f"Batch {batch_number} failed: {e}")
        await store_batch_error(task_id, batch_number, str(e))

# 并发优化的查询端点
@app.get("/predictions/search")
async def search_predictions(
    q: str = Query(..., description="搜索关键词"),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    prediction_service: PredictionService = Depends(get_prediction_service)
):
    """
    并发优化的搜索端点

    - 并发查询：同时搜索多个字段
    - 结果合并：去重和排序
    - 分页支持：offset/limit
    """
    # 并发搜索多个字段
    search_tasks = [
        prediction_service.search_by_team(q, limit),
        prediction_service.search_by_league(q, limit),
        prediction_service.search_by_date(q, limit)
    ]

    # 等待所有搜索完成
    search_results = await asyncio.gather(*search_tasks, return_exceptions=True)

    # 合并和去重结果
    all_predictions = []
    prediction_ids = set()

    for results in search_results:
        if not isinstance(results, Exception):
            for pred in results:
                if pred.id not in prediction_ids:
                    prediction_ids.add(pred.id)
                    all_predictions.append(pred)

    # 应用分页
    total = len(all_predictions)
    paginated_results = all_predictions[offset:offset + limit]

    return {
        "predictions": paginated_results,
        "total": total,
        "offset": offset,
        "limit": limit
    }

# 响应压缩中间件
from fastapi.middleware.gzip import GZipMiddleware

app.add_middleware(GZipMiddleware, minimum_size=1000)

# 缓存头优化
@app.get("/predictions/{prediction_id}")
async def get_prediction(
    prediction_id: int,
    prediction_service: PredictionService = Depends(get_prediction_service)
):
    prediction = await prediction_service.get_prediction(prediction_id)
    if not prediction:
        raise HTTPException(status_code=404, detail="Prediction not found")

    # 设置缓存头
    response = JSONResponse(content=prediction.dict())
    response.headers["Cache-Control"] = "public, max-age=300"  # 5分钟缓存
    response.headers["ETag"] = f'"{prediction.updated_at.isoformat()}"'

    return response
```

---

## 🔧 质量修复

### 自动化质量修复

```bash
#!/bin/bash
# scripts/quality_fix.sh

echo "🔧 开始自动化质量修复..."

# 1. Ruff自动修复
echo "📝 运行Ruff代码检查和修复..."
ruff check src/ tests/ --fix --unsafe-fixes
echo "✅ Ruff修复完成"

# 2. Ruff格式化
echo "🎨 运行Ruff格式化..."
ruff format src/ tests/
echo "✅ 格式化完成"

# 3. Import排序优化
echo "📦 优化import语句..."
ruff check src/ tests/ --select=I --fix
echo "✅ Import优化完成"

# 4. 移除未使用的导入
echo "🗑️ 移除未使用的导入..."
ruff check src/ --select=F401 --fix
echo "✅ 未使用导入清理完成"

# 5. 类型检查修复
echo "🔍 运行MyPy类型检查..."
mypy src/ --ignore-missing-imports --show-error-codes --no-error-summary
echo "✅ 类型检查完成"

# 6. 安全检查
echo "🛡️ 运行Bandit安全扫描..."
bandit -r src/ -f json -o bandit-report.json || echo "安全扫描完成，有警告"
echo "✅ 安全检查完成"

echo "🎉 自动化质量修复完成！"
echo "📊 生成的报告文件："
echo "   - bandit-report.json (安全扫描报告)"
```

### Python质量修复脚本

```python
#!/usr/bin/env python3
# scripts/advanced_quality_fixer.py

import subprocess
import sys
import os
from pathlib import Path

class AdvancedQualityFixer:
    """高级质量修复工具"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.src_dir = project_root / "src"
        self.tests_dir = project_root / "tests"

    def fix_ruff_issues(self, unsafe_fixes: bool = False):
        """使用Ruff修复代码质量问题"""
        print("🔧 使用Ruff修复代码问题...")

        cmd = ["ruff", "check", "src/", "tests/", "--fix"]
        if unsafe_fixes:
            cmd.append("--unsafe-fixes")

        result = subprocess.run(cmd, cwd=self.project_root)
        if result.returncode == 0:
            print("✅ Ruff修复成功")
        else:
            print("⚠️ Ruff修复过程中有警告")

    def format_code(self):
        """使用Ruff格式化代码"""
        print("🎨 使用Ruff格式化代码...")

        result = subprocess.run(
            ["ruff", "format", "src/", "tests/"],
            cwd=self.project_root
        )
        if result.returncode == 0:
            print("✅ 代码格式化成功")
        else:
            print("❌ 代码格式化失败")

    def fix_imports(self):
        """修复导入语句问题"""
        print("📦 修复导入语句...")

        # 排序导入
        subprocess.run(
            ["ruff", "check", "src/", "tests/", "--select=I", "--fix"],
            cwd=self.project_root
        )

        # 移除未使用的导入
        subprocess.run(
            ["ruff", "check", "src/", "--select=F401", "--fix"],
            cwd=self.project_root
        )

        print("✅ 导入语句修复完成")

    def fix_docstrings(self):
        """修复文档字符串问题"""
        print("📝 修复文档字符串...")

        # 查找需要修复docstring的文件
        python_files = list(self.src_dir.rglob("*.py"))

        for file_path in python_files:
            self._fix_file_docstrings(file_path)

        print("✅ 文档字符串修复完成")

    def _fix_file_docstrings(self, file_path: Path):
        """修复单个文件的docstring"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # 简单的docstring修复逻辑
            # 这里可以根据需要扩展更复杂的修复规则
            lines = content.split('\n')
            fixed_lines = []

            for i, line in enumerate(lines):
                # 修复常见的docstring格式问题
                if '"""' in line and not line.strip().endswith('"""'):
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        # 如果下一行有内容，可能需要添加换行
                        fixed_lines.append(line)
                        fixed_lines.append("")
                    else:
                        fixed_lines.append(line)
                else:
                    fixed_lines.append(line)

            # 写回文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(fixed_lines))

        except Exception as e:
            print(f"⚠️ 修复文件 {file_path} 时出错: {e}")

    def run_type_checks(self):
        """运行类型检查"""
        print("🔍 运行MyPy类型检查...")

        result = subprocess.run(
            [
                "mypy", "src/",
                "--ignore-missing-imports",
                "--show-error-codes",
                "--no-error-summary"
            ],
            cwd=self.project_root
        )

        if result.returncode == 0:
            print("✅ 类型检查通过")
        else:
            print("⚠️ 类型检查发现问题，请查看上述输出")

    def run_security_check(self):
        """运行安全检查"""
        print("🛡️ 运行Bandit安全检查...")

        result = subprocess.run(
            ["bandit", "-r", "src/", "-f", "json", "-o", "bandit-report.json"],
            cwd=self.project_root
        )

        print("✅ 安全检查完成，报告已保存到 bandit-report.json")

    def fix_syntax_errors(self):
        """修复语法错误"""
        print("🐛 检查并修复语法错误...")

        # 使用Python编译检查语法错误
        python_files = list(self.src_dir.rglob("*.py"))
        syntax_errors = []

        for file_path in python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                compile(content, str(file_path), 'exec')
            except SyntaxError as e:
                syntax_errors.append((file_path, e))
                print(f"❌ 语法错误在 {file_path}: {e}")

        if not syntax_errors:
            print("✅ 未发现语法错误")
        else:
            print(f"⚠️ 发现 {len(syntax_errors)} 个语法错误，需要手动修复")

    def run_complete_fix(self):
        """运行完整的质量修复流程"""
        print("🚀 开始完整质量修复流程...")

        try:
            self.fix_syntax_errors()
            self.fix_ruff_issues(unsafe_fixes=True)
            self.format_code()
            self.fix_imports()
            self.fix_docstrings()
            self.run_type_checks()
            self.run_security_check()

            print("🎉 完整质量修复流程完成！")

        except Exception as e:
            print(f"❌ 质量修复过程中出错: {e}")
            sys.exit(1)

if __name__ == "__main__":
    project_root = Path(__file__).parent.parent
    fixer = AdvancedQualityFixer(project_root)
    fixer.run_complete_fix()
```

### Makefile集成

```makefile
# 高级质量修复命令
quality-fix-advanced:
	@echo "🔧 运行高级质量修复..."
	@$(ACTIVATE) && python scripts/advanced_quality_fixer.py

# 智能代码修复
smart-fix:
	@echo "🤖 运行智能代码修复..."
	@$(ACTIVATE) && \
		echo "📝 Ruff修复..." && \
		ruff check src/ tests/ --fix --unsafe-fixes && \
		echo "🎨 格式化..." && \
		ruff format src/ tests/ && \
		echo "📦 Import优化..." && \
		ruff check src/ tests/ --select=I,F401 --fix && \
		echo "✅ 智能修复完成"

# 类型安全修复
type-fix:
	@echo "🔍 运行类型安全修复..."
	@$(ACTIVATE) && \
		mypy src/ --ignore-missing-imports --show-error-codes || true && \
		echo "✅ 类型检查完成"

# 安全漏洞修复
security-fix:
	@echo "🛡️ 运行安全漏洞修复..."
	@$(ACTIVATE) && \
		bandit -r src/ -f json -o security-report.json || true && \
		echo "✅ 安全检查完成，报告: security-report.json"
```

---

## 🚨 故障排除

### 依赖冲突解决

```bash
#!/bin/bash
# scripts/fix_dependencies.sh

echo "🔧 开始修复依赖冲突..."

# 1. 清理虚拟环境
echo "🗑️ 清理虚拟环境..."
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate

# 2. 升级pip
echo "⬆️ 升级pip..."
pip install --upgrade pip

# 3. 安装pip-tools
echo "📦 安装pip-tools..."
pip install pip-tools

# 4. 重新编译依赖
echo "🔄 重新编译依赖..."
pip-compile pyproject.toml --extra=dev --output-file requirements-dev.txt

# 5. 同步安装
echo "📥 同步安装依赖..."
pip-sync requirements-dev.txt

# 6. 验证核心依赖
echo "✅ 验证核心依赖..."
python -c "
import sys
modules = ['fastapi', 'sqlalchemy', 'redis', 'pytest', 'ruff']
failed = []
for module in modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except ImportError as e:
        failed.append((module, e))
        print(f'❌ {module}: {e}')

if failed:
    print(f'\\n❌ 依赖验证失败: {len(failed)} 个模块')
    sys.exit(1)
else:
    print('\\n✅ 所有核心依赖验证通过')
"

echo "🎉 依赖修复完成！"
```

### 测试失败排查

```bash
#!/bin/bash
# scripts/diagnose_tests.sh

echo "🔍 开始测试诊断..."

# 1. 检查测试收集
echo "📋 检查测试收集..."
pytest --collect-only -q 2>&1 | head -20

# 2. 检查语法错误
echo "🐛 检查语法错误..."
python -c "
import subprocess
import sys

result = subprocess.run(['pytest', '--collect-only'],
                       capture_output=True, text=True)

if result.returncode != 0:
    print('❌ 发现测试收集错误:')
    print(result.stderr)

    # 尝试定位具体错误文件
    lines = result.stderr.split('\n')
    for line in lines:
        if 'error' in line.lower() or 'failed' in line.lower():
            print(f'  📍 {line}')
else:
    print('✅ 测试收集正常')
"

# 3. 检查导入问题
echo "📦 检查关键模块导入..."
python -c "
import sys
import traceback

critical_modules = [
    'src.core.di',
    'src.domain.services.prediction_service',
    'src.database.connection',
    'src.cache.redis_client'
]

failed_imports = []
for module in critical_modules:
    try:
        __import__(module)
        print(f'✅ {module}')
    except Exception as e:
        failed_imports.append((module, e))
        print(f'❌ {module}: {e}')

if failed_imports:
    print(f'\\n❌ 导入失败的模块:')
    for module, error in failed_imports:
        print(f'  📍 {module}: {error}')
        print(f'     {traceback.format_exc()}')
"

# 4. 运行最小测试集
echo "🧪 运行最小测试集..."
pytest tests/unit/utils/ -v --tb=short --maxfail=3

# 5. 检查环境问题
echo "🌍 检查环境状态..."
python -c "
import os
import sys

print(f'Python版本: {sys.version}')
print(f'当前工作目录: {os.getcwd()}')
print(f'PYTHONPATH: {os.environ.get(\"PYTHONPATH\", \"未设置\")}')

# 检查关键环境变量
env_vars = ['DATABASE_URL', 'REDIS_URL', 'ENVIRONMENT']
for var in env_vars:
    value = os.environ.get(var)
    if value:
        print(f'✅ {var}: 已设置')
    else:
        print(f'⚠️ {var}: 未设置')
"

echo "🔍 测试诊断完成！"
```

### Docker环境问题

```bash
#!/bin/bash
# scripts/fix_docker_environment.sh

echo "🐳 开始修复Docker环境..."

# 1. 完全重置Docker环境
echo "🗑️ 清理Docker环境..."
docker-compose down -v --remove-orphans
docker system prune -f
docker volume prune -f

# 2. 清理悬空镜像
echo "🧹 清理悬空镜像..."
docker image prune -f

# 3. 重新构建启动
echo "🔄 重新构建启动..."
docker-compose up --build -d

# 4. 等待服务启动
echo "⏳ 等待服务启动..."
sleep 30

# 5. 检查服务健康状态
echo "🏥 检查服务健康状态..."
docker-compose ps

# 6. 检查服务日志
echo "📋 检查服务日志..."
for service in app db redis; do
    echo "\\n=== $service 服务日志 ==="
    docker-compose logs --tail=20 $service
done

# 7. 验证服务连接
echo "🔗 验证服务连接..."
docker-compose exec -T app python -c "
import asyncio
import sys

async def check_services():
    try:
        # 检查数据库连接
        from src.database.connection import DatabaseManager
        db_manager = DatabaseManager()
        await db_manager.check_connection()
        print('✅ 数据库连接正常')

        # 检查Redis连接
        from src.cache.redis_client import RedisClient
        redis_client = RedisClient()
        await redis_client.ping()
        print('✅ Redis连接正常')

        return True
    except Exception as e:
        print(f'❌ 服务连接失败: {e}')
        return False

result = asyncio.run(check_services())
sys.exit(0 if result else 1)
"

if [ $? -eq 0 ]; then
    echo "✅ Docker环境修复完成！"
else
    echo "❌ Docker环境仍有问题，请检查上述日志"
fi
```

### 内存和性能监控

```python
#!/usr/bin/env python3
# scripts/performance_monitor.py

import psutil
import time
import os
import sys
import subprocess
import tracemalloc
from memory_profiler import profile
from pathlib import Path

class PerformanceMonitor:
    """性能监控工具"""

    def __init__(self):
        self.start_time = time.time()
        self.process = psutil.Process()

    def monitor_memory_usage(self):
        """监控内存使用情况"""
        # 内存信息
        memory_info = self.process.memory_info()
        memory_percent = self.process.memory_percent()

        print(f"🧠 内存使用:")
        print(f"   RSS: {memory_info.rss / 1024 / 1024:.2f} MB")
        print(f"   VMS: {memory_info.vms / 1024 / 1024:.2f} MB")
        print(f"   占比: {memory_percent:.2f}%")

        # 系统内存
        system_memory = psutil.virtual_memory()
        print(f"🖥️ 系统内存:")
        print(f"   总计: {system_memory.total / 1024 / 1024 / 1024:.2f} GB")
        print(f"   可用: {system_memory.available / 1024 / 1024 / 1024:.2f} GB")
        print(f"   使用率: {system_memory.percent:.2f}%")

    def monitor_cpu_usage(self):
        """监控CPU使用情况"""
        cpu_percent = self.process.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()

        print(f"⚡ CPU使用:")
        print(f"   进程CPU: {cpu_percent:.2f}%")
        print(f"   CPU核心数: {cpu_count}")
        print(f"   系统负载: {os.getloadavg()[0]:.2f}")

    def monitor_disk_io(self):
        """监控磁盘IO"""
        disk_io = self.process.io_counters()
        disk_usage = psutil.disk_usage('/')

        print(f"💾 磁盘IO:")
        print(f"   读取次数: {disk_io.read_count}")
        print(f"   写入次数: {disk_io.write_count}")
        print(f"   读取字节: {disk_io.read_bytes / 1024 / 1024:.2f} MB")
        print(f"   写入字节: {disk_io.write_bytes / 1024 / 1024:.2f} MB")

        print(f"💿 磁盘使用:")
        print(f"   总计: {disk_usage.total / 1024 / 1024 / 1024:.2f} GB")
        print(f"   可用: {disk_usage.free / 1024 / 1024 / 1024:.2f} GB")
        print(f"   使用率: {(1 - disk_usage.free / disk_usage.total) * 100:.2f}%")

    def profile_memory_usage(self, duration: int = 60):
        """内存使用分析"""
        print(f"🔍 开始内存使用分析 ({duration}秒)...")

        # 启动内存跟踪
        tracemalloc.start()

        start_time = time.time()
        peak_memory = 0

        while time.time() - start_time < duration:
            # 获取当前内存使用
            current, peak = tracemalloc.get_traced_memory()
            peak_memory = max(peak_memory, peak)

            # 获取进程内存
            memory_info = self.process.memory_info()

            print(f"📊 [{time.time() - start_time:.1f}s] "
                  f"RSS: {memory_info.rss / 1024 / 1024:.1f}MB, "
                  f"Peak: {peak / 1024 / 1024:.1f}MB")

            time.sleep(5)

        tracemalloc.stop()

        print(f"📈 内存分析完成，峰值使用: {peak_memory / 1024 / 1024:.2f} MB")

    @profile
    def profile_function(self, func, *args, **kwargs):
        """函数性能分析"""
        print(f"🔍 分析函数性能: {func.__name__}")
        start_time = time.time()
        start_memory = self.process.memory_info().rss

        try:
            result = func(*args, **kwargs)

            end_time = time.time()
            end_memory = self.process.memory_info().rss

            print(f"⏱️ 执行时间: {end_time - start_time:.4f} 秒")
            print(f"🧠 内存变化: {(end_memory - start_memory) / 1024 / 1024:.2f} MB")

            return result

        except Exception as e:
            print(f"❌ 函数执行失败: {e}")
            raise

def main():
    """主函数"""
    monitor = PerformanceMonitor()

    print("🚀 启动性能监控...")
    print(f"📊 进程ID: {os.getpid()}")
    print(f"📁 工作目录: {os.getcwd()}")

    while True:
        print("\\n" + "="*50)
        print(f"⏰ 运行时间: {time.time() - monitor.start_time:.1f} 秒")

        # 监控各项指标
        monitor.monitor_memory_usage()
        monitor.monitor_cpu_usage()
        monitor.monitor_disk_io()

        # 等待下次监控
        time.sleep(10)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\\n👋 监控已停止")
    except Exception as e:
        print(f"❌ 监控出错: {e}")
        sys.exit(1)
```

---

## 📋 总结

这个详细的参考文档提供了：

1. **完整的代码示例** - 策略工厂、依赖注入、CQRS模式
2. **详细的配置参数** - pyproject.toml、pytest.ini等
3. **性能优化指南** - 数据库、缓存、API优化
4. **质量修复工具** - 自动化修复脚本和高级用法
5. **故障排除方案** - 依赖冲突、测试失败、Docker问题
6. **性能监控工具** - 内存、CPU、磁盘IO监控

通过分层文档架构，开发者可以根据需要选择合适的文档层级：
- **快速入门**: 使用 CLAUDE.md
- **深入开发**: 参考 CLAUDE_DETAILED.md

---

*文档版本: v1.0 | 最后更新: 2025-11-16*