"""
TestContainers集成配置文件
提供容器化的测试环境
"""

import os
import sys
from pathlib import Path

# 添加src到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tests.factories.base import BaseFactory

# 尝试导入TestContainers
try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer

    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False


@pytest.fixture(scope="session")
def postgres_container():
    """
    PostgreSQL测试容器
    如果TestContainers不可用，跳过测试
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("TestContainers not available")

    with PostgresContainer(
        image="postgres:15-alpine",
        dbname="football_prediction_test",
        username="test_user",
        password="test_password",
        port=5432,
    ) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def redis_container():
    """
    Redis测试容器
    如果TestContainers不可用，跳过测试
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("TestContainers not available")

    with RedisContainer(image="redis:7-alpine", port=6379) as redis:
        yield redis


@pytest.fixture(scope="session")
@pytest.mark.docker

def test_database_engine(postgres_container, client):
    """
    测试数据库引擎
    基于TestContainers的PostgreSQL实例
    """
    # 获取容器连接URL
    database_url = postgres_container.get_connection_url()

    # 创建数据库引擎
    engine = create_engine(database_url, echo=True)

    # 创建所有表
    from src.database.base import Base
    from src.database import models as _models  # noqa: F401 保证模型注册

    Base.metadata.create_all(engine)

    yield engine

    # 清理
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db_session(test_database_engine, client):
    """
    测试数据库会话
    每个测试函数都有一个独立的会话
    """
    Session = sessionmaker(bind=test_database_engine)
    session = Session()

    def _bind_session(factory_cls, bound_session):
        stack = [factory_cls]
        visited = set()
        while stack:
            cls = stack.pop()
            if cls in visited:
                continue
            visited.add(cls)
            cls._meta.sqlalchemy_session = bound_session
            stack.extend(cls.__subclasses__())

    try:
        _bind_session(BaseFactory, session)
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        _bind_session(BaseFactory, None)
        session.close()


@pytest.fixture(scope="function")
def test_redis_client(redis_container, client):
    """
    测试Redis客户端
    基于TestContainers的Redis实例
    """
    import redis

    # 获取Redis连接信息
    redis_port = redis_container.get_exposed_port(6379)

    # 创建Redis客户端
    client = redis.Redis(
        host="localhost",
        port=redis_port,
        db=1,  # 使用测试数据库
        decode_responses=True,
    )

    # 清空测试数据库
    client.flushdb()

    yield client

    # 清理
    client.flushdb()
    client.close()


@pytest.fixture(scope="function", autouse=True)
def setup_container_environment(postgres_container, redis_container):
    """
    自动设置容器环境变量
    这个fixture会自动应用于所有使用容器的测试
    """
    # 设置数据库环境变量
    database_url = postgres_container.get_connection_url()
    redis_port = redis_container.get_exposed_port(6379)
    redis_url = f"redis://localhost:{redis_port}/1"

    os.environ["DATABASE_URL"] = database_url
    os.environ["TEST_DATABASE_URL"] = database_url
    os.environ["REDIS_URL"] = redis_url
    os.environ["TEST_REDIS_URL"] = redis_url

    # 设置测试环境
    os.environ["TESTING"] = "true"
    os.environ["ENVIRONMENT"] = "test"

    yield

    # 清理环境变量
    for key in ["DATABASE_URL", "TEST_DATABASE_URL", "REDIS_URL", "TEST_REDIS_URL"]:
        os.environ.pop(key, None)


@pytest.fixture(scope="function")
def sample_test_data(test_db_session):
    """
    创建示例测试数据
    """
    from src.database.models.team import Team
    from src.database.models.league import League
    from src.database.models.match import Match

    # 创建联赛
    league = League(league_name="Test League", country="Test Country")
    test_db_session.add(league)
    test_db_session.flush()

    # 创建球队
    home_team = Team(name="Home Team", short_name="HT", country="Test Country")
    away_team = Team(name="Away Team", short_name="AT", country="Test Country")
    test_db_session.add_all([home_team, away_team])
    test_db_session.flush()

    # 创建比赛
    match = Match(
        league_id=league.id,
        home_team_id=home_team.id,
        away_team_id=away_team.id,
        match_date="2024-01-01 15:00:00",
        status="SCHEDULED",
    )
    test_db_session.add(match)
    test_db_session.commit()

    return {
        "league": league,
        "home_team": home_team,
        "away_team": away_team,
        "match": match,
    }


# 跳过标记
def pytest_runtest_setup(item):
    """测试前的设置"""
    # 检查是否需要TestContainers
    if (
        "postgres_container" in item.fixturenames
        or "redis_container" in item.fixturenames
    ):
        if not TESTCONTAINERS_AVAILABLE:
            pytest.skip(
                "TestContainers not available - install with: pip install testcontainers"
            )

    # 检查Docker是否运行
    if (
        "postgres_container" in item.fixturenames
        or "redis_container" in item.fixturenames
    ):
        import subprocess

        try:
            subprocess.run(["docker", "info"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            pytest.skip("Docker not available or not running")
