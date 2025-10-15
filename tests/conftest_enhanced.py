"""增强的pytest配置和共享fixtures"""

import asyncio
import os
import sys
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock

import pytest

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, "src")


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "password": "hashed_password",
        "is_active": True,
        "created_at": "2025-01-15T14:30:00Z",
        "updated_at": "2025-01-15T14:30:00Z",
    }


@pytest.fixture
def sample_match_data():
    """示例比赛数据"""
    return {
        "id": 123,
        "home_team": "Team A",
        "away_team": "Team B",
        "home_score": 2,
        "away_score": 1,
        "status": "finished",
        "start_time": "2025-01-15T15:00:00Z",
        "competition": "Premier League",
    }


@pytest.fixture
def sample_prediction_data():
    """示例预测数据"""
    return {
        "id": 456,
        "match_id": 123,
        "predicted_result": "home_win",
        "confidence": 0.75,
        "home_win_prob": 0.65,
        "draw_prob": 0.20,
        "away_win_prob": 0.15,
        "model_name": "v1.0",
        "created_at": "2025-01-15T14:00:00Z",
    }


@pytest.fixture
def mock_database():
    """模拟数据库连接"""
    db = Mock()
    db.connect = Mock()
    db.close = Mock()
    db.execute = Mock()
    db.fetch_one = Mock()
    db.fetch_all = Mock()
    return db


@pytest.fixture
def mock_redis():
    """模拟Redis连接"""
    redis = Mock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=False)
    return redis


@pytest.fixture
def mock_external_api():
    """模拟外部API"""
    api = Mock()
    api.get = AsyncMock()
    api.post = AsyncMock()
    api.put = AsyncMock()
    api.delete = AsyncMock()

    # 模拟响应
    api.get.return_value.json.return_value = {"status": "success", "data": {}}
    return api


@pytest.fixture
def test_config():
    """测试配置"""
    return {
        "database": {"url": "sqlite:///:memory:", "echo": False},
        "redis": {"url": "redis://localhost:6379/0"},
        "api": {"host": "localhost", "port": 8000, "debug": True},
        "security": {
            "secret_key": "test-secret-key",
            "algorithm": "HS256",
            "expire_minutes": 30,
        },
    }


@pytest.fixture
def mock_logger():
    """模拟日志器"""
    logger = Mock()
    logger.debug = Mock()
    logger.info = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.critical = Mock()
    return logger


@pytest.fixture
def sample_csv_data():
    """示例CSV数据"""
    return """id,name,email
1,John Doe,john@example.com
2,Jane Smith,jane@example.com
3,Bob Johnson,bob@example.com"""


@pytest.fixture
def sample_json_data():
    """示例JSON数据"""
    return {
        "users": [
            {"id": 1, "name": "John", "active": True},
            {"id": 2, "name": "Jane", "active": False},
            {"id": 3, "name": "Bob", "active": True},
        ],
        "total": 3,
        "page": 1,
    }


@pytest.fixture
def sample_xml_data():
    """示例XML数据"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<root>
    <user id="1">
        <name>John Doe</name>
        <email>john@example.com</email>
    </user>
</root>"""


@pytest.fixture
def performance_data():
    """性能测试数据"""
    return {
        "small_list": list(range(10)),
        "medium_list": list(range(1000)),
        "large_list": list(range(100000)),
        "small_dict": {f"key_{i}": f"value_{i}" for i in range(10)},
        "medium_dict": {f"key_{i}": f"value_{i}" for i in range(1000)},
        "nested_dict": {"level1": {"level2": {"level3": "deep_value"}}},
    }


@pytest.fixture
def error_scenarios():
    """错误场景数据"""
    return {
        "network_error": ConnectionError("Network unavailable"),
        "timeout_error": TimeoutError("Request timed out"),
        "value_error": ValueError("Invalid value"),
        "key_error": KeyError("Key not found"),
        "type_error": TypeError("Type mismatch"),
        "attribute_error": AttributeError("Attribute not found"),
    }


@pytest.fixture
def boundary_values():
    """边界值测试数据"""
    return {
        "integers": [-1, 0, 1, 2, 255, 256, 1024, 65535, 65536],
        "floats": [-1.0, 0.0, 1.0, 3.14159, 1e10, -1e10],
        "strings": ["", "a", "abc", "a" * 100, "unicode: 你好", "emoji: 😊"],
        "lists": [[], [1], [1, 2], list(range(100))],
        "dicts": [{}, {"a": 1}, {"a": 1, "b": 2}, {str(i): i for i in range(100)}],
    }


# 测试标记
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "performance: Performance tests")
    config.addinivalue_line("markers", "database: Tests requiring database")
    config.addinivalue_line("markers", "redis: Tests requiring Redis")
    config.addinivalue_line("markers", "external_api: Tests calling external APIs")


# 测试收集钩子
def pytest_collection_modifyitems(config, items):
    """修改测试收集"""
    for item in items:
        # 自动标记异步测试
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)

        # 自动标记慢测试
        if "performance" in item.nodeid or "large" in item.nodeid:
            item.add_marker(pytest.mark.slow)


# 测试钩子
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """设置测试环境"""
    # 设置测试环境变量
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")


# 辅助函数
def create_mock_response(data: dict[str, Any], status_code: int = 200):
    """创建模拟HTTP响应"""
    response = Mock()
    response.status_code = status_code
    response.json.return_value = data
    response.text = str(data)
    return response


def create_async_mock_response(data: dict[str, Any], status_code: int = 200):
    """创建异步模拟HTTP响应"""
    response = AsyncMock()
    response.status_code = status_code
    response.json.return_value = data
    response.text = str(data)
    return response


# 性能测试装饰器
def measure_time(func):
    """测量函数执行时间"""

    def wrapper(*args, **kwargs):
        import time

        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        return result, end - start

    return wrapper


# 数据生成器
def generate_test_data(count: int = 10) -> Generator[dict[str, Any], None, None]:
    """生成测试数据"""
    for i in range(count):
        yield {
            "id": i + 1,
            "name": f"Test Item {i + 1}",
            "value": i * 10,
            "active": i % 2 == 0,
        }


# 测试验证器
def assert_valid_uuid(uuid_str: str):
    """验证UUID格式"""
    import uuid

    try:
        uuid.UUID(uuid_str)
    except ValueError:
        pytest.fail(f"Invalid UUID: {uuid_str}")


def assert_valid_email(email: str):
    """验证邮箱格式"""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(pattern, email):
        pytest.fail(f"Invalid email: {email}")


# 测试清理
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """测试后清理"""
    yield
    # 在这里添加清理逻辑
