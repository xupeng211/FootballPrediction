# TODO: Consider creating a fixture for 4 repeated Mock creations

# TODO: Consider creating a fixture for 4 repeated Mock creations

#!/usr/bin/env python3
from unittest.mock import AsyncMock, Mock

"""
测试配置中心 - 增强版
Enhanced Test Configuration Center

提供统一的测试配置管理，包括：
- 测试数据库配置
- Mock服务配置
- 环境变量管理
- 测试工具类
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Generator, Optional

import pytest

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


@pytest.mark.external_api
@pytest.mark.slow
class TestConfig:
    """测试配置管理类"""

    # 测试数据库配置
    TEST_DATABASE_URL = "sqlite:///:memory:"
    TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

    # 测试Redis配置
    TEST_REDIS_URL = "redis://localhost:6379/1"

    # 测试API配置
    TEST_API_KEY = "test_api_key_12345"
    TEST_SECRET_KEY = "test_secret_key_12345"

    # 外部服务配置
    EXTERNAL_API_URL = "http://localhost:8080/api"
    KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

    # 测试标志
    TESTING = True
    DEBUG = True

    @staticmethod
    def setup_full_api_mode():
        """设置完整API模式（启用所有路由）"""
        os.environ["MINIMAL_API_MODE"] = "false"
        os.environ["FAST_FAIL"] = "false"
        os.environ["ENABLE_METRICS"] = "false"
        os.environ["METRICS_ENABLED"] = "false"
        os.environ["ENABLE_FEAST"] = "false"
        os.environ["ENVIRONMENT"] = "test"
        os.environ["ENABLED_SERVICES"] = "[]"
        os.environ["TESTING"] = "true"
        os.environ["MINIMAL_HEALTH_MODE"] = "false"
        os.environ["FAST_FAIL"] = "false"

    @staticmethod
    def setup_minimal_api_mode():
        """设置最小API模式（只启用健康检查）"""
        os.environ["MINIMAL_API_MODE"] = "true"
        os.environ["FAST_FAIL"] = "false"
        os.environ["ENABLE_METRICS"] = "false"
        os.environ["METRICS_ENABLED"] = "false"
        os.environ["ENABLE_FEAST"] = "false"
        os.environ["ENVIRONMENT"] = "test"
        os.environ["ENABLED_SERVICES"] = "[]"
        os.environ["TESTING"] = "true"
        os.environ["MINIMAL_HEALTH_MODE"] = "true"
        os.environ["FAST_FAIL"] = "false"

    @classmethod
    def setup_test_environment(cls):
        """设置完整的测试环境变量"""
        # 基础环境配置
        cls.setup_full_api_mode()

        # 数据库配置
        os.environ["DATABASE_URL"] = cls.TEST_DATABASE_URL
        os.environ["TEST_ASYNC_DATABASE_URL"] = cls.TEST_ASYNC_DATABASE_URL

        # 缓存配置
        os.environ["REDIS_URL"] = cls.TEST_REDIS_URL

        # API配置
        os.environ["TEST_API_KEY"] = cls.TEST_API_KEY
        os.environ["SECRET_KEY"] = cls.TEST_SECRET_KEY

        # 外部服务配置
        os.environ["EXTERNAL_API_URL"] = cls.EXTERNAL_API_URL
        os.environ["KAFKA_BOOTSTRAP_SERVERS"] = cls.KAFKA_BOOTSTRAP_SERVERS

        # 调试配置
        os.environ["DEBUG"] = str(cls.DEBUG)

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """获取当前配置"""
        return {
            "MINIMAL_API_MODE": os.environ.get("MINIMAL_API_MODE", "true"),
            "MINIMAL_HEALTH_MODE": os.environ.get("MINIMAL_HEALTH_MODE", "true"),
            "FAST_FAIL": os.environ.get("FAST_FAIL", "false"),
            "ENABLE_METRICS": os.environ.get("ENABLE_METRICS", "false"),
            "TESTING": os.environ.get("TESTING", "true"),
            "ENVIRONMENT": os.environ.get("ENVIRONMENT", "test"),
            "DATABASE_URL": os.environ.get("DATABASE_URL", "sqlite:///:memory:"),
            "REDIS_URL": os.environ.get("REDIS_URL", "redis://localhost:6379/1"),
        }


class MockServiceRegistry:
    """Mock服务注册表"""

    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._setup_default_services()

    def _setup_default_services(self):
        """设置默认Mock服务"""
        # Mock Redis
        self._services["redis"] = MockRedis()

        # Mock HTTP Client
        self._services["http"] = MockHTTPClient()

        # Mock Kafka
        self._services["kafka_producer"] = MockKafkaProducer()
        self._services["kafka_consumer"] = MockKafkaConsumer()

        # Mock MLflow
        self._services["mlflow"] = MockMlflowClient()

    def get_service(self, service_name: str) -> Any:
        """获取Mock服务"""
        return self._services.get(service_name)

    def register_service(self, service_name: str, service: Any):
        """注册Mock服务"""
        self._services[service_name] = service


class MockRedis:
    """Mock Redis客户端"""

    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._connected = True

    def ping(self) -> bool:
        return self._connected

    def get(self, key: str) -> Optional[bytes]:
        value = self._data.get(key)
        return value.encode() if value else None

    def set(self, key: str, value: Any, ex: Optional[int] = None) -> bool:
        self._data[key] = value
        return True

    def delete(self, key: str) -> int:
        return 1 if self._data.pop(key, None) is not None else 0

    def exists(self, key: str) -> bool:
        return key in self._data

    def keys(self, pattern: str = "*") -> list:
        return [k.encode() for k in self._data.keys()]

    def flushdb(self) -> bool:
        self._data.clear()
        return True

    def info(self) -> Dict[str, Any]:
        return {
            "used_memory": len(str(self._data)),
            "connected_clients": 1,
            "redis_version": "6.0.0",
        }


class MockHTTPClient:
    """Mock HTTP客户端"""

    def __init__(self):
        self.responses: Dict[str, Any] = {}
        self.requests: list = []

    def get(self, url: str, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = Mock()
        response.status_code = 200
        response.json.return_value = self.responses.get(url, {"status": "ok"})
        return response

    def post(self, url: str, **kwargs):
        self.requests.append({"method": "POST", "url": url, **kwargs})
        response = Mock()
        response.status_code = 201
        response.json.return_value = {"status": "created"}
        return response

    async def aget(self, url: str, **kwargs):
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = AsyncMock()
        response.status_code = 200
        response.json.return_value = self.responses.get(url, {"status": "ok"})
        return response


class MockKafkaProducer:
    """Mock Kafka生产者"""

    def __init__(self):
        self.messages: list = []

    def send(self, topic: str, value: bytes, **kwargs):
        self.messages.append({"topic": topic, "value": value, **kwargs})
        future = Mock()
        future.get.return_value = {"topic": topic, "partition": 0, "offset": 123}
        return future

    def flush(self):
        pass

    def close(self):
        pass


class MockKafkaConsumer:
    """Mock Kafka消费者"""

    def __init__(self):
        self.messages: list = []

    def __iter__(self):
        return iter(self.messages)

    def poll(self, timeout_ms: float = 1000) -> Dict[str, list]:
        return {"test_topic": self.messages}


class MockMlflowClient:
    """Mock MLflow客户端"""

    def __init__(self):
        self.experiments: Dict[str, Any] = {}
        self.runs: Dict[str, Any] = {}

    def create_experiment(self, name: str) -> str:
        exp_id = f"exp_{len(self.experiments)}"
        self.experiments[exp_id] = {"name": name, "id": exp_id}
        return exp_id

    def create_run(self, experiment_id: str, run_name: str) -> str:
        run_id = f"run_{len(self.runs)}"
        self.runs[run_id] = {
            "experiment_id": experiment_id,
            "name": run_name,
            "id": run_id,
            "metrics": {},
            "params": {},
        }
        return run_id

    def log_metric(self, run_id: str, key: str, value: float, step: int = 0):
        if run_id in self.runs:
            self.runs[run_id]["metrics"][key] = value

    def log_param(self, run_id: str, key: str, value: str):
        if run_id in self.runs:
            self.runs[run_id]["params"][key] = value


class TestDataFactory:
    """测试数据工厂"""

    @staticmethod
    def create_team_data(**overrides) -> Dict[str, Any]:
        """创建团队测试数据"""
        default_data = {
            "id": 1,
            "name": "Test Team",
            "short_name": "TT",
            "founded_year": 1900,
            "logo_url": "https://example.com/logo.png",
            "country": "Test Country",
            "league": "Test League",
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def create_match_data(**overrides) -> Dict[str, Any]:
        """创建比赛测试数据"""
        default_data = {
            "id": 1,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 0,
            "away_score": 0,
            "match_date": "2024-01-01T15:00:00",
            "venue": "Test Stadium",
            "status": "upcoming",
            "league": "Test League",
        }
        default_data.update(overrides)
        return default_data

    @staticmethod
    def create_prediction_data(**overrides) -> Dict[str, Any]:
        """创建预测测试数据"""
        default_data = {
            "id": 1,
            "match_id": 1,
            "predicted_winner": "home",
            "confidence": 0.75,
            "home_win_probability": 0.60,
            "draw_probability": 0.25,
            "away_win_probability": 0.15,
            "model_version": "v1.0.0",
            "created_at": "2024-01-01T10:00:00",
        }
        default_data.update(overrides)
        return default_data


class TestUtilities:
    """测试工具类"""

    @staticmethod
    def assert_dict_contains(actual: Dict[str, Any], expected: Dict[str, Any]):
        """断言字典包含指定键值对"""
        for key, value in expected.items():
            assert key in actual, f"Key '{key}' not found in dictionary"
            assert actual[key]  == value, f"Expected {key}={value}, got {actual[key]}"

    @staticmethod
    def assert_list_contains(actual: list, expected_items: list):
        """断言列表包含指定元素"""
        for item in expected_items:
            assert item in actual, f"Item '{item}' not found in list"

    @staticmethod
    async def wait_for_condition(
        condition_func, timeout: float = 5.0, interval: float = 0.1
    ):
        """等待条件满足"""
        start_time = asyncio.get_event_loop().time()
        while not condition_func():
            if asyncio.get_event_loop().time() - start_time > timeout:
                raise TimeoutError("Condition not met within timeout")
            await asyncio.sleep(interval)


# 全局测试配置实例
test_config = TestConfig()
mock_registry = MockServiceRegistry()
data_factory = TestDataFactory()
test_utils = TestUtilities()


def setup_test_environment():
    """设置测试环境（便捷函数）"""
    test_config.setup_test_environment()
    return {
        "config": test_config,
        "mocks": mock_registry,
        "data_factory": data_factory,
        "utils": test_utils,
    }
