"""
pytest配置文件
"""

import os
import sys
import warnings


# 配置警告过滤器 - 必须在其他导入之前
def configure_warnings():
    """配置测试期间的警告过滤器"""

    # 过滤 MonkeyPatchWarning (来自 locust/gevent)
    try:
        from gevent import monkey

        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            message=".*Monkey-patching ssl after ssl has already been imported.*",
        )
    except ImportError:
        pass

    # 过滤 DeprecationWarning
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*直接从 error_handler 导入已弃用.*",
    )

    # 过滤 RuntimeWarning 来自 optional.py
    warnings.filterwarnings(
        "ignore",
        category=RuntimeWarning,
        message=".*导入.*时发生意外错误.*",
        module=r"src\.dependencies\.optional",
    )

    # 设置环境变量
    os.environ["GEVENT_SUPPRESS_RAGWARN"] = "1"


# 立即配置警告
configure_warnings()

import asyncio
import tempfile
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# 设置异步测试模式
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# === Mock Fixtures ===
@pytest.fixture
def mock_redis() -> MagicMock:
    """Mock Redis客户端"""
    redis = MagicMock()
    redis.get.return_value = None
    redis.set.return_value = True
    redis.exists.return_value = False
    return redis


@pytest.fixture
def mock_db_session() -> MagicMock:
    """Mock数据库会话"""
    session = MagicMock()
    session.commit.return_value = None
    session.rollback.return_value = None
    session.close.return_value = None
    return session


@pytest.fixture
def mock_cache() -> MagicMock:
    """Mock缓存"""
    cache = MagicMock()
    cache.get.return_value = None
    cache.set.return_value = True
    cache.delete.return_value = True
    return cache


@pytest.fixture
def mock_logger() -> MagicMock:
    """Mock日志器"""
    logger = MagicMock()
    return logger


# === Test Data Fixtures ===
@pytest.fixture
def sample_match_data() -> dict:
    """示例比赛数据"""
    return {
        "id": 1,
        "home_team": "Team A",
        "away_team": "Team B",
        "date": "2024-01-01",
        "time": "15:00",
        "venue": "Stadium",
        "status": "upcoming",
    }


@pytest.fixture
def sample_prediction_data() -> dict:
    """示例预测数据"""
    return {
        "id": 1,
        "match_id": 1,
        "user_id": 1,
        "home_score": 2,
        "away_score": 1,
        "confidence": 0.85,
    }


# === API Test Fixtures ===
@pytest.fixture
def api_client():
    """API客户端fixture"""
    from fastapi.testclient import TestClient

    from src.api.app import app

    return TestClient(app)


@pytest.fixture
def api_client_full(test_db, test_redis_client):
    """完整API客户端fixture（包含数据库和Redis）"""
    from fastapi.testclient import TestClient

    from src.main import app

    with TestClient(app) as client:
        yield client


# === Database Fixtures ===
@pytest.fixture(scope="function")
def test_db():
    """测试数据库fixture"""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from src.database.base import Base

    # 创建内存数据库
    engine = create_engine("sqlite:///:memory:")

    # 创建表
    Base.metadata.create_all(engine)

    # 创建会话工厂
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    yield TestingSessionLocal

    # 清理
    Base.metadata.drop_all(engine)


# === 环境配置 ===
@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    """设置测试环境变量"""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DEBUG", "true")


# === 自动应用Mock ===
@pytest.fixture(autouse=True)
def auto_mock_external_services(monkeypatch):
    """自动Mock外部服务"""
    import sys

    # Mock requests
    mock_requests = MagicMock()
    mock_requests.get.return_value.json.return_value = {}
    mock_requests.get.return_value.status_code = 200

    # 创建requests模块的mock
    requests_mock = MagicMock()
    requests_mock.get = mock_requests.get
    requests_mock.post = mock_requests.post
    requests_mock.__version__ = "2.28.0"

    # 使用sys.modules来mock整个模块
    sys.modules["requests"] = requests_mock

    # Mock HTTP客户端（如果有）
    try:
        import httpx

        mock_httpx = MagicMock()
        mock_httpx.get.return_value.json.return_value = {}
        mock_httpx.get.return_value.status_code = 200
        sys.modules["httpx"] = mock_httpx
    except ImportError:
        pass
