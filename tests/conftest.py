"""
pytest配置文件

提供全局的pytest配置和fixtures，包括：
- 数据库测试配置
- Mock配置
- 测试环境设置
- Prometheus metrics清理
"""

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from prometheus_client import REGISTRY, CollectorRegistry
from sqlalchemy.ext.asyncio import create_async_engine

from src.database.base import Base
from src.database.config import get_test_database_config


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
def setup_test_database(event_loop):
    """
    Set up the test database: create schema before tests and drop after.
    """
    # Ensure we are in the test environment
    os.environ["ENVIRONMENT"] = "test"

    config = get_test_database_config()

    # Use a separate engine for schema creation/deletion
    engine = create_async_engine(config.async_url)

    async def init_db():
        async with engine.begin() as conn:
            # Drop all tables first for a clean state, in case of leftovers
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    event_loop.run_until_complete(init_db())

    yield

    async def teardown_db():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        await engine.dispose()

    event_loop.run_until_complete(teardown_db())


@pytest.fixture(autouse=True)
def reset_prometheus_registry():
    """
    重置Prometheus注册表，避免测试间指标重复注册

    这个fixture在每个测试前自动运行，确保：
    1. 清理全局REGISTRY中的所有collector
    2. 重置MetricsExporter的全局实例
    3. 避免测试之间的状态污染
    """
    # 清空全局注册表中的collectors
    collectors_to_remove = list(REGISTRY._collector_to_names.keys())
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass  # 如果collector已经被移除，忽略错误

    # 重置MetricsExporter的全局实例，避免单例状态污染
    try:
        from src.monitoring.metrics_exporter import reset_metrics_exporter

        reset_metrics_exporter()
    except ImportError:
        pass  # 如果模块不存在，忽略错误


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    # ✅ 修复：rollback 和 close 通常是同步方法，不应该使用 AsyncMock
    session.rollback = Mock()
    session.close = Mock()
    return session


@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    redis_mock = AsyncMock()
    redis_mock.ping = AsyncMock(return_value=True)
    redis_mock.set = AsyncMock(return_value=True)
    redis_mock.get = AsyncMock(return_value=None)
    redis_mock.delete = AsyncMock(return_value=1)
    return redis_mock


@pytest.fixture
def clean_metrics_registry():
    """
    提供干净的Prometheus注册表用于测试

    这个fixture为每个测试提供一个独立的CollectorRegistry实例，
    避免测试间的指标污染和冲突。

    使用方法：
    - 在测试中通过参数接收此fixture
    - 将其传递给MetricsExporter(registry=clean_metrics_registry)
    - 确保每个测试有独立的指标空间
    """
    # 创建全新的注册表实例，完全独立于全局REGISTRY
    return CollectorRegistry()


@pytest.fixture
def mock_prometheus_client():
    """
    模拟Prometheus客户端，避免真实依赖

    提供完整的Prometheus客户端mock，包括：
    - Counter、Gauge、Histogram等指标类型
    - CollectorRegistry注册表
    - 指标导出功能
    """
    mock_client = MagicMock()

    # Mock Counter指标
    mock_counter = MagicMock()
    mock_counter.inc = MagicMock()
    mock_counter.labels = MagicMock(return_value=mock_counter)
    mock_client.Counter = MagicMock(return_value=mock_counter)

    # Mock Gauge指标
    mock_gauge = MagicMock()
    mock_gauge.set = MagicMock()
    mock_gauge.inc = MagicMock()
    mock_gauge.dec = MagicMock()
    mock_gauge.labels = MagicMock(return_value=mock_gauge)
    mock_client.Gauge = MagicMock(return_value=mock_gauge)

    # Mock Histogram指标
    mock_histogram = MagicMock()
    mock_histogram.observe = MagicMock()
    mock_histogram.time = MagicMock()
    mock_histogram.labels = MagicMock(return_value=mock_histogram)
    mock_client.Histogram = MagicMock(return_value=mock_histogram)

    # Mock Summary指标
    mock_summary = MagicMock()
    mock_summary.observe = MagicMock()
    mock_summary.time = MagicMock()
    mock_summary.labels = MagicMock(return_value=mock_summary)
    mock_client.Summary = MagicMock(return_value=mock_summary)

    # Mock CollectorRegistry
    mock_registry = MagicMock()
    mock_registry.register = MagicMock()
    mock_registry.unregister = MagicMock()
    mock_client.CollectorRegistry = MagicMock(return_value=mock_registry)
    mock_client.REGISTRY = mock_registry

    # Mock 导出功能
    mock_client.generate_latest = MagicMock(return_value=b"# Mock metrics\n")
    mock_client.exposition = MagicMock()

    return mock_client


@pytest.fixture
def mock_duration_histogram():
    """
    模拟duration_histogram指标

    这个fixture专门用于模拟持续时间直方图指标，
    确保在测试中正确初始化和使用。
    """
    mock_histogram = MagicMock()
    mock_histogram.observe = MagicMock()
    mock_histogram.time = MagicMock()
    mock_histogram.labels = MagicMock(return_value=mock_histogram)

    # 模拟上下文管理器
    mock_timer = MagicMock()
    mock_timer.__enter__ = MagicMock(return_value=mock_timer)
    mock_timer.__exit__ = MagicMock(return_value=None)
    mock_histogram.time.return_value = mock_timer

    return mock_histogram


@pytest.fixture
def mock_total_metrics():
    """
    模拟*_total_metric计数器指标

    这个fixture提供各种总计指标的mock，包括：
    - requests_total
    - errors_total
    - predictions_total
    等常用的计数器指标
    """
    mock_metrics = {}

    # 创建各种total指标的mock
    metric_names = [
        "requests_total",
        "errors_total",
        "predictions_total",
        "cache_hits_total",
        "database_queries_total",
    ]

    for name in metric_names:
        mock_counter = MagicMock()
        mock_counter.inc = MagicMock()
        mock_counter.labels = MagicMock(return_value=mock_counter)
        mock_metrics[name] = mock_counter

    return mock_metrics


# 配置asyncio测试模式
pytest_plugins = ("pytest_asyncio",)


# 配置异步测试标记
def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")


# 禁用一些警告
@pytest.fixture(autouse=True)
def suppress_warnings():
    """抑制测试中的警告"""
    import warnings

    # 基础警告抑制
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)

    # Marshmallow 4 兼容性警告抑制 - 针对第三方库(Great Expectations)
    try:
        import marshmallow.warnings

        warnings.filterwarnings(
            "ignore",
            category=marshmallow.warnings.ChangedInMarshmallow4Warning,
            message=".*Number.*field should not be instantiated.*",
        )
    except ImportError:
        # 如果无法导入marshmallow.warnings，使用通用过滤器
        warnings.filterwarnings(
            "ignore", message=".*Number.*field.*should.*not.*be.*instantiated.*"
        )
