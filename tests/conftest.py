"""
pytest配置文件 - Phase 2 增强版本

Enhanced pytest configuration with improved testing infrastructure
"""

import os
import sys
import warnings
import asyncio
import tempfile
from typing import Any, Generator, AsyncGenerator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

# 导入增强的测试配置
from tests.test_config import (
    TestConfig,
    MockServiceRegistry,
    TestDataFactory,
    TestUtilities,
    setup_test_environment,
    mock_registry,
    data_factory,
    test_utils
)

from src.main import app
from src.database.base import Base
from src.database.dependencies import (
    get_db,
    get_async_db,
    get_test_db,
    get_test_async_db,
)

# 全局事件循环处理
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# 配置警告过滤器 - 必须在其他导入之前
def configure_warnings():
    """配置测试期间的警告过滤器"""

    # 过滤 DeprecationWarning
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*直接从 error_handler 导入已弃用.*",
    )

    # 设置环境变量
    os.environ["GEVENT_SUPPRESS_RAGWARN"] = "1"


# 立即配置警告
configure_warnings()


# === 测试数据库配置 ===

# 同步测试数据库（使用 SQLite 内存数据库）
TEST_DATABASE_URL = "sqlite:///:memory:"
test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

# 异步测试数据库
TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
test_async_engine = create_async_engine(
    TEST_ASYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingAsyncSessionLocal = async_sessionmaker(
    bind=test_async_engine, class_=AsyncSession, expire_on_commit=False
)


# === 测试数据库 Fixtures ===


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """提供测试用的同步数据库会话"""
    # 创建所有表
    Base.metadata.create_all(bind=test_engine)

    # 创建会话
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        # 删除所有表
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
async def async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """提供测试用的异步数据库会话"""
    # 创建所有表
    async with test_async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # 创建会话
    session = TestingAsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
        # 删除所有表
        async with test_async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(scope="function")
def test_client(db_session: Session) -> Generator[TestClient, None, None]:
    """提供测试客户端，使用 dependency_overrides 替换数据库依赖"""

    # 重写依赖注入，使用测试数据库会话
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    def override_get_async_db():
        # 对于同步测试客户端，这里提供一个异步会话的模拟
        # 实际的异步测试应该使用 async_test_client
        try:
            yield db_session  # 这里为了兼容性使用同步会话
        finally:
            pass

    # 应用依赖覆盖
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_async_db] = override_get_async_db

    # 创建测试客户端
    with TestClient(app) as client:
        yield client

    # 清理依赖覆盖
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def async_test_client(
    async_db_session: AsyncSession,
) -> AsyncGenerator[TestClient, None]:
    """提供异步测试客户端"""

    # 重写依赖注入
    async def override_get_async_db():
        try:
            yield async_db_session
        finally:
            pass

    def override_get_db():
        try:
            yield async_db_session  # 使用异步会话
        finally:
            pass

    # 应用依赖覆盖
    app.dependency_overrides[get_async_db] = override_get_async_db
    app.dependency_overrides[get_db] = override_get_db

    # 使用 httpx 创建异步测试客户端
    from httpx import AsyncClient

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    # 清理依赖覆盖
    app.dependency_overrides.clear()


# === 环境配置 ===
@pytest.fixture(autouse=True)
def test_env():
    """设置测试环境变量（不再使用 monkeypatch）"""
    os.environ["ENVIRONMENT"] = "testing"
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["SECRET_KEY"] = "test-secret-key"
    os.environ["DEBUG"] = "true"
    os.environ["TESTING"] = "true"


# === Mock 外部服务的 Fixtures（不再使用 sys.modules） ===


@pytest.fixture
def mock_redis():
    """Mock Redis 服务"""
    from tests.helpers.mock_redis import MockRedis

    # 替换 Redis 导入
    import src.cache.redis_manager

    src.cache.redis_manager.redis_client = MockRedis()

    yield MockRedis()

    # 清理
    src.cache.redis_manager.redis_client = None


