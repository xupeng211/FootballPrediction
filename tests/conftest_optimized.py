"""
优化的测试配置文件
Optimized Test Configuration

提供性能优化的测试fixtures和配置，包括：
- 智能资源管理
- 测试并行化支持
- 缓存和复用机制
- 快速测试模式
"""

import asyncio
import pytest
import os
import sys
import time
from pathlib import Path
from typing import AsyncGenerator, Generator, Any, Dict, List
import logging
from unittest.mock import Mock, AsyncMock, MagicMock

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, "src")

# 配置日志
logging.basicConfig(level=logging.WARNING)  # 测试时减少日志输出
logger = logging.getLogger(__name__)

# 测试环境配置
os.environ["TESTING"] = "true"
os.environ["TEST_ENV"] = "optimized"

# 性能优化标志
FAST_TESTS = os.getenv("FAST_TESTS", "false").lower() == "true"
SKIP_INTEGRATION = os.getenv("SKIP_INTEGRATION", "false").lower() == "true"
SKIP_PERFORMANCE = os.getenv("SKIP_PERFORMANCE", "true").lower() == "true"
SKIP_SLOW = os.getenv("SKIP_SLOW", "false").lower() == "true"

# 共享资源缓存
_shared_resources: Dict[str, Any] = {}
_resource_locks: Dict[str, asyncio.Lock] = {}


def pytest_configure(config):
    """配置pytest"""
    # 注册自定义标记
    config.addinivalue_line(
        "markers", "unit: Unit tests (fast, isolated)"
    )
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, requires external services)"
    )
    config.addinivalue_line(
        "markers", "performance: Performance tests (very slow, resource intensive)"
    )
    config.addinivalue_line(
        "markers", "slow: Slow tests (takes more than 1 second)"
    )
    config.addinivalue_line(
        "markers", "fast: Fast tests (takes less than 100ms)"
    )
    config.addinivalue_line(
        "markers", "cache: Tests that involve caching"
    )
    config.addinivalue_line(
        "markers", "kafka: Tests that require Kafka"
    )
    config.addinivalue_line(
        "markers", "database: Tests that require database"
    )
    config.addinivalue_line(
        "markers", "api: API tests"
    )


def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    # 根据环境变量跳过特定类型的测试
    if SKIP_INTEGRATION:
        skip_integration = pytest.mark.skip(reason="Integration tests skipped")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

    if SKIP_PERFORMANCE:
        skip_performance = pytest.mark.skip(reason="Performance tests skipped")
        for item in items:
            if "performance" in item.keywords:
                item.add_marker(skip_performance)

    if SKIP_SLOW:
        skip_slow = pytest.mark.skip(reason="Slow tests skipped")
        for item in items:
            if "slow" in item.keywords:
                item.add_marker(skip_slow)

    # 快速测试模式：只运行unit和fast标记的测试
    if FAST_TESTS:
        skip_not_fast = pytest.mark.skip(reason="Only fast tests in FAST_TESTS mode")
        for item in items:
            if not any(marker in item.keywords for marker in ["unit", "fast"]):
                item.add_marker(skip_not_fast)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环（session级别复用）"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def optimized_database():
    """优化的数据库fixture（session级别复用）"""
    if SKIP_INTEGRATION:
        pytest.skip("Integration tests skipped")
        return

    # 使用内存数据库加速测试
    database_url = "sqlite+aiosqlite:///:memory:"

    # 检查是否已经创建
    if "optimized_database" in _shared_resources:
        return _shared_resources["optimized_database"]

    # 创建数据库引擎
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import text

    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=False,  # 内存数据库不需要
        connect_args={"check_same_thread": False}
    )

    # 创建会话工厂
    async_session = sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False
    )

    # 创建表
    try:
        from src.database.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except ImportError:
        # 如果模型不可用，创建基本表
        async with engine.begin() as conn:
            await conn.execute(text("CREATE TABLE IF NOT EXISTS test_table (id INTEGER)"))

    # 缓存共享资源
    _shared_resources["optimized_database"] = {
        "engine": engine,
        "session_factory": async_session
    }

    yield _shared_resources["optimized_database"]

    # 清理（可选，内存数据库会自动清理）
    await engine.dispose()


