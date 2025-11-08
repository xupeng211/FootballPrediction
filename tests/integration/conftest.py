"""
集成测试配置
Integration Tests Configuration

提供集成测试所需的fixture和配置。
"""

import asyncio
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.database.models import Base
from src.main import app


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine():
    """创建测试数据库引擎"""
    # 使用内存SQLite数据库进行测试
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        future=True,
    )

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def test_client():
    """创建测试客户端"""
    return TestClient(app)


@pytest.fixture
def mock_redis():
    """模拟Redis客户端"""
    redis_mock = MagicMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    redis_mock.expire.return_value = True
    return redis_mock


@pytest.fixture
def mock_settings():
    """模拟设置"""
    settings = MagicMock()
    settings.DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    settings.REDIS_URL = "redis://localhost:6379/0"
    settings.SECRET_KEY = "test-secret-key"
    settings.DEBUG = True
    return settings


@pytest.fixture
async def sample_data(test_db_session: AsyncSession):
    """创建测试数据"""
    from src.database.models import Match, Team

    # 创建测试球队
    teams = [
        Team(
            name="Test Team A",
            short_name="TTA",
            country="Test Country",
            founded_year=2020,
        ),
        Team(
            name="Test Team B",
            short_name="TTB",
            country="Test Country",
            founded_year=2021,
        ),
    ]

    for team in teams:
        test_db_session.add(team)

    await test_db_session.commit()

    # 创建测试比赛
    from datetime import datetime

    match = Match(
        home_team_id=teams[0].id,
        away_team_id=teams[1].id,
        home_score=0,
        away_score=0,
        match_date=datetime(2024, 1, 15, 15, 0, 0),
        league="Test League",
        status="upcoming",
        venue="Test Stadium",
    )

    test_db_session.add(match)
    await test_db_session.commit()

    # 重新获取以确保有ID
    await test_db_session.refresh(match)
    for team in teams:
        await test_db_session.refresh(team)

    return {"teams": teams, "match": match}


@pytest.fixture
def override_db_dependency(test_db_session: AsyncSession):
    """覆盖数据库依赖"""

    async def get_test_db():
        yield test_db_session

    return get_test_db


# 集成测试标记
pytest.mark.integration = pytest.mark.integration
pytest.mark.api_integration = pytest.mark.integration
pytest.mark.db_integration = pytest.mark.integration
pytest.mark.cache_integration = pytest.mark.integration