@pytest.fixture
def mock_mlflow():
    """Mock MLflow 服务"""
    from tests.helpers.mock_mlflow import MockMlflowClient

    # 替换 MLflow 客户端
    import src.monitoring.metrics_collector

    original_client = getattr(src.monitoring.metrics_collector, "mlflow_client", None)
    src.monitoring.metrics_collector.mlflow_client = MockMlflowClient()

    yield MockMlflowClient()

    # 恢复原始客户端
    src.monitoring.metrics_collector.mlflow_client = original_client


@pytest.fixture
def mock_kafka():
    """Mock Kafka 生产者和消费者"""
    from tests.helpers.mock_kafka import MockKafkaProducer, MockKafkaConsumer

    # 替换 Kafka 导入
    import src.streaming.kafka_producer
    import src.streaming.kafka_consumer

    original_producer = getattr(src.streaming.kafka_producer, "KafkaProducer", None)
    original_consumer = getattr(src.streaming.kafka_consumer, "KafkaConsumer", None)

    src.streaming.kafka_producer.KafkaProducer = MockKafkaProducer
    src.streaming.kafka_consumer.KafkaConsumer = MockKafkaConsumer

    yield MockKafkaProducer(), MockKafkaConsumer()

    # 恢复原始类
    src.streaming.kafka_producer.KafkaProducer = original_producer
    src.streaming.kafka_consumer.KafkaConsumer = original_consumer


# === 测试数据 Fixtures ===


@pytest.fixture
def sample_team_data():
    """示例团队数据"""
    return {
        "name": "Test Team",
        "league": "Test League",
        "country": "Test Country",
        "founded": 2020,
    }


@pytest.fixture
def sample_match_data(sample_team_data):
    """示例比赛数据"""
    return {
        "home_team": sample_team_data,
        "away_team": {**sample_team_data, "name": "Away Team"},
        "date": "2024-01-01",
        "league": "Test League",
    }


@pytest.fixture
def sample_prediction_data(sample_match_data):
    """示例预测数据"""
    return {
        "match": sample_match_data,
        "predicted_winner": "home",
        "confidence": 0.75,
        "model_version": "v1.0.0",
    }


# === 标记定义 ===
def pytest_configure(config):
    """配置 pytest 标记"""
    config.addinivalue_line("markers", "unit: 单元测试")
    config.addinivalue_line("markers", "integration: 集成测试")
    config.addinivalue_line("markers", "api: API测试")
    config.addinivalue_line("markers", "database: 数据库测试")
    config.addinivalue_line("markers", "slow: 慢速测试")
    config.addinivalue_line("markers", "legacy: 遗留测试（使用真实服务）")
    config.addinivalue_line("markers", "requires_redis: 需要Redis的测试")
    config.addinivalue_line("markers", "requires_db: 需要数据库的测试")


# === 测试收集钩子 ===
def pytest_collection_modifyitems(config, items):
    """修改测试收集，根据标记应用不同的设置"""
    for item in items:
        # 为 unit 测试标记为快速测试
        if "unit" in item.keywords:
            pass  # 移除错误的标记添加

        # 为 legacy 测试添加跳过标记（除非显式运行）
        if "legacy" in item.keywords and not config.getoption("-m"):
            item.add_marker(
                pytest.mark.skip(reason="Legacy tests - run with pytest -m legacy")
            )


# === 测试报告钩子 ===
@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """生成测试报告"""
    outcome = yield
    report = outcome.get_result()

    if report.when == "call":
        # 添加额外的测试信息到报告中
        if hasattr(item, "function"):
            report.sections.append(("Test Function", item.function.__name__))
        if hasattr(item, "module"):
            report.sections.append(("Test Module", item.module.__name__))

# 改进的测试配置

# 改进的异步会话fixture
@pytest.fixture(scope="function")
async def async_client():
    """创建异步测试客户端"""
    from httpx import AsyncClient
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client

