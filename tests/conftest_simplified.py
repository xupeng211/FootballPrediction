"""
简化的pytest配置文件
Simplified pytest configuration

遵循最佳实践：
- 最小化mock配置
- 使用精确的patch装饰器
- 保持测试隔离性
"""

import os
import sys
import warnings
import pytest
from unittest.mock import Mock, MagicMock, AsyncMock

# 添加src到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# === 基础配置 ===
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow tests")
    config.addinivalue_line("markers", "fast: Fast tests")
    config.addinivalue_line("markers", "smoke: Smoke tests")
    config.addinivalue_line("markers", "api: API tests")
    config.addinivalue_line("markers", "database: Database tests")


# === 警告配置 ===
def configure_warnings():
    """配置测试期间的警告过滤器"""
    # 过滤已知的安全警告
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*Support for class-based.*config.*is deprecated.*",
        module=r".*pydantic.*",
    )
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message=".*Monkey-patching ssl.*",
    )


# 在导入任何模块之前配置警告
configure_warnings()


# === 简化的Fixtures ===


@pytest.fixture
def mock_database():
    """模拟数据库会话"""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.query = Mock(return_value=Mock())
    session.close = Mock()
    return session


@pytest.fixture
def mock_cache():
    """模拟缓存客户端"""
    cache = Mock()
    cache.get = Mock(return_value=None)
    cache.set = Mock()
    cache.delete = Mock()
    cache.exists = Mock(return_value=False)
    return cache


@pytest.fixture
def mock_logger():
    """模拟日志记录器"""
    logger = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.debug = Mock()
    return logger


@pytest.fixture
def sample_prediction_data():
    """示例预测数据"""
    return {
        "match_id": 123,
        "home_win_prob": 0.5,
        "draw_prob": 0.3,
        "away_win_prob": 0.2,
        "predicted_outcome": "home",
        "confidence": 0.75,
        "model_version": "v1.0",
    }


@pytest.fixture
def sample_match_data():
    """示例比赛数据"""
    return {
        "match_id": 123,
        "home_team": "Team A",
        "away_team": "Team B",
        "home_score": 2,
        "away_score": 1,
        "match_date": "2023-01-01T15:00:00",
        "league": "Test League",
        "status": "completed",
    }


@pytest.fixture
def fastapi_test_client():
    """FastAPI测试客户端"""
    from fastapi.testclient import TestClient
    from src.api.app import app

    return TestClient(app)


# === 测试环境配置 ===
@pytest.fixture(autouse=True)
def test_env(monkeypatch):
    """设置测试环境变量"""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("TESTING", "true")


# === 辅助函数 ===
def create_mock_response(status_code=200, json_data=None):
    """创建模拟HTTP响应"""
    mock = Mock()
    mock.status_code = status_code
    mock.json.return_value = json_data or {}
    mock.text = str(json_data or {})
    mock.raise_for_status.return_value = None
    return mock


def assert_valid_prediction_response(data):
    """验证预测响应格式"""
    required_fields = [
        "match_id",
        "home_win_prob",
        "draw_prob",
        "away_win_prob",
        "predicted_outcome",
        "confidence",
        "model_version",
        "predicted_at",
    ]
    for field in required_fields:
        assert field in data, f"Missing field: {field}"

    # 验证数据有效性
    assert isinstance(data["match_id"], int)
    assert isinstance(data["home_win_prob"], (int, float))
    assert isinstance(data["draw_prob"], (int, float))
    assert isinstance(data["away_win_prob"], (int, float))
    assert data["predicted_outcome"] in ["home", "draw", "away"]
    assert 0 <= data["confidence"] <= 1


# === 测试标记配置 ===
pytest_plugins = ["pytest_asyncio"]


# 异步配置
@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    import asyncio

    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()
