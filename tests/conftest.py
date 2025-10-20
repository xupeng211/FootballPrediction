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

    # 过滤 Pydantic 弃用警告（主要来自第三方库如MLflow）
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*Support for class-based.*config.*is deprecated.*",
        module=r".*pydantic.*",
    )
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*Pydantic V1 style.*@validator.*validators are deprecated.*",
        module=r".*mlflow.*",
    )
    warnings.filterwarnings(
        "ignore",
        category=DeprecationWarning,
        message=".*Pydantic V1 style.*@root_validator.*validators are deprecated.*",
        module=r".*mlflow.*",
    )

    # 过滤 pytest asyncio 警告
    warnings.filterwarnings(
        "ignore",
        category=pytest.PytestDeprecationWarning,
        message=".*The configuration option.*asyncio_default_fixture_loop_scope.*is unset.*",
    )

    # 设置环境变量
    os.environ["GEVENT_SUPPRESS_RAGWARN"] = "1"


import asyncio
import tempfile
from typing import Any, Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 立即配置警告（在pytest导入后）
configure_warnings()


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
def auth_headers():
    """认证头fixture"""
    return {"Authorization": "Bearer mock_token", "Content-Type": "application/json"}


@pytest.fixture
def mock_prediction_engine():
    """模拟预测引擎fixture"""
    from unittest.mock import MagicMock, AsyncMock

    engine = MagicMock()
    engine.predict = AsyncMock(
        return_value={
            "match_id": 123,
            "home_win_prob": 0.5,
            "draw_prob": 0.3,
            "away_win_prob": 0.2,
            "predicted_outcome": "home",
            "confidence": 0.75,
            "model_version": "v1.0",
        }
    )
    return engine


@pytest.fixture
def sample_user_data():
    """示例用户数据"""
    return {
        "id": 1,
        "username": "testuser",
        "email": "test@example.com",
        "is_active": True,
        "created_at": "2025-01-17T10:00:00Z",
    }


@pytest.fixture
def sample_team_data():
    """示例队伍数据"""
    return {
        "id": 1,
        "name": "Team A",
        "league": "Premier League",
        "country": "England",
        "founded": 1886,
    }


@pytest.fixture
def sample_league_data():
    """示例联赛数据"""
    return {
        "id": 1,
        "name": "Premier League",
        "country": "England",
        "season": "2024-2025",
        "total_teams": 20,
    }


@pytest.fixture
def sample_odds_data():
    """示例赔率数据"""
    return {
        "match_id": 123,
        "home_win": 2.10,
        "draw": 3.40,
        "away_win": 3.20,
        "over_under_2_5": {"over": 1.85, "under": 1.95},
    }


@pytest.fixture
def mock_external_apis():
    """模拟外部API fixture"""
    from unittest.mock import MagicMock

    return {
        "football_api": MagicMock(),
        "odds_api": MagicMock(),
        "weather_api": MagicMock(),
    }


@pytest.fixture
def temp_file():
    """临时文件fixture"""
    import tempfile
    import os

    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)

    yield path

    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def mock_database_session():
    """模拟数据库会话fixture"""
    from unittest.mock import MagicMock
    from sqlalchemy.orm import Session

    session = MagicMock(spec=Session)
    session.commit.return_value = None
    session.rollback.return_value = None
    session.flush.return_value = None

    return session


# === Helper Fixtures ===
@pytest.fixture
def make_prediction_request():
    """创建预测请求的工厂函数"""

    def _make_request(match_id=123, model_version="v1.0", **kwargs):
        data = {
            "match_id": match_id,
            "model_version": model_version,
            "include_details": kwargs.get("include_details", False),
        }
        data.update(kwargs)
        return data

    return _make_request


@pytest.fixture
def make_user_request():
    """创建用户请求的工厂函数"""

    def _make_request(username="testuser", email="test@example.com", **kwargs):
        data = {
            "username": username,
            "email": email,
            "password": kwargs.get("password", "securepassword"),
        }
        data.update(kwargs)
        return data

    return _make_request


