from typing import Any
"""
集成测试配置文件
提供数据库、Redis,Kafka 等集成测试的共享 fixtures
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import pytest

# 加载测试环境配置
test_env_path = Path(__file__).parent.parent.parent / ".env.test"
if test_env_path.exists():
    with open(test_env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ[key.strip()] = value.strip()

# SQLAlchemy imports
try:
    from sqlalchemy.ext.asyncio import AsyncSession
except ImportError:
    AsyncSession = None

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
sys.path.insert(0, "src")

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 测试环境配置
os.environ["TESTING"] = "true"
os.environ["TEST_ENV"] = "integration"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db():
    """测试数据库 fixture"""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from sqlalchemy.orm import sessionmaker

    # 数据库配置
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/football_prediction",
    )

    # 调试输出
    logger.info(f"Database URL: {database_url}")

    # 创建引擎
    engine = create_async_engine(
        database_url,
        echo=False,
        pool_pre_ping=True,
        pool_recycle=3600,
    )

    # 创建会话工厂
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    # 等待数据库就绪
    max_retries = 30
    for i in range(max_retries):
        try:
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            break
            except Exception:
            if i == max_retries - 1:
                raise
            logger.info(f"Waiting for database... ({i + 1}/{max_retries})")
            await asyncio.sleep(2)

    # 创建表（如果不存在）
    from src.database.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield async_session

    # 清理
    await engine.dispose()


@pytest.fixture
async def db_session(test_db) -> AsyncGenerator[Any, None]:
    """数据库会话 fixture"""
    async with test_db() as session:
        yield session
        await session.rollback()


@pytest.fixture(scope="session")
async def test_redis():
    """Redis fixture"""
    try:
        import redis.asyncio as redis

        redis_url = os.getenv("REDIS_URL", "redis://:test_pass@localhost:6380/1")

        # 创建 Redis 客户端
        client = redis.from_url(redis_url, decode_responses=True)

        # 等待 Redis 就绪
        max_retries = 30
        for i in range(max_retries):
            try:
                await client.ping()
                break
            except Exception:
                if i == max_retries - 1:
                    raise
                logger.info(f"Waiting for Redis... ({i + 1}/{max_retries})")
                await asyncio.sleep(1)

        # 清空测试数据库
        await client.flushdb()

        yield client

        # 清理
        await client.flushdb()
        await client.close()

    except ImportError:
        logger.warning("Redis not available, using mock")
        from unittest.mock import AsyncMock

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.get = AsyncMock(return_value=None)
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.setex = AsyncMock(return_value=True)
        mock_redis.delete = AsyncMock(return_value=1)
        mock_redis.flushdb = AsyncMock(return_value=True)
        mock_redis.close = AsyncMock()

        yield mock_redis


@pytest.fixture(scope="session")
async def test_kafka():
    """Kafka fixture"""
    try:

        from kafka.errors import KafkaError

        # Kafka 配置
        bootstrap_servers = os.getenv("KAFKA_BROKER", "localhost:9093")
        topic_prefix = os.getenv("KAFKA_TOPIC_PREFIX", "test_")

        # 等待 Kafka 就绪
        max_retries = 30
        for i in range(max_retries):
            try:
                admin_client = KafkaAdminClient(
                    bootstrap_servers=bootstrap_servers, client_id="test-admin"
                )
                admin_client.list_topics()
                admin_client.close()
                break
            except Exception:
                if i == max_retries - 1:
                    raise
                logger.info(f"Waiting for Kafka... ({i + 1}/{max_retries})")
                await asyncio.sleep(2)

        # 创建测试主题
        test_topics = [
            f"{topic_prefix}predictions",
            f"{topic_prefix}matches",
            f"{topic_prefix}audit_logs",
        ]

        admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers, client_id="test-admin")

        from kafka.admin import NewTopic

        new_topics = [
            NewTopic(name=topic, num_partitions=3, replication_factor=1) for topic in test_topics
        ]

        try:
            admin_client.create_topics(new_topics, validate_only=False)
        except KafkaError as e:
            if "TopicAlreadyExistsError" not in str(e):
                raise

        # 创建生产者和消费者
        producer = KafkaProducer(
            bootstrap_servers=bootstrap_servers,
            client_id="test-producer",
            value_serializer=lambda v: v.encode() if isinstance(v, str) else v,
            key_serializer=lambda k: k.encode() if isinstance(k, str) else k,
        )

        yield {
            "producer": producer,
            "admin_client": admin_client,
            "topics": test_topics,
            "bootstrap_servers": bootstrap_servers,
        }

        # 清理
        producer.close()
        admin_client.close()

    except ImportError:
        logger.warning("Kafka not available, using mock")
        from unittest.mock import MagicMock

        mock_producer = MagicMock()
        mock_producer.send = MagicMock(return_value=MagicMock(get=MagicMock(return_value=None)))
        mock_producer.flush = MagicMock()
        mock_producer.close = MagicMock()

        mock_admin = MagicMock()

        yield {
            "producer": mock_producer,
            "admin_client": mock_admin,
            "topics": ["test_predictions", "test_matches", "test_audit_logs"],
            "bootstrap_servers": "localhost:9093",
        }


@pytest.fixture
async def api_client():
    """API 测试客户端 fixture"""
    from httpx import AsyncClient

    from src.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
async def test_user_token(api_client):
    """创建测试用户并获取 token"""
    # 创建测试用户
    user_data = {
        "username": "test_integration_user",
        "email": "test_integration@example.com",
        "password": "test_pass_123",
    }

    # 注册用户
    response = await api_client.post("/api/v1/auth/register", json=user_data)
    if response.status_code == 201:
        # 登录获取 token
        login_data = {
            "username": user_data["username"],
            "password": user_data["password"],
        }
        response = await api_client.post("/api/v1/auth/login", _data=login_data)
        if response.status_code == 200:
            return response.json()["access_token"]

    # 如果注册失败,尝试直接登录
    login_data = {"username": user_data["username"], "password": user_data["password"]}
    response = await api_client.post("/api/v1/auth/login", _data=login_data)
    if response.status_code == 200:
        return response.json()["access_token"]

    # 如果都失败,返回模拟 token
    return "mock_test_token"


@pytest.fixture
async def auth_headers(test_user_token):
    """认证头 fixture"""
    return {"Authorization": f"Bearer {test_user_token}"}


@pytest.fixture
async def sample_match_data(db_session):
    """创建示例比赛数据"""
    from src.database.models import Match, Team

    # 创建队伍
    home_team = Team(name="Test Home Team", city="Test City", founded=2000)
    away_team = Team(name="Test Away Team", city="Test City", founded=2001)

    db_session.add(home_team)
    db_session.add(away_team)
    await db_session.commit()
    await db_session.refresh(home_team)
    await db_session.refresh(away_team)

    # 创建比赛
    match = Match(
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        match_date="2025-01-20T20:00:00Z",
        status="UPCOMING",
        competition="Test League",
        season="2024/2025",
    )

    db_session.add(match)
    await db_session.commit()
    await db_session.refresh(match)

    return {
        "match": match,
        "home_team": home_team,
        "away_team": away_team,
    }


@pytest.fixture
async def sample_prediction_data(db_session, sample_match_data):
    """创建示例预测数据"""
    from src.database.models import Prediction, User

    # 创建用户
    _user = User(
        username="test_predictor",
        email="predictor@example.com",
        password_hash="hashed_password",
        role="user",
    )

    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # 创建预测
    _prediction = Prediction(
        user_id=user.id,
        match_id=sample_match_data["match"].id,
        _prediction="HOME_WIN",
        confidence=0.75,
        created_at="2025-01-15T10:00:00Z",
    )

    db_session.add(prediction)
    await db_session.commit()
    await db_session.refresh(prediction)

    return {
        "user": user,
        "prediction": prediction,
    }


# 清理 fixture
@pytest.fixture(autouse=True)
async def cleanup_data(db_session):
    """自动清理测试数据"""
    yield

    # 清理数据（按依赖关系顺序）
    from sqlalchemy import text

    # 使用原始 SQL 清理更快
    await db_session.execute(text("TRUNCATE TABLE predictions RESTART IDENTITY CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE matches RESTART IDENTITY CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE teams RESTART IDENTITY CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE"))
    await db_session.execute(text("TRUNCATE TABLE audit_logs RESTART IDENTITY CASCADE"))
    await db_session.commit()
