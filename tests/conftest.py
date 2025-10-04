"""
pytest配置文件 - 最小化版本
"""

import asyncio
import os
import sys
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
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
    """提供干净的Prometheus注册表用于测试"""
    from unittest.mock import Mock

    mock_registry = Mock()
    return mock_registry


@pytest.fixture
def mock_prometheus_client():
    """模拟Prometheus客户端"""
    mock_client = MagicMock()
    mock_counter = MagicMock()
    mock_counter.inc = MagicMock()
    mock_counter.labels = MagicMock(return_value=mock_counter)
    mock_client.Counter = MagicMock(return_value=mock_counter)
    mock_client.Gauge = MagicMock(return_value=mock_counter)
    mock_client.Histogram = MagicMock(return_value=mock_counter)
    return mock_client


@pytest.fixture
def mock_mlflow_client():
    """模拟MLflow客户端"""
    mock_client = Mock()
    mock_version_info = Mock()
    mock_version_info.version = "1"
    mock_version_info.current_stage = "Production"
    mock_version_info.name = "football_baseline_model"
    mock_client.get_latest_versions = Mock(return_value=[mock_version_info])
    return mock_client


@pytest.fixture
def mock_redis_manager():
    """模拟Redis管理器"""
    mock_manager = AsyncMock()
    mock_manager.connect = AsyncMock()
    mock_manager.disconnect = AsyncMock()
    mock_manager.is_connected = AsyncMock(return_value=True)
    mock_manager.ping = AsyncMock(return_value=True)
    mock_manager.get = AsyncMock(return_value=None)
    mock_manager.set = AsyncMock(return_value=True)
    mock_manager.delete = AsyncMock(return_value=1)
    return mock_manager


# Configure pytest
def pytest_configure(config):
    """配置pytest"""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")


@pytest.fixture(autouse=True)
def suppress_warnings():
    """抑制测试中的警告"""
    import warnings

    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
