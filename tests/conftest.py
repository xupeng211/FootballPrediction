"""pytest配置及全局测试Mock定义"""

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock

import httpx
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
    apply_redis_mocks,
    create_sqlite_memory_engine,
    create_sqlite_sessionmaker,
)

# 添加src目录到Python路径
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture(scope="session", autouse=True)
def mock_external_services() -> None:
    """在测试阶段统一Mock外部依赖"""

    monkeypatch = MonkeyPatch()
    apply_mlflow_mocks(monkeypatch)
    apply_redis_mocks(monkeypatch)
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
    from src.main import app

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
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
