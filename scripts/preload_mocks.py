#!/usr/bin/env python3
"""
在 pytest 导入测试之前应用 mocks
"""

import sys
import os
from unittest.mock import MagicMock, AsyncMock

# 设置测试环境
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "testing"

# Mock 数据库连接
sys.modules["src.database.connection"] = MagicMock()

# Mock 数据库管理器
mock_db_manager = MagicMock()
mock_db_manager.get_async_session.return_value.__aenter__.return_value = AsyncMock()
mock_db_manager.get_session.return_value.__enter__.return_value = MagicMock()
sys.modules["src.database.connection"].DatabaseManager = MagicMock(
    return_value=mock_db_manager
)

# Mock Redis
try:
    import redis

    mock_redis_client = MagicMock()
    mock_redis_client.ping.return_value = True
    mock_redis_client.get.return_value = None
    mock_redis_client.set.return_value = True
    mock_redis_client.exists.return_value = False

    original_redis = redis.Redis

    def mock_redis_init(*args, **kwargs):
        return mock_redis_client

    redis.Redis = mock_redis_init
except ImportError:
    pass

# Mock Kafka
sys.modules["src.streaming.kafka_producer"] = MagicMock()
sys.modules["src.streaming.kafka_consumer"] = MagicMock()

# Mock MLflow
mock_mlflow = MagicMock()
mock_mlflow.log_metric = MagicMock()
mock_mlflow.log_param = MagicMock()
mock_mlflow.log_artifact = MagicMock()
mock_mlflow.start_run = MagicMock(return_value="test-run-id")
mock_mlflow.end_run = MagicMock()
sys.modules["mlflow"] = mock_mlflow
sys.modules["mlflow.tracking"] = MagicMock()
sys.modules["mlflow.entities"] = MagicMock()

# Mock HTTP 客户端
mock_requests = MagicMock()
mock_requests.get.return_value.json.return_value = {}
mock_requests.get.return_value.status_code = 200
mock_requests.post.return_value.json.return_value = {}
mock_requests.post.return_value.status_code = 200
sys.modules["requests"] = mock_requests

try:
    mock_httpx = MagicMock()
    mock_httpx.get.return_value.json.return_value = {}
    mock_httpx.get.return_value.status_code = 200
    sys.modules["httpx"] = mock_httpx
except ImportError:
    pass

print("Pre-test mocks applied successfully!")
