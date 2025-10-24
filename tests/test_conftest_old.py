# TODO: Consider creating a fixture for 51 repeated Mock creations

# TODO: Consider creating a fixture for 51 repeated Mock creations

# TODO: Consider creating a fixture for 51 repeated Mock creations

from unittest.mock import patch, AsyncMock, MagicMock
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
def api_client_full(test_db, test_redis_):
    """完整API客户端fixture（包含数据库和Redis）"""
    from fastapi.testclient import TestClient

    from src.main import app

    with TestClient(app) as client:
        yield client


# === Database Fixtures ===
@pytest.fixture(scope="function")
@pytest.mark.external_api

def test_db(, client):
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
def test_env(monkeypatch, client):
    """设置测试环境变量"""
    monkeypatch.setenv("ENVIRONMENT", "testing")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/1")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("DEBUG", "true")
    monkeypatch.setenv("TESTING", "true")


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

    # Mock 数据库连接
    mock_db_connection = MagicMock()
    mock_db_connection.engine = MagicMock()
    mock_db_connection.engine.pool = MagicMock()
    sys.modules["src.database.connection"] = MagicMock()
    sys.modules["src.database.connection"].DatabaseManager = MagicMock
    sys.modules["src.database.connection"].get_database_url = (
        lambda: "sqlite:///:memory:"
    )

    # Mock Kafka producer
    try:
        mock_kafka_producer = MagicMock()
        mock_kafka_producer.send = MagicMock()
        mock_kafka_producer.flush = MagicMock()
        mock_kafka_producer.close = MagicMock()

        sys.modules["src.streaming.kafka_producer"] = MagicMock()
        sys.modules["src.streaming.kafka_producer"].KafkaProducer = MagicMock
        sys.modules[
            "src.streaming.kafka_producer"
        ].KafkaProducer.return_value = mock_kafka_producer
    except ImportError:
        pass

    # Mock Kafka consumer
    try:
        mock_kafka_consumer = AsyncMock()
        mock_kafka_consumer.poll = AsyncMock(return_value=[])
        mock_kafka_consumer.commit = AsyncMock()
        mock_kafka_consumer.close = AsyncMock()

        sys.modules["src.streaming.kafka_consumer"] = MagicMock()
        sys.modules["src.streaming.kafka_consumer"].KafkaConsumer = MagicMock
        sys.modules[
            "src.streaming.kafka_consumer"
        ].KafkaConsumer.return_value = mock_kafka_consumer
    except ImportError:
        pass

    # Mock MLflow
    try:
        mock_mlflow = MagicMock()
        mock_mlflow.log_metric = MagicMock()
        mock_mlflow.log_param = MagicMock()
        mock_mlflow.log_artifact = MagicMock()
        mock_mlflow.start_run = MagicMock(return_value="test-run-id")
        mock_mlflow.end_run = MagicMock()

        sys.modules["mlflow"] = mock_mlflow
        sys.modules["mlflow.tracking"] = MagicMock()
        sys.modules["mlflow.entities"] = MagicMock()
    except ImportError:
        pass

    # Mock Redis 连接（避免真实连接）
    try:
        import redis

        mock_redis_client = MagicMock()
        mock_redis_client.ping.return_value = True
        mock_redis_client.get.return_value = None
        mock_redis_client.set.return_value = True
        mock_redis_client.exists.return_value = False

        # Mock redis.Redis 构造函数
        def mock_redis_init(*args, **kwargs):
            return mock_redis_client

        redis.Redis = mock_redis_init
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
                return original_create_engine(*args, **kwargs)
            return mock_engine

        # 替换 create_engine
        import sqlalchemy

        sqlalchemy.create_engine = mock_create_engine
    except ImportError:
        pass


# === Database Manager Mock ===
@pytest.fixture(scope="session")
def mock_database_manager():
    """模拟数据库管理器"""
    with patch("src.database.connection.DatabaseManager") as mock:
        # 配置 mock 实例
        mock_instance = AsyncMock()
        mock_instance.get_async_session.return_value.__aenter__.return_value = (
            AsyncMock()
        )
        mock_instance.get_session.return_value.__enter__.return_value = MagicMock()
        mock.return_value = mock_instance
        yield mock


@pytest.fixture
def mock_async_db_session():
    """模拟异步数据库会话"""
    session = AsyncMock()
    session.execute.return_value.fetchone.return_value = None
    session.execute.return_value.fetchall.return_value = []
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.refresh = AsyncMock()
    session.close = AsyncMock()
    session.delete = MagicMock()
    session.query = MagicMock()
    return session


# === Redis Manager Mock ===
@pytest.fixture(scope="session")
def mock_redis_manager():
    """模拟 Redis 管理器"""
    with patch("src.cache.redis_manager.RedisManager") as mock:
        mock_instance = AsyncMock()
        mock_instance.get.return_value = None
        mock_instance.set.return_value = True
        mock_instance.delete.return_value = True
        mock_instance.exists.return_value = False
        mock_instance.expire.return_value = True
        mock_instance.hgetall.return_value = {}
        mock_instance.hset.return_value = True
        mock_instance.ping.return_value = True
        mock.return_value = mock_instance
        yield mock_instance


