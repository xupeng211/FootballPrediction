"""pytest配置及全局测试Mock定义"""

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# import httpx
import pytest
from fastapi.testclient import TestClient

try:
    from pytest import MonkeyPatch
except ImportError:  # pragma: no cover
    from _pytest.monkeypatch import MonkeyPatch

from tests.helpers import (
    MockRedis,
    apply_http_mocks,
    apply_kafka_mocks,
    apply_mlflow_mocks,
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
os.environ.setdefault("ENABLE_FEAST", "false")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ENABLED_SERVICES", "[]")
os.environ.setdefault("TESTING", "true")


def _setup_redis_mocks():
    """
    设置Redis相关的所有Mock，必须在导入任何其他模块之前调用
    """
    import sys

    # 创建Redis模块的完整Mock
    class RedisModule:
        VERSION = (5, 2, 1)
        __version__ = "5.2.1"

        class Redis:
            def __init__(self, *args, **kwargs):
                pass

            def ping(self):
                return True

            def get(self, key):
                return None

            def set(self, key, value, ex=None):
                return True

            def exists(self, key):
                return False

            def delete(self, key):
                return 0

            def close(self):
                pass

        class ConnectionPool:
            def __init__(self, *args, **kwargs):
                pass

        class RedisCluster(Redis):
            def __init__(self, *args, **kwargs):
                pass

        # 添加 exceptions 模块
        class exceptions:
            class ConnectionError(Exception):
                pass
            class RedisError(Exception):
                pass
            class TimeoutError(Exception):
                pass

    class RedisAsyncioModule:
        VERSION = (5, 2, 1)
        __version__ = "5.2.1"

        class Redis:
            def __init__(self, *args, **kwargs):
                pass

            async def ping(self):
                return True

            async def get(self, key):
                return None

            async def set(self, key, value, ex=None):
                return True

            async def exists(self, key):
                return False

            async def delete(self, key):
                return 0

            async def close(self):
                pass

        class RedisCluster(Redis):
            def __init__(self, *args, **kwargs):
                pass

        class Sentinel:
            def __init__(self, *args, **kwargs):
                pass

    # 创建Redis模块实例
    redis_module = RedisModule()
    redis_asyncio_module = RedisAsyncioModule()

    # 设置所有需要的Redis模块
    redis_modules = {
        'redis': redis_module,
        'redis.cluster': type('RedisClusterModule', (), {
            'RedisCluster': RedisModule.RedisCluster,
            'ClusterNode': type('ClusterNode', (), {})
        })(),
        'redis.connection': type('RedisConnectionModule', (), {
            'ConnectionPool': RedisModule.ConnectionPool
        })(),
        'redis.asyncio': redis_asyncio_module,
        'redis.asyncio.cluster': type('RedisAsyncioClusterModule', (), {
            'RedisCluster': RedisAsyncioModule.RedisCluster
        })(),
        'redis.sentinel': type('RedisSentinelModule', (), {
            'Sentinel': type('Sentinel', (), {})
        })(),
        'redis.asyncio.sentinel': type('RedisAsyncioSentinelModule', (), {
            'Sentinel': RedisAsyncioModule.Sentinel
        })(),
    }

    # 将asyncio模块添加到redis模块的属性中
    redis_module.asyncio = redis_asyncio_module

    # 添加到sys.modules
    for name, module in redis_modules.items():
        if name not in sys.modules:
            sys.modules[name] = module


def _setup_feast_mocks():
    """
    设置Feast相关的Mock
    """
    import sys
    from unittest.mock import MagicMock

    # 创建Feast的Mock
    class FeastModule:
        def __getattr__(self, name):
            return MagicMock()

        class Entity:
            def __init__(self, *args, **kwargs):
                pass

        class FeatureStore:
            def __init__(self, *args, **kwargs):
                pass

        class FeatureView:
            def __init__(self, *args, **kwargs):
                pass

        class Field:
            def __init__(self, *args, **kwargs):
                pass

        class types:
            class Float64:
                pass

            class Int64:
                pass

        class infra:
            class online_stores:
                class redis:
                    class RedisOnlineStore:
                        def __init__(self, *args, **kwargs):
                            pass

            class offline_stores:
                class contrib:
                    class postgres_offline_store:
                        class postgres_source:
                            class PostgreSQLSource:
                                def __init__(self, *args, **kwargs):
                                    pass

    # 添加Feast模块
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
            sys.modules[module_name] = FeastModule()


# 在导入任何其他模块之前设置Mock
_setup_redis_mocks()
_setup_feast_mocks()


@pytest.fixture(scope="session", autouse=True)
def mock_external_services() -> None:
    """在测试阶段统一Mock外部依赖"""

    monkeypatch = MonkeyPatch()

    # Mock数据质量监控器
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
    try:
        from src.data.quality.data_quality_monitor import DataQualityMonitor
        monkeypatch.setattr(DataQualityMonitor, "__new__", lambda *args, **kwargs: mock_monitor)
    except ImportError:
        pass

    apply_mlflow_mocks(monkeypatch)
    apply_kafka_mocks(monkeypatch)
    apply_http_mocks(monkeypatch, responses={})

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
