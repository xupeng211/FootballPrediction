"""
外部依赖统一mock模块

为集成测试提供统一的外部服务mock，避免依赖真实的外部服务：
- Redis
- Kafka
- MLflow
- Feast
- Prometheus
- Great Expectations
- MinIO

使用方法：
    from tests.external_mocks import *
    # 或者使用pytest fixtures:
    def test_something(mock_redis_manager, mock_mlflow_client):
        # 使用mock进行测试
"""

from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch

import pytest


# Redis Mocks
class MockRedisManager:
    """Redis管理器Mock"""

    def __init__(self):
        self._sync_client = Mock()
        self._async_client = AsyncMock()
        self._cache_data = {}

    async def aget(self, key: str):
        """异步获取值"""
        return self._cache_data.get(key)

    async def aset(self, key: str, value: Any, expire: Optional[int] = None):
        """异步设置值"""
        self._cache_data[key] = value
        return True

    async def aexists(self, key: str) -> bool:
        """异步检查键是否存在"""
        return key in self._cache_data

    async def adelete(self, key: str):
        """异步删除键"""
        if key in self._cache_data:
            del self._cache_data[key]
        return True

    async def aping(self) -> bool:
        """异步ping"""
        return True

    async def aclose(self):
        """异步关闭连接"""


class MockRedisClient:
    """Redis客户端Mock"""

    def __init__(self):
        self.data = {}

    def get(self, key: str):
        return self.data.get(key)

    def set(self, key: str, value: Any, ex: Optional[int] = None):
        self.data[key] = value
        return True

    def exists(self, key: str) -> bool:
        return key in self.data

    def delete(self, key: str):
        if key in self.data:
            del self.data[key]
        return True

    def ping(self) -> bool:
        return True


# MLflow Mocks
class MockMLflowClient:
    """MLflow客户端Mock"""

    def __init__(self):
        self.models = {}
        self.experiments = {}
        self.runs = {}

    def create_experiment(self, name: str):
        self.experiments[name] = {"name": name, "id": len(self.experiments) + 1}
        return self.experiments[name]["id"]

    def log_model(self, run_id: str, artifact_path: str, model: Any):
        self.models[run_id] = {"artifact_path": artifact_path, "model": model}

    def log_param(self, run_id: str, key: str, value: Any):
        if run_id not in self.runs:
            self.runs[run_id] = {}
        if "params" not in self.runs[run_id]:
            self.runs[run_id]["params"] = {}
        self.runs[run_id]["params"][key] = value

    def log_metric(
        self, run_id: str, key: str, value: float, step: Optional[int] = None
    ):
        if run_id not in self.runs:
            self.runs[run_id] = {}
        if "metrics" not in self.runs[run_id]:
            self.runs[run_id]["metrics"] = {}
        self.runs[run_id]["metrics"][key] = value

    def create_run(self, experiment_id: int, run_name: str):
        run_id = f"run_{len(self.runs) + 1}"
        self.runs[run_id] = {
            "experiment_id": experiment_id,
            "run_name": run_name,
            "params": {},
            "metrics": {},
        }
        return run_id

    def set_terminated(self, run_id: str):
        if run_id in self.runs:
            self.runs[run_id]["status"] = "FINISHED"


class MockMLflowTrackingClient:
    """MLflow跟踪客户端Mock"""

    def __init__(self):
        self.client = MockMLflowClient()

    def search_experiments(self, **kwargs):
        return [
            {"name": name, "id": info["id"]}
            for name, info in self.client.experiments.items()
        ]

    def get_experiment_by_name(self, name: str):
        if name in self.client.experiments:
            return self.client.experiments[name]
        return None


# Kafka Mocks
class MockKafkaProducer:
    """Kafka生产者Mock"""

    def __init__(self):
        self.messages = []
        self.connected = True

    async def send(self, topic: str, value: Any, key: Optional[Any] = None):
        self.messages.append({"topic": topic, "value": value, "key": key})
        return Mock()

    async def start(self):
        self.connected = True

    async def stop(self):
        self.connected = False

    async def flush(self):
        pass


class MockKafkaConsumer:
    """Kafka消费者Mock"""

    def __init__(self):
        self.messages = []
        self.current_offset = 0

    async def start(self):
        pass

    async def stop(self):
        pass

    async def getmany(self, *args, **kwargs):
        if self.current_offset < len(self.messages):
            return {Mock(): [self.messages[self.current_offset]]}
        return {}

    def add_message(self, message: Any):
        self.messages.append(message)


# Feast Mocks
class MockFeatureStore:
    """Feast特征存储Mock"""

    def __init__(self):
        self.features = {}
        self.feature_views = {}

    def get_historical_features(self, entity_df: Any, features: list):
        """获取历史特征"""
        return Mock()

    def get_online_features(self, features: list, entity_rows: list):
        """获取在线特征"""
        result = Mock()
        result.to_dict.return_value = {feature: 0.5 for feature in features}
        return result

    def materialize_incremental(self, end_date: Any):
        """增量物化特征"""
        return True

    def write_to_online_store(self, feature_view_name: str, df: Any):
        """写入在线存储"""
        return True


