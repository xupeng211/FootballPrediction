"""
pytest配置文件

提供全局的pytest配置和fixtures，包括：
- 数据库测试配置
- Mock配置
- 测试环境设置
- Prometheus metrics清理
"""

from unittest.mock import AsyncMock

import pytest
from prometheus_client import REGISTRY, CollectorRegistry


@pytest.fixture(autouse=True)
def reset_prometheus_registry():
    """重置Prometheus注册表，避免测试间指标重复注册"""
    # 清空全局注册表中的collectors
    collectors_to_remove = list(REGISTRY._collector_to_names.keys())
    for collector in collectors_to_remove:
        try:
            REGISTRY.unregister(collector)
        except KeyError:
            pass  # 如果collector已经被移除，忽略错误


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
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
    """提供干净的Prometheus注册表用于测试"""
    return CollectorRegistry()


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

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
    warnings.filterwarnings("ignore", message=".*Number.*field.*")
