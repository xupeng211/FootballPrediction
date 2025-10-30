# TODO: Consider creating a fixture for 28 repeated Mock creations

# TODO: Consider creating a fixture for 28 repeated Mock creations


""""""""
Mock配置文件
处理所有导入错误和模块依赖问题
""""""""

import sys
from pathlib import Path

import pytest

# 添加项目路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


# 在收集测试之前设置所有Mock
def pytest_configure(config):
    """pytest配置钩子,在测试开始前设置Mock"""

    # Mock所有可能有问题的外部依赖
    external_deps = [
        "redis",
        "redis.client",
        "redis.connection",
        "psycopg2",
        "psycopg2.extensions",
        "psycopg2.extras",
        "asyncpg",
        "sqlalchemy.dialects.postgresql",
        "sqlalchemy.dialects.postgresql.psycopg2",
        "sqlalchemy.dialects.postgresql.asyncpg",
        "kafka",
        "kafka.consumer",
        "kafka.producer",
        "confluent_kafka",
        "mlflow",
        "mlflow.tracking",
        "mlflow.sklearn",
        "prometheus_client",
        "prometheus_client.collector",
        "prometheus_client.metrics",
        "feast",
        "feast.feature_store",
        "feast.repo_config",
        "great_expectations",
        "great_expectations.dataset",
        "great_expectations.core",
        "celery",
        "celery.app",
        "celery.task",
        "testcontainers",
        "testcontainers.postgres",
        "testcontainers.kafka",
    ]

    for dep in external_deps:
        sys.modules[dep] = Mock()

    # Mock FastAPI相关
    try:
    except ImportError:
        sys.modules["fastapi"] = Mock()
        sys.modules["fastapi.app"] = Mock()

    # 创建一些通用的Mock实例
    mock_db_session = Mock()
    mock_db_session.add = Mock()
    mock_db_session.commit = Mock()
    mock_db_session.rollback = Mock()
    mock_db_session.query = Mock(return_value=Mock())
    mock_db_session.execute = Mock(return_value=Mock())

    # 创建Mock的数据库引擎
    mock_engine = Mock()
    mock_engine.connect = Mock(return_value=Mock())
    mock_engine.execute = Mock(return_value=Mock())

    # 创建Mock的Redis客户端
    mock_redis = Mock()
    mock_redis.get = Mock(return_value=None)
    mock_redis.set = Mock(return_value=True)
    mock_redis.delete = Mock(return_value=True)
    mock_redis.exists = Mock(return_value=False)

    # 创建Mock的Kafka客户端
    mock_kafka_producer = Mock()
    mock_kafka_producer.send = Mock(return_value=Mock())
    mock_kafka_producer.flush = Mock(return_value=None)

    mock_kafka_consumer = Mock()
    mock_kafka_consumer.subscribe = Mock()
    mock_kafka_consumer.poll = Mock(return_value=[])

    # 将Mock添加到sys.modules以便其他模块导入
    sys.modules["mock_db_session"] = mock_db_session
    sys.modules["mock_engine"] = mock_engine
    sys.modules["mock_redis"] = mock_redis
    sys.modules["mock_kafka_producer"] = mock_kafka_producer
    sys.modules["mock_kafka_consumer"] = mock_kafka_consumer


@pytest.fixture(scope="session")
def mock_settings():
    """全局Mock设置"""
    return {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/0",
        "kafka_bootstrap_servers": ["localhost:9092"],
        "environment": "test",
    }


@pytest.fixture
def mock_request():
    """Mock FastAPI请求对象"""
    request = Mock()
    request.url = Mock()
    request.url.path = "/test"
    request.method = "GET"
    request.headers = {"content-type": "application/json"}
    return request


@pytest.fixture
def mock_user():
    """Mock用户对象"""
    user = Mock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture
def mock_match():
    """Mock比赛对象"""
    match = Mock()
    match.id = 1
    match.home_team_id = 1
    match.away_team_id = 2
    match.home_score = 2
    match.away_score = 1
    match.status = "FINISHED"
    match.match_date = "2025-01-20T15:00:00Z"
    return match


@pytest.fixture
def mock_prediction():
    """Mock预测对象"""
    prediction = Mock()
    prediction.id = 1
    prediction.user_id = 1
    prediction.match_id = 1
    prediction.predicted_result = "HOME_WIN"
    prediction.confidence = 0.85
    prediction.actual_result = "HOME_WIN"
    prediction.is_correct = True
    return prediction


@pytest.fixture
def sample_data():
    """示例测试数据"""
    return {
        "teams": [
            {"id": 1, "name": "Team A", "short_name": "TA"},
            {"id": 2, "name": "Team B", "short_name": "TB"},
        ],
        "matches": [
            {
                "id": 1,
                "home_team_id": 1,
                "away_team_id": 2,
                "date": "2025-01-20",
                "status": "SCHEDULED",
            }
        ],
        "predictions": [
            {
                "id": 1,
                "match_id": 1,
                "user_id": 1,
                "prediction": "HOME_WIN",
                "confidence": 0.75,
            }
        ],
    }