# Prometheus Mocks
class MockPrometheusRegistry:
    """Prometheus注册表Mock"""

    def __init__(self):
        self.metrics = {}

    def register(self, metric: Any):
        self.metrics[metric._name] = metric

    def unregister(self, metric: Any):
        if metric._name in self.metrics:
            del self.metrics[metric._name]

    def collect(self):
        return list(self.metrics.values())


class MockCounter:
    """Prometheus计数器Mock"""

    def __init__(
        self, name: str, documentation: str, labelnames: Optional[list] = None
    ):
        self._name = name
        self._documentation = documentation
        self._labelnames = labelnames or []
        self._value = 0.0
        self._values: Dict[Any, float] = {}

    def inc(self, amount: float = 1.0, **labels):
        if labels:
            key = tuple(sorted(labels.items()))
            if key not in self._values:
                self._values[key] = 0.0
            self._values[key] += amount
        else:
            self._value += amount

    def labels(self, **labels):
        return MockChildCounter(self, labels)

    def get_value(self):
        return sum(self._values.values()) if self._values else self._value


class MockChildCounter:
    """带标签的Prometheus计数器Mock"""

    def __init__(self, parent: MockCounter, labels: dict):
        self._parent = parent
        self._labels = labels

    def inc(self, amount: float = 1.0):
        self._parent.inc(amount, **self._labels)


class MockGauge:
    """Prometheus仪表Mock"""

    def __init__(
        self, name: str, documentation: str, labelnames: Optional[list] = None
    ):
        self._name = name
        self._documentation = documentation
        self._labelnames = labelnames or []
        self._value = 0.0
        self._values: Dict[Any, float] = {}

    def set(self, value: float, **labels):
        if labels:
            key = tuple(sorted(labels.items()))
            self._values[key] = value
        else:
            self._value = value

    def inc(self, amount: float = 1.0, **labels):
        if labels:
            key = tuple(sorted(labels.items()))
            current = self._values.get(key, 0.0)
            self._values[key] = current + amount
        else:
            self._value += amount

    def dec(self, amount: float = 1.0, **labels):
        if labels:
            key = tuple(sorted(labels.items()))
            current = self._values.get(key, 0.0)
            self._values[key] = current - amount
        else:
            self._value -= amount

    def labels(self, **labels):
        return MockChildGauge(self, labels)

    def get_value(self):
        return list(self._values.values())[0] if self._values else self._value


class MockChildGauge:
    """带标签的Prometheus仪表Mock"""

    def __init__(self, parent: MockGauge, labels: dict):
        self._parent = parent
        self._labels = labels

    def set(self, value: float):
        self._parent.set(value, **self._labels)

    def inc(self, amount: float = 1.0):
        self._parent.inc(amount, **self._labels)

    def dec(self, amount: float = 1.0):
        self._parent.dec(amount, **self._labels)


class MockHistogram:
    """Prometheus直方图Mock"""

    def __init__(
        self, name: str, documentation: str, labelnames: Optional[list] = None
    ):
        self._name = name
        self._documentation = documentation
        self._labelnames = labelnames or []
        self._observations: List[Dict[str, Any]] = []

    def observe(self, value: float, **labels):
        self._observations.append({"value": value, "labels": labels})

    def labels(self, **labels):
        return MockChildHistogram(self, labels)


class MockChildHistogram:
    """带标签的Prometheus直方图Mock"""

    def __init__(self, parent: MockHistogram, labels: dict):
        self._parent = parent
        self._labels = labels

    def observe(self, value: float):
        self._parent.observe(value, **self._labels)


# Great Expectations Mocks
class MockGreatExpectationsDataContext:
    """Great Expectations数据上下文Mock"""

    def __init__(self):
        self.validations = []
        self.expectation_suites = {}

    def get_expectation_suite(self, suite_name: str):
        if suite_name not in self.expectation_suites:
            self.expectation_suites[suite_name] = Mock()
        return self.expectation_suites[suite_name]

    def run_validation(self, expectation_suite: Any, batch: Any):
        result = Mock()
        result.success = True
        result.statistics = {"evaluated_expectations": 5, "successful_expectations": 5}
        return result


# MinIO Mocks
class MockMinioClient:
    """MinIO客户端Mock"""

    def __init__(self):
        self.buckets = {}
        self.objects = {}

    def make_bucket(self, bucket_name: str):
        if bucket_name not in self.buckets:
            self.buckets[bucket_name] = []

    def put_object(self, bucket_name: str, object_name: str, data: Any, length: int):
        if bucket_name in self.buckets:
            self.buckets[bucket_name].append(object_name)
            self.objects[f"{bucket_name}/{object_name}"] = data

    def get_object(self, bucket_name: str, object_name: str):
        key = f"{bucket_name}/{object_name}"
        if key in self.objects:
            return Mock(data=self.objects[key])
        return None

    def bucket_exists(self, bucket_name: str) -> bool:
        return bucket_name in self.buckets

    def stat_object(self, bucket_name: str, object_name: str):
        key = f"{bucket_name}/{object_name}"
        if key in self.objects:
            return Mock(size=len(str(self.objects[key])))
        return None


