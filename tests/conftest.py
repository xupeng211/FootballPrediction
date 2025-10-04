"""pytest配置及全局测试Mock定义"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock

# import httpx
import pytest
from fastapi.testclient import TestClient

# 预先加载测试环境配置
try:
    from tests.test_env_config import mock_redis_cluster
    mock_redis_cluster()  # 立即应用Redis mock
except ImportError:
    # 如果配置文件不存在，使用专门的mock模块
    try:
        from tests.mocks.redis_mocks import install_redis_mocks
        install_redis_mocks()
    except ImportError:
        # 回退到基本mock
        from unittest.mock import MagicMock

        class RedisClusterStub:
            def __init__(self, *args, **kwargs):
                pass

        redis_cluster_mock = MagicMock()
        redis_cluster_mock.RedisCluster = RedisClusterStub
        sys.modules['redis.cluster'] = redis_cluster_mock

try:
    from pytest import MonkeyPatch
except ImportError:  # pragma: no cover
    from _pytest.monkeypatch import MonkeyPatch

from tests.helpers import (
    MockRedis,
    apply_http_mocks,
    apply_kafka_mocks,
    apply_mlflow_mocks,
    apply_redis_mocks,
    create_sqlite_memory_engine,
    create_sqlite_sessionmaker,
)

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# 默认启用最小化模式，避免导入重量级依赖
os.environ.setdefault("MINIMAL_API_MODE", "true")
os.environ.setdefault("FAST_FAIL", "false")
os.environ.setdefault("ENABLE_METRICS", "false")
os.environ.setdefault("METRICS_ENABLED", "false")
os.environ.setdefault("ENABLED_SERVICES", "[]")


def _apply_feast_mocks(monkeypatch: MonkeyPatch) -> None:
    """
    应用Feast相关的Mock，解决Redis版本兼容性问题

    这将阻止Feast导入时尝试使用Redis特定功能，避免版本冲突
    """
    import sys
    from unittest.mock import MagicMock

    # 在导入前设置环境变量，禁用Redis相关功能
    monkeypatch.setenv("FEAST_DISABLE_REDIS", "true")

    # 完全Mock掉Feast模块，避免Redis依赖问题
    class MockFeastModule:
        """Feast模块的完整Mock"""
        def __getattr__(self, name):
            return MagicMock()

    # 创建feast及其子模块的mock
    feast_modules = [
        'feast',
        'feast.infra',
        'feast.infra.online_stores',
        'feast.infra.online_stores.redis',
        'feast.infra.offline_stores',
        'feast.infra.offline_stores.contrib',
        'feast.infra.offline_stores.contrib.postgres_offline_store',
        'feast.types',
    ]

    for module_name in feast_modules:
        if module_name not in sys.modules:
            sys.modules[module_name] = MockFeastModule()

    # Mock所有Redis相关模块
    class RedisStub:
        def __init__(self, *args, **kwargs):
            pass
        def ping(self):
            return True

    class RedisClusterStub(RedisStub):
        pass

    class SentinelStub:
        def __init__(self, *args, **kwargs):
            pass

    redis_modules = {
        'redis.cluster': MagicMock(RedisCluster=RedisClusterStub),
        'redis.asyncio.cluster': MagicMock(RedisCluster=RedisClusterStub),
        'redis.sentinel': MagicMock(Sentinel=SentinelStub),
        'redis.asyncio.sentinel': MagicMock(Sentinel=SentinelStub),
    }

    for module_name, module_mock in redis_modules.items():
        sys.modules[module_name] = module_mock


def _apply_data_quality_mocks(monkeypatch: MonkeyPatch) -> None:
    """
    Mock数据质量监控器，避免数据库依赖
    """
    from unittest.mock import AsyncMock, MagicMock

    # 创建Mock的数据质量监控器
    mock_monitor = MagicMock()
    mock_monitor.generate_quality_report = AsyncMock(return_value={
        "overall_status": "healthy",
        "quality_score": 95.0,
        "anomalies": {"count": 0, "items": []},
        "report_time": datetime.now().isoformat(),
        "checks": {
            "data_freshness": {"status": "pass", "score": 100},
            "data_completeness": {"status": "pass", "score": 95},
            "data_consistency": {"status": "pass", "score": 90},
        }
    })

    # Mock DataQualityMonitor类
    from src.data.quality.data_quality_monitor import DataQualityMonitor
    monkeypatch.setattr(DataQualityMonitor, "__new__", lambda *args, **kwargs: mock_monitor)


@pytest.fixture(scope="session", autouse=True)
def mock_external_services() -> None:
    """在测试阶段统一Mock外部依赖"""

    monkeypatch = MonkeyPatch()

    # 修复Redis/Feast兼容性问题 - 必须在其他导入之前
    _apply_feast_mocks(monkeypatch)

    # 应用Redis mock（必须在Feast导入后）
    apply_redis_mocks(monkeypatch)
    apply_mlflow_mocks(monkeypatch)
    apply_kafka_mocks(monkeypatch)
    apply_http_mocks(monkeypatch, responses={})

    # Mock数据质量监控器
    _apply_data_quality_mocks(monkeypatch)

    yield
    monkeypatch.undo()


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def sqlite_memory_engine():
    """提供内存 SQLite Engine"""

    engine = create_sqlite_memory_engine()
    yield engine
    engine.dispose()


@pytest.fixture(scope="session")
def sqlite_session_factory(sqlite_memory_engine):  # type: ignore[annotations]
    """基于内存数据库的 Sessionmaker"""

    return create_sqlite_sessionmaker(engine=sqlite_memory_engine)


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    redis_mock = MockRedis()
    redis_mock.set("__ping__", "ok")
    return redis_mock


@pytest.fixture
def mock_db_session():
    """模拟数据库会话"""
    from sqlalchemy.ext.asyncio import AsyncSession

    session = AsyncMock(spec=AsyncSession)
    session.execute.return_value = AsyncMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    return session


@pytest.fixture
def test_client():
    """测试客户端"""
    from src.main import app

    client = TestClient(app)
    return client


@pytest.fixture
async def async_client():
    """异步测试客户端"""
    from httpx import AsyncClient

    from src.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "email": "test@example.com",
        "username": "testuser",
        "password": "TestPassword123!",
        "full_name": "Test User",
    }


@pytest.fixture
def sample_prediction_data():
    """示例预测数据"""
    return {
        "match_id": 12345,
        "home_team": "Team A",
        "away_team": "Team B",
        "predicted_home_score": 2,
        "predicted_away_score": 1,
        "confidence": 0.75,
    }


@pytest.fixture
def auth_headers():
    """认证头"""
    return {
        "Authorization": "Bearer test_token_here",
        "Content-Type": "application/json",
    }


# 测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "slow: 标记测试为慢速测试")
    config.addinivalue_line("markers", "integration: 标记为集成测试")
    config.addinivalue_line("markers", "e2e: 标记为端到端测试")
    config.addinivalue_line("markers", "smoke: 标记为冒烟测试")
    config.addinivalue_line("markers", "legacy: 标记为遗留测试（依赖真实服务）")
    config.addinivalue_line("markers", "unit: 标记为单元测试")


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        # 自动添加标记
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
