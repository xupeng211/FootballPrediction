# TODO: Consider creating a fixture for 21 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock


# TODO: Consider creating a fixture for 21 repeated Mock creations


"""
预加载Mock - 在pytest收集测试之前应用
"""

import os
import sys

# 设置测试环境变量
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "testing"


# 在模块级别应用Mock
def pytest_configure(config):
    """在pytest配置阶段应用Mock"""

    # Mock 数据库连接
    sys.modules["src.database.connection"] = MagicMock()

    # Mock 数据库管理器
    mock_db_manager = MagicMock()
    mock_db_manager.get_async_session.return_value.__aenter__.return_value = AsyncMock()
    mock_db_manager.get_session.return_value.__enter__.return_value = MagicMock()
    sys.modules["src.database.connection"].DatabaseManager = MagicMock(return_value=mock_db_manager)

    # Mock Redis
    try:
        import redis

        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        mock_redis_client.exists.return_value = False
        mock_redis_client.hgetall.return_value = {}
        mock_redis_client.hset.return_value = True

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

    # Mock SQLAlchemy engine
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.pool import StaticPool

        mock_engine = MagicMock()
        mock_engine.connect.return_value.__enter__ = MagicMock()
        mock_engine.connect.return_value.__exit__ = MagicMock()

        # 创建内存数据库引擎
        def mock_create_engine(*args, **kwargs):
            if (
                "sqlite:///:memory:" in str(args)
                or kwargs.get("connect_args", {}).get("check_same_thread") is False
            ):
                # 测试时创建真实的内存数据库
                kwargs.setdefault("poolclass", StaticPool)
                kwargs.setdefault("connect_args", {"check_same_thread": False})
                return create_engine(*args, **kwargs)
            return mock_engine

        # 替换 create_engine
        import sqlalchemy

        sqlalchemy.create_engine = mock_create_engine
    except ImportError:
        pass