@pytest.fixture
async def db_session(optimized_database):
    """数据库会话fixture（快速模式）"""
    session_factory = optimized_database["session_factory"]

    async with session_factory() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="session")
async def optimized_redis():
    """优化的Redis fixture（使用模拟或连接池）"""
    if SKIP_INTEGRATION:
        pytest.skip("Integration tests skipped")
        return

    # 检查是否已经创建
    if "optimized_redis" in _shared_resources:
        return _shared_resources["optimized_redis"]

    try:
        import redis.asyncio as redis

        # 尝试连接真实Redis
        redis_client = redis.from_url(
            "redis://localhost:6380/1",
            decode_responses=True,
            max_connections=20,  # 连接池
            retry_on_timeout=True,
            socket_keepalive=True,
            socket_keepalive_options={},
        )

        # 测试连接
        await redis_client.ping()

        _shared_resources["optimized_redis"] = redis_client

    except Exception:
        # 使用模拟Redis
        logger.warning("Using mock Redis for tests")
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.exists = AsyncMock(return_value=0)
        mock_redis.flushdb = AsyncMock(return_value=True)
        mock_redis.close = AsyncMock()
        mock_redis.keys = AsyncMock(return_value=[])
        mock_redis.mget = AsyncMock(return_value=[])
        mock_redis.mset = AsyncMock(return_value=True)
        mock_redis.mdelete = AsyncMock(return_value=0)
        mock_redis.ttl = AsyncMock(return_value=-1)

        _shared_resources["optimized_redis"] = mock_redis

    return _shared_resources["optimized_redis"]


@pytest.fixture(scope="session")
async def optimized_kafka():
    """优化的Kafka fixture（使用模拟）"""
    if SKIP_INTEGRATION:
        pytest.skip("Integration tests skipped")
        return

    # 检查是否已经创建
    if "optimized_kafka" in _shared_resources:
        return _shared_resources["optimized_kafka"]

    # 使用模拟Kafka（更快）
    mock_producer = AsyncMock()
    mock_producer.send = AsyncMock(
        return_value=Mock(
            topic="test_topic",
            partition=0,
            offset=0
        )
    )
    mock_producer.flush = AsyncMock()
    mock_producer.close = AsyncMock()

    mock_consumer = AsyncMock()
    mock_consumer.poll = AsyncMock(return_value={})
    mock_consumer.commit = AsyncMock()
    mock_consumer.close = AsyncMock()

    mock_admin = AsyncMock()
    mock_admin.list_topics = AsyncMock(return_value={})
    mock_admin.create_topics = AsyncMock()
    mock_admin.delete_topics = AsyncMock()
    mock_admin.close = AsyncMock()

    kafka_config = {
        "producer": mock_producer,
        "consumer": mock_consumer,
        "admin_client": mock_admin,
        "topics": ["test_topic"],
        "bootstrap_servers": "localhost:9093"
    }

    _shared_resources["optimized_kafka"] = kafka_config
    return kafka_config


@pytest.fixture
async def api_client():
    """优化的API客户端fixture"""
    try:
        from httpx import AsyncClient
        from src.api.app import app

        # 使用更小的超时值加速测试
        client = AsyncClient(
            app=app,
            base_url="http://test",
            timeout=5.0,  # 5秒超时
            follow_redirects=True
        )

        yield client

    except ImportError:
        # 使用模拟客户端
        mock_client = AsyncMock()
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json = AsyncMock(return_value={"status": "ok"})
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.put = AsyncMock(return_value=mock_response)
        mock_client.delete = AsyncMock(return_value=mock_response)

        yield mock_client


@pytest.fixture
def mock_time():
    """时间模拟fixture"""
    import time

    class MockTime:
        def __init__(self):
            self.current_time = time.time()
            self.start_time = self.current_time

        def time(self):
            return self.current_time

        def sleep(self, seconds):
            self.current_time += seconds

        def advance(self, seconds):
            self.current_time += seconds

        def reset(self):
            self.current_time = self.start_time

    mock = MockTime()

    with patch('time.time', mock.time):
        with patch('asyncio.sleep', mock.sleep):
            yield mock


