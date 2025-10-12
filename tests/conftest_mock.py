"""
测试Mock配置文件 - 在conftest.py加载之前生效
"""

import sys
import os

# 确保测试环境设置
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "testing"

# 在导入任何测试之前应用Mock
from unittest.mock import MagicMock, AsyncMock

# Mock 数据库连接模块
db_mock = MagicMock()
sys.modules["src.database.connection"] = db_mock

# Mock DatabaseManager
mock_db_manager = AsyncMock()
mock_async_session = AsyncMock()
mock_async_session.execute = AsyncMock(return_value=MagicMock())
mock_async_session.__aenter__ = AsyncMock(return_value=mock_async_session)
mock_async_session.__aexit__ = AsyncMock(return_value=None)
mock_db_manager.get_async_session.return_value = mock_async_session

mock_sync_session = MagicMock()
mock_sync_session.execute = MagicMock(return_value=MagicMock())
mock_sync_session.__enter__ = MagicMock(return_value=mock_sync_session)
mock_sync_session.__exit__ = MagicMock(return_value=None)
mock_db_manager.get_session.return_value = mock_sync_session

db_mock.DatabaseManager = MagicMock(return_value=mock_db_manager)

# Mock Redis
try:
    # 完全替换redis模块
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.exists.return_value = False
    redis_mock.hgetall.return_value = {}
    redis_mock.hset.return_value = True
    redis_mock.Redis.return_value = redis_mock

    sys.modules["redis"] = redis_mock
except ImportError:
    pass

# Mock Kafka
kafka_producer_mock = MagicMock()
kafka_consumer_mock = AsyncMock()
kafka_consumer_mock.__aiter__ = AsyncMock(return_value=iter([]))

sys.modules["src.streaming.kafka_producer"] = MagicMock()
sys.modules["src.streaming.kafka_producer"].KafkaProducer = MagicMock(
    return_value=kafka_producer_mock
)
sys.modules["src.streaming.kafka_consumer"] = MagicMock()
sys.modules["src.streaming.kafka_consumer"].KafkaConsumer = MagicMock(
    return_value=kafka_consumer_mock
)

# Mock MLflow
mlflow_mock = MagicMock()
mlflow_mock.log_metric = MagicMock()
mlflow_mock.log_param = MagicMock()
mlflow_mock.log_artifact = MagicMock()
mlflow_mock.start_run = MagicMock(return_value="test-run-id")
mlflow_mock.end_run = MagicMock()
sys.modules["mlflow"] = mlflow_mock
sys.modules["mlflow.tracking"] = MagicMock()
sys.modules["mlflow.entities"] = MagicMock()

# Mock requests
requests_mock = MagicMock()
requests_mock.get.return_value.json.return_value = {}
requests_mock.get.return_value.status_code = 200
requests_mock.post.return_value.json.return_value = {}
requests_mock.post.return_value.status_code = 200
sys.modules["requests"] = requests_mock

# Mock httpx if available
try:
    httpx_mock = MagicMock()
    httpx_mock.get.return_value.json.return_value = {}
    httpx_mock.get.return_value.status_code = 200
    sys.modules["httpx"] = httpx_mock
except ImportError:
    pass

print("Mocks applied successfully in conftest_mock.py")