# === Mock Redis Client ===
@pytest.fixture
def mock_redis_client():
    """模拟 Redis 客户端"""
    client = AsyncMock()
    client.get.return_value = None
    client.set.return_value = True
    client.delete.return_value = True
    client.exists.return_value = False
    client.hgetall.return_value = {}
    client.hset.return_value = True
    client.zadd.return_value = 1
    client.zrange.return_value = []
    client.ping.return_value = True
    client.keys.return_value = []
    return client


# === External API Mocks ===
@pytest.fixture
def mock_football_api():
    """模拟 Football API"""
    with patch("src.collectors.football_api.FootballAPI") as mock:
        api_instance = AsyncMock()
        api_instance.get_matches.return_value = []
        api_instance.get_odds.return_value = []
        api_instance.get_scores.return_value = []
        api_instance.get_live_scores.return_value = []
        mock.return_value = api_instance
        yield api_instance


@pytest.fixture
def mock_api_sports():
    """模拟 API Sports"""
    with patch("src.collectors.api_sports.APISports") as mock:
        api_instance = AsyncMock()
        api_instance.get_fixtures.return_value = []
        api_instance.get_odds.return_value = []
        api_instance.get_live_games.return_value = []
        mock.return_value = api_instance
        yield api_instance


@pytest.fixture
def mock_scorebat_api():
    """模拟 Scorebat API"""
    with patch("src.collectors.scorebat.ScorebatAPI") as mock:
        api_instance = AsyncMock()
        api_instance.get_latest_scores.return_value = []
        api_instance.get_video_highlights.return_value = []
        mock.return_value = api_instance
        yield api_instance


# === Kafka Mocks ===
@pytest.fixture
def mock_kafka_producer():
    """模拟 Kafka 生产者"""
    with patch("src.streaming.kafka.KafkaProducer") as mock:
        producer = AsyncMock()
        producer.send.return_value = None
        producer.flush.return_value = None
        mock.return_value = producer
        yield producer


@pytest.fixture
def mock_kafka_consumer():
    """模拟 Kafka 消费者"""
    with patch("src.streaming.kafka.KafkaConsumer") as mock:
        consumer = AsyncMock()
        consumer.__aiter__.return_value = iter([])
        mock.return_value = consumer
        yield consumer


# === Common Mock Decorators ===
def with_database_mock(func):
    """装饰器：自动应用数据库 mock"""

    def wrapper(*args, **kwargs):
        with patch("src.database.connection.DatabaseManager"):
            return func(*args, **kwargs)

    return wrapper


def with_redis_mock(func):
    """装饰器：自动应用 Redis mock"""

    def wrapper(*args, **kwargs):
        with patch("src.cache.redis_manager.RedisManager"):
            return func(*args, **kwargs)

    return wrapper


def with_external_apis_mock(func):
    """装饰器：自动应用外部 API mock"""

    def wrapper(*args, **kwargs):
        with (
            patch("src.collectors.football_api.FootballAPI"),
            patch("src.collectors.api_sports.APISports"),
            patch("src.collectors.scorebat.ScorebatAPI"),
        ):
            return func(*args, **kwargs)

    return wrapper


# === Test Data Factory ===
@pytest.fixture
def test_match_data(, client):
    """测试用比赛数据"""
    return {
        "id": 12345,
        "home_team_id": 1,
        "away_team_id": 2,
        "home_score": 2,
        "away_score": 1,
        "match_time": "2024-01-15T20:00:00Z",
        "status": "finished",
        "league_id": 101,
        "season": "2023-2024",
    }


@pytest.fixture
def test_team_data(, client):
    """测试用球队数据"""
    return {
        "id": 1,
        "name": "Test Team",
        "short_name": "TT",
        "country": "Test Country",
        "founded": 1900,
        "venue": "Test Stadium",
    }


@pytest.fixture
def test_odds_data(, client):
    """测试用赔率数据"""
    return {
        "id": 54321,
        "match_id": 12345,
        "bookmaker": "TestBookmaker",
        "home_odds": 2.50,
        "draw_odds": 3.20,
        "away_odds": 2.80,
        "collected_at": "2024-01-15T19:00:00Z",
    }


@pytest.fixture
def test_prediction_data(, client):
    """测试用预测数据"""
    return {
        "id": 999,
        "match_id": 12345,
        "model_name": "test_model",
        "prediction": "home_win",
        "confidence": 0.75,
        "home_win_prob": 0.60,
        "draw_prob": 0.25,
        "away_win_prob": 0.15,
        "created_at": "2024-01-15T18:00:00Z",
    }