# Mock服务fixture
@pytest.fixture
def mock_redis():
    """Redis Mock fixture"""
    from tests.redis_mock import MockRedis
    return MockRedis()

@pytest.fixture
def mock_kafka_producer():
    """Kafka Producer Mock fixture"""
    from tests.external_services_mock import MockKafkaProducer
    return MockKafkaProducer()

@pytest.fixture
def mock_kafka_consumer():
    """Kafka Consumer Mock fixture"""
    from tests.external_services_mock import MockKafkaConsumer
    return MockKafkaConsumer()

# 测试数据fixtures
@pytest.fixture
def sample_team_data():
    """示例团队数据"""
    return {
        "id": 1,
        "name": "Test Team",
        "founded_year": 1900,
        "logo_url": "logo.png"
    }

@pytest.fixture
def sample_match_data():
    """示例比赛数据"""
    return {
        "id": 1,
        "home_team_id": 1,
        "away_team_id": 2,
        "match_date": "2024-01-01",
        "venue": "Test Stadium"
    }

# 错误处理fixture
@pytest.fixture
def mock_database_error():
    """模拟数据库错误"""
    def side_effect(*args, **kwargs):
        raise Exception("Database connection failed")
    return side_effect


# === Phase 2 增强Fixtures ===

@pytest.fixture(scope="session", autouse=True)
def test_environment_setup():
    """自动设置测试环境"""
    setup_test_environment()
    yield
    # 清理工作（如果需要）

@pytest.fixture
def test_config():
    """测试配置fixture"""
    return TestConfig()

@pytest.fixture
def mock_services():
    """Mock服务注册表fixture"""
    return mock_registry

@pytest.fixture
def test_data():
    """测试数据工厂fixture"""
    return data_factory

@pytest.fixture
def test_helpers():
    """测试工具类fixture"""
    return test_utils

@pytest.fixture
def mock_redis():
    """Mock Redis fixture"""
    return mock_registry.get_service("redis")

@pytest.fixture
def mock_http_client():
    """Mock HTTP客户端fixture"""
    return mock_registry.get_service("http")

@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka生产者fixture"""
    return mock_registry.get_service("kafka_producer")

@pytest.fixture
def mock_kafka_consumer():
    """Mock Kafka消费者fixture"""
    return mock_registry.get_service("kafka_consumer")

@pytest.fixture
def mock_mlflow():
    """Mock MLflow客户端fixture"""
    return mock_registry.get_service("mlflow")

# 增强的测试数据fixtures
@pytest.fixture
def sample_team_data(test_data):
    """增强的团队数据fixture"""
    return test_data.create_team_data()

@pytest.fixture
def sample_match_data(test_data):
    """增强的比赛数据fixture"""
    return test_data.create_match_data()

@pytest.fixture
def sample_prediction_data(test_data):
    """增强的预测数据fixture"""
    return test_data.create_prediction_data()

@pytest.fixture
def multiple_team_data(test_data):
    """多个团队数据fixture"""
    return [
        test_data.create_team_data(id=1, name="Team A", short_name="TA"),
        test_data.create_team_data(id=2, name="Team B", short_name="TB"),
        test_data.create_team_data(id=3, name="Team C", short_name="TC"),
    ]

@pytest.fixture
def multiple_match_data(test_data, multiple_team_data):
    """多个比赛数据fixture"""
    return [
        test_data.create_match_data(
            id=1,
            home_team_id=1,
            away_team_id=2,
            match_date="2024-01-01T15:00:00"
        ),
        test_data.create_match_data(
            id=2,
            home_team_id=2,
            away_team_id=3,
            match_date="2024-01-02T16:00:00"
        ),
        test_data.create_match_data(
            id=3,
            home_team_id=1,
            away_team_id=3,
            match_date="2024-01-03T17:00:00"
        ),
    ]
