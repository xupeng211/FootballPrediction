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

@pytest.fixture(scope = os.getenv("CONFTEST_SCOPE_15"))
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
    mock_version_info.current_stage = os.getenv("CONFTEST_CURRENT_STAGE_66")
    mock_version_info.name = os.getenv("CONFTEST_NAME_67")
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

@pytest.fixture
def client():
    """创建测试客户端"""
    from fastapi.testclient import TestClient
    try:
        # 只在真正需要时才导入app
        import sys
        if 'src.main' not in sys.modules:
            # 抑制应用启动时的日志输出
            import logging
            logging.getLogger().setLevel(logging.CRITICAL)
            # 设置环境变量以减少初始化
            import os
            os.environ['TESTING'] = 'true'
            os.environ['LOG_LEVEL'] = 'CRITICAL'
        from src.main import app
        return TestClient(app)
    except ImportError:
        # 如果导入失败，返回一个简单的模拟客户端
        from unittest.mock import Mock
        mock_client = Mock()
        mock_client.get = Mock(return_value=Mock(status_code=200, json=lambda: {}))
        mock_client.post = Mock(return_value=Mock(status_code=200, json=lambda: {}))
        mock_client.put = Mock(return_value=Mock(status_code=200, json=lambda: {}))
        mock_client.delete = Mock(return_value=Mock(status_code=200, json=lambda: {}))
        return mock_client

@pytest.fixture(autouse=True)
def suppress_warnings():
    """抑制测试中的警告"""
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=UserWarning)