# Database Mocks
class MockDatabaseManager:
    """数据库管理器Mock"""

    def __init__(self):
        self._session = Mock()
        self._async_session = AsyncMock()

    def get_session(self):
        return self._session

    def get_async_session(self):
        return self._async_session

    def initialize(self):
        pass


# Pytest Fixtures
@pytest.fixture
def mock_redis_manager():
    """Redis管理器Mock fixture"""
    return MockRedisManager()


@pytest.fixture
def mock_redis_client():
    """Redis客户端Mock fixture"""
    return MockRedisClient()


@pytest.fixture
def mock_mlflow_client():
    """MLflow客户端Mock fixture"""
    return MockMLflowClient()


@pytest.fixture
def mock_mlflow_tracking_client():
    """MLflow跟踪客户端Mock fixture"""
    return MockMLflowTrackingClient()


@pytest.fixture
def mock_kafka_producer():
    """Kafka生产者Mock fixture"""
    return MockKafkaProducer()


@pytest.fixture
def mock_kafka_consumer():
    """Kafka消费者Mock fixture"""
    return MockKafkaConsumer()


@pytest.fixture
def mock_feature_store():
    """Feast特征存储Mock fixture"""
    return MockFeatureStore()


@pytest.fixture
def mock_prometheus_registry():
    """Prometheus注册表Mock fixture"""
    return MockPrometheusRegistry()


@pytest.fixture
def mock_counter():
    """Prometheus计数器Mock fixture"""
    return MockCounter("test_counter", "Test counter")


@pytest.fixture
def mock_gauge():
    """Prometheus仪表Mock fixture"""
    return MockGauge("test_gauge", "Test gauge")


@pytest.fixture
def mock_histogram():
    """Prometheus直方图Mock fixture"""
    return MockHistogram("test_histogram", "Test histogram")


@pytest.fixture
def mock_gx_context():
    """Great Expectations数据上下文Mock fixture"""
    return MockGreatExpectationsDataContext()


@pytest.fixture
def mock_minio_client():
    """MinIO客户端Mock fixture"""
    return MockMinioClient()


@pytest.fixture
def mock_database_manager():
    """数据库管理器Mock fixture"""
    return MockDatabaseManager()


# Patches for common imports
@pytest.fixture(autouse=True)
def patch_external_dependencies():
    """自动patch外部依赖"""
    patches = [
        patch("src.cache.redis_manager.RedisManager", MockRedisManager),
        patch("src.streaming.kafka_manager.KafkaProducer", MockKafkaProducer),
        patch("src.streaming.kafka_manager.KafkaConsumer", MockKafkaConsumer),
        patch("src.features.feature_store.FootballFeatureStore", MockFeatureStore),
        patch("mlflow.client.MlflowClient", MockMLflowClient),
        patch("mlflow.tracking.MlflowClient", MockMLflowTrackingClient),
        patch("prometheus_client.Counter", MockCounter),
        patch("prometheus_client.Gauge", MockGauge),
        patch("prometheus_client.Histogram", MockHistogram),
        patch("prometheus_client.CollectorRegistry", MockPrometheusRegistry),
    ]

    for p in patches:
        p.start()

    yield

    for p in patches:
        p.stop()


# Utility functions
def create_mock_async_session():
    """创建异步数据库会话Mock"""
    session = AsyncMock()
    session.execute.return_value.scalar.return_value = 1
    session.execute.return_value.scalar_one_or_none.return_value = 1
    session.execute.return_value.fetchall.return_value = []
    session.commit.return_value = None
    session.rollback.return_value = None
    return session


def create_mock_sync_session():
    """创建同步数据库会话Mock"""
    session = Mock()
    session.execute.return_value.scalar.return_value = 1
    session.execute.return_value.scalar_one_or_none.return_value = 1
    session.execute.return_value.fetchall.return_value = []
    session.commit.return_value = None
    session.rollback.return_value = None
    return session


# Context manager for temporary mocking
class ExternalDependencyMockContext:
    """外部依赖Mock上下文管理器"""

    def __init__(self):
        self.patches = []

    def __enter__(self):
        # 启动所有patches
        patches = [
            patch("src.cache.redis_manager.RedisManager", MockRedisManager),
            patch("src.streaming.kafka_manager.KafkaProducer", MockKafkaProducer),
            patch("src.streaming.kafka_manager.KafkaConsumer", MockKafkaConsumer),
            patch("src.features.feature_store.FootballFeatureStore", MockFeatureStore),
            patch("mlflow.client.MlflowClient", MockMLflowClient),
            patch("mlflow.tracking.MlflowClient", MockMLflowTrackingClient),
            patch("prometheus_client.Counter", MockCounter),
            patch("prometheus_client.Gauge", MockGauge),
            patch("prometheus_client.Histogram", MockHistogram),
            patch("prometheus_client.CollectorRegistry", MockPrometheusRegistry),
        ]

        for p in patches:
            self.patches.append(p.start())

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 停止所有patches
        for p in self.patches:
            p.stop()


# Global instance for convenience
mock_context = ExternalDependencyMockContext()