# === Performance Fixtures ===
@pytest.fixture
def benchmark_timer():
    """性能计时器fixture"""
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None

        def start(self):
            self.start_time = time.time()

        def stop(self):
            self.end_time = time.time()

        @property
        def elapsed(self):
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0

    return Timer()


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
    monkeypatch.setenv("TESTING", "true")


# === Faker Fixtures ===
@pytest.fixture
def fake_match():
    """生成假比赛数据的fixture"""
    from tests.factories.fake_data import FootballDataFactory

    return FootballDataFactory.match()


@pytest.fixture
def fake_prediction():
    """生成假预测数据的fixture"""
    from tests.factories.fake_data import FootballDataFactory

    return FootballDataFactory.prediction()


@pytest.fixture
def fake_user():
    """生成假用户数据的fixture"""
    from tests.factories.fake_data import FootballDataFactory

    return FootballDataFactory.user()


@pytest.fixture
def fake_team():
    """生成假球队数据的fixture"""
    from tests.factories.fake_data import FootballDataFactory

    return FootballDataFactory.team()


@pytest.fixture
def fake_batch_data():
    """生成批量假数据的fixture工厂"""
    from tests.factories.fake_data import create_batch_fake_data

    def _create_batch(data_type, count=10):
        return create_batch_fake_data(data_type, count)

    return _create_batch


@pytest.fixture
def fake_api_request():
    """生成API假请求数据的fixture工厂"""
    from tests.factories.fake_data import APIDataFactory

    def _create_request(request_type, **kwargs):
        if request_type == "prediction":
            return APIDataFactory.prediction_request()
        elif request_type == "batch_prediction":
            return APIDataFactory.batch_prediction_request(**kwargs)
        elif request_type == "verification":
            return APIDataFactory.verification_request()
        else:
            raise ValueError(f"Unknown request type: {request_type}")

    return _create_request


# === 自动应用Mock ===
@pytest.fixture(autouse=True)
def auto_mock_external_services(monkeypatch):
    """自动Mock外部服务"""
    import sys
    from unittest.mock import MagicMock, AsyncMock

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
def test_match_data():
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
def test_team_data():
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
def test_odds_data():
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
def test_prediction_data():
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


@pytest.fixture
def api_client():
    """HTTP 客户端 fixture"""
    from unittest.mock import AsyncMock, Mock

    # 创建 mock 客户端
    mock_client = AsyncMock()
    mock_client.get.return_value = Mock()
    mock_client.post.return_value = Mock()

    # 设置默认响应
    def setup_response(method):
        method.return_value.status_code = 200
        method.return_value.json.return_value = {"status": "success"}

    setup_response(mock_client.get)
    setup_response(mock_client.post)
    setup_response(mock_client.put)
    setup_response(mock_client.delete)

    return mock_client


@pytest.fixture
def performance_metrics():
    """性能指标收集器 fixture"""
    from collections import defaultdict
    import time

    class PerformanceMetrics:
        def __init__(self):
            self.timers = {}
            self.counters = defaultdict(int)

        def start_timer(self, name):
            self.timers[name] = time.time()

        def end_timer(self, name):
            if name in self.timers:
                duration = time.time() - self.timers[name]
                del self.timers[name]
                return duration
            return 0

        def increment(self, name):
            self.counters[name] += 1

    return PerformanceMetrics()


@pytest.fixture
def test_data_loader():
    """测试数据加载器 fixture"""

    class TestDataLoader:
        def create_teams(self):
            return [
                {"id": 1, "name": "Team A", "short_name": "TA"},
                {"id": 2, "name": "Team B", "short_name": "TB"},
            ]

        def create_matches(self):
            return [
                {
                    "id": 1,
                    "home_team_id": 1,
                    "away_team_id": 2,
                    "match_time": "2024-01-15T20:00:00Z",
                    "status": "upcoming",
                }
            ]

        def create_odds(self, match_id):
            return {
                "match_id": match_id,
                "home_odds": 2.50,
                "draw_odds": 3.20,
                "away_odds": 2.80,
            }

    return TestDataLoader()


# === 配置pytest标记 ===
def pytest_configure(config):
    """配置pytest标记"""
    config.addinivalue_line("markers", "smoke: mark test as a smoke test")
    config.addinivalue_line("markers", "fast: mark test as a fast test")