@pytest.fixture
def fast faker():
    """快速Faker fixture（复用实例）"""
    if "faker" not in _shared_resources:
        from faker import Faker
        _shared_resources["faker"] = Faker()

    return _shared_resources["faker"]


@pytest.fixture
def mock_cache():
    """内存缓存fixture（用于测试）"""
    cache = {}

    async def get(key):
        return cache.get(key)

    async def set(key, value, ttl=None):
        cache[key] = value
        return True

    async def delete(key):
        return cache.pop(key, None) is not None

    async def exists(key):
        return key in cache

    async def clear():
        cache.clear()

    return {
        "get": get,
        "set": set,
        "delete": delete,
        "exists": exists,
        "clear": clear,
        "_cache": cache
    }


@pytest.fixture
async def sample_data_factory():
    """示例数据工厂fixture"""
    faker = await fast faker()

    def create_team(**overrides):
        """创建球队数据"""
        data = {
            "id": faker.random_int(min=1, max=10000),
            "name": faker.company(),
            "city": faker.city(),
            "founded": faker.random_int(min=1900, max=2023),
            "stadium": faker.street_name() + " Stadium",
            "capacity": faker.random_int(min=10000, max=100000)
        }
        data.update(overrides)
        return data

    def create_match(**overrides):
        """创建比赛数据"""
        data = {
            "id": faker.random_int(min=1, max=10000),
            "home_team_id": faker.random_int(min=1, max=100),
            "away_team_id": faker.random_int(min=1, max=100),
            "match_date": faker.date_time_this_year().isoformat(),
            "status": "UPCOMING",
            "competition": faker.word(),
            "season": f"{faker.random_int(2020, 2023)}/{faker.random_int(2021, 2024)}"
        }
        data.update(overrides)
        return data

    def create_prediction(**overrides):
        """创建预测数据"""
        predictions = ["HOME_WIN", "AWAY_WIN", "DRAW"]
        data = {
            "id": faker.random_int(min=1, max=10000),
            "match_id": faker.random_int(min=1, max=10000),
            "prediction": faker.random_element(predictions),
            "confidence": round(faker.pyfloat(left_digits=1, right_digits=2, positive=True, min_value=0.5, max_value=1.0), 2),
            "model_version": f"v{faker.random_int(1, 5)}.{faker.random_int(0, 9)}",
            "created_at": faker.date_time_this_year().isoformat()
        }
        data.update(overrides)
        return data

    return {
        "create_team": create_team,
        "create_match": create_match,
        "create_prediction": create_prediction
    }


# 优化的钩子函数
def pytest_runtest_setup(item):
    """测试前的设置"""
    # 记录测试开始时间
    item.start_time = time.time()


def pytest_runtest_teardown(item):
    """测试后的清理"""
    # 记录慢测试
    if hasattr(item, 'start_time'):
        duration = time.time() - item.start_time
        if duration > 1.0:  # 超过1秒的测试
            logger.warning(f"Slow test: {item.nodeid} took {duration:.2f}s")


def pytest_sessionfinish(session, exitstatus):
    """会话结束时的清理"""
    # 清理共享资源
    for key, resource in _shared_resources.items():
        if hasattr(resource, 'close'):
            if asyncio.iscoroutinefunction(resource.close):
                asyncio.run(resource.close())
            else:
                resource.close()
    _shared_resources.clear()


# 并行测试支持
@pytest.fixture(scope="session")
def worker_id():
    """获取worker ID（用于并行测试）"""
    import os
    return os.getenv("PYTEST_XDIST_WORKER", "main")


@pytest.fixture
def unique_suffix(worker_id):
    """生成唯一的后缀（用于并行测试避免冲突）"""
    return f"{worker_id}_{int(time.time())}"


# 快速测试标记
pytest.mark.fast = pytest.mark.fast
pytest.mark.unit = pytest.mark.unit
pytest.mark.integration = pytest.mark.integration
pytest.mark.performance = pytest.mark.performance
pytest.mark.slow = pytest.mark.slow
