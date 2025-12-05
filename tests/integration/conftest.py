"""
集成测试配置文件 - 全面增强版
Enhanced Integration Test Configuration

提供集成测试和端到端测试所需的共享fixtures和配置
Enhanced fixtures and configuration for integration and E2E testing
"""

import asyncio
import sys
import tempfile
from collections.abc import AsyncGenerator
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock

# 添加项目根目录到Python路径
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import sessionmaker

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入数据库Base类和模型
try:
    from src.database.base import Base
    from src.database.models.league import League
    from src.database.models.match import Match
    from src.database.models.predictions import Prediction
    from src.database.models.team import Team
except ImportError:
    # 使用SQLAlchemy Base作为后备
    from sqlalchemy.orm import DeclarativeBase

    class Base(DeclarativeBase):
        pass

    Team = None
    Match = None
    Prediction = None
    League = None

# 导入领域模型
try:
    from src.domain.models.prediction import (
        ConfidenceScore,
        PredictionScore,
        PredictionStatus,
    )
except ImportError:
    PredictionScore = None
    ConfidenceScore = None
    PredictionStatus = None


# 测试数据库配置
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
TEST_SYNC_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环用于异步测试"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def test_db_engine():
    """创建异步测试数据库引擎"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

    # 创建所有表
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
def sync_test_db_engine():
    """创建同步测试数据库引擎（用于某些特殊情况）"""
    engine = create_engine(
        TEST_SYNC_DATABASE_URL,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )

    # 创建所有表
    Base.metadata.create_all(engine)

    yield engine

    Base.metadata.drop_all(engine)


@pytest_asyncio.fixture
async def test_db_session(test_db_engine) -> AsyncGenerator[AsyncSession, None]:
    """创建测试数据库会话"""
    async_session = async_sessionmaker(
        test_db_engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session


@pytest.fixture
def sync_test_db_session(sync_test_db_engine):
    """创建同步测试数据库会话"""
    session_factory = sessionmaker(bind=sync_test_db_engine)
    session = session_factory()

    yield session

    session.close()


@pytest.fixture
def app():
    """创建FastAPI应用实例"""
    try:
        from src.api.app import app as main_app

        return main_app
    except ImportError:
        # 创建一个最小的FastAPI应用用于测试
        from fastapi import FastAPI

        return FastAPI()


@pytest.fixture
def test_client(app):
    """创建FastAPI测试客户端"""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """创建异步HTTP客户端"""
    try:
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    except TypeError:
        # 如果AsyncClient API不同，使用备用方法

        client = TestClient(app)

        # 创建一个简单的包装器
        class AsyncClientWrapper:
            def __init__(self, test_client):
                self.client = test_client

            async def get(self, url, **kwargs):
                return self.client.get(url, **kwargs)

            async def post(self, url, **kwargs):
                return self.client.post(url, **kwargs)

            async def put(self, url, **kwargs):
                return self.client.put(url, **kwargs)

            async def delete(self, url, **kwargs):
                return self.client.delete(url, **kwargs)

        yield AsyncClientWrapper(client)


# 增强的测试数据fixtures
@pytest_asyncio.fixture
async def sample_league(test_db_session: AsyncSession):
    """创建示例联赛数据"""
    if not League:
        pytest.skip("League model not available")

    # League是dataclass，不是SQLAlchemy模型，不需要数据库操作
    league = League(
        name="Premier League",
        country="England",
        is_active=True,
    )

    return league


@pytest_asyncio.fixture
async def sample_teams(test_db_session: AsyncSession, sample_league):
    """创建示例球队数据"""
    if not Team:
        pytest.skip("Team model not available")

    # Team是dataclass，不是SQLAlchemy模型，不需要数据库操作
    teams = [
        Team(
            name="Manchester United",
            short_name="MUN",
            country="England",
            founded_year=1878,
        ),
        Team(
            name="Liverpool",
            short_name="LIV",
            country="England",
            founded_year=1892,
        ),
        Team(
            name="Chelsea",
            short_name="CHE",
            country="England",
            founded_year=1905,
        ),
        Team(
            name="Arsenal",
            short_name="ARS",
            country="England",
            founded_year=1886,
        ),
    ]

    return teams


@pytest_asyncio.fixture
async def sample_match(test_db_session: AsyncSession, sample_teams):
    """创建示例比赛数据"""
    if not Match or not sample_teams:
        pytest.skip("Match model or teams not available")

    _home_team, _away_team = sample_teams[0], sample_teams[1]

    # 创建Match对象
    match = Match(
        home_team_id=1,  # 简化测试ID
        away_team_id=2,
        league_id=39,  # Premier League ID
        season="2024-2025",
        match_date=datetime.utcnow() + timedelta(days=1),
        venue="Old Trafford",
    )

    # 保存到数据库
    test_db_session.add(match)
    await test_db_session.commit()
    await test_db_session.refresh(match)

    return match


@pytest_asyncio.fixture
async def sample_predictions(test_db_session: AsyncSession, sample_match):
    """创建示例预测数据"""
    if not Prediction:
        pytest.skip("Prediction model not available")

    # 使用简化的预测数据，不依赖数据库
    predictions = [
        Prediction(
            id=101,
            user_id=1,
            match_id=(
                sample_match.home_team_id
                if hasattr(sample_match, "home_team_id")
                else 1
            ),
            score=PredictionScore(predicted_home=2, predicted_away=1),
            confidence=ConfidenceScore(value=Decimal("0.75")),
            status=PredictionStatus.PENDING,
        ),
        Prediction(
            id=102,
            user_id=2,
            match_id=(
                sample_match.away_team_id
                if hasattr(sample_match, "away_team_id")
                else 2
            ),
            score=PredictionScore(predicted_home=1, predicted_away=2),
            confidence=ConfidenceScore(value=Decimal("0.65")),
            status=PredictionStatus.PENDING,
        ),
        Prediction(
            id=103,
            user_id=3,
            match_id=(
                sample_match.league_id if hasattr(sample_match, "league_id") else 39
            ),
            score=PredictionScore(
                predicted_home=1, predicted_away=1, actual_home=2, actual_away=1
            ),
            confidence=ConfidenceScore(value=Decimal("0.60")),
            status=PredictionStatus.EVALUATED,
        ),
    ]

    # 为已评估的预测设置比分
    if hasattr(predictions[2], "make_prediction") and hasattr(
        predictions[2], "evaluate"
    ):
        try:
            predictions[2].make_prediction(
                predicted_home=2, predicted_away=1, confidence=0.85
            )
            predictions[2].evaluate(actual_home=2, actual_away=1)
        except Exception:
            # 如果领域方法不可用，手动设置属性
            predictions[2].predicted_home = 2
            predictions[2].predicted_away = 1
            predictions[2].actual_home = 2
            predictions[2].actual_away = 1
            predictions[2].confidence = 0.85

    # Prediction是领域模型，不是SQLAlchemy模型，不需要数据库操作
    # 直接返回预测对象用于测试
    return predictions


@pytest.fixture
def auth_headers():
    """认证头信息"""
    return {"Authorization": "Bearer test_token"}


@pytest.fixture
def access_token():
    """认证访问令牌fixture"""
    return "mock_test_access_token_12345"


@pytest_asyncio.fixture
async def sample_data(sample_teams, sample_match, sample_predictions):
    """数据库测试示例数据fixture"""
    """提供集成测试所需的示例数据结构"""
    return {
        "teams": sample_teams,
        "match": sample_match,
        "predictions": sample_predictions,
    }


@pytest.fixture
def training_data():
    """机器学习训练数据fixture"""
    """提供ML模型训练所需的示例数据"""
    return {
        "matches": [
            {
                "id": 1,
                "home_team": "Manchester United",
                "away_team": "Liverpool",
                "home_score": 2,
                "away_score": 1,
                "date": "2024-01-15",
            },
            {
                "id": 2,
                "home_team": "Chelsea",
                "away_team": "Arsenal",
                "home_score": 0,
                "away_score": 0,
                "date": "2024-01-16",
            },
            {
                "id": 3,
                "home_team": "Manchester City",
                "away_team": "Tottenham",
                "home_score": 3,
                "away_score": 1,
                "date": "2024-01-17",
            },
            {
                "id": 4,
                "home_team": "Barcelona",
                "away_team": "Real Madrid",
                "home_score": 1,
                "away_score": 2,
                "date": "2024-01-18",
            },
            {
                "id": 5,
                "home_team": "Bayern Munich",
                "away_team": "PSG",
                "home_score": 4,
                "away_score": 2,
                "date": "2024-01-19",
            },
        ],
        "features": [
            {
                "match_id": 1,
                "home_strength": 0.85,
                "away_strength": 0.78,
                "home_form": 0.9,
                "away_form": 0.7,
                "h2h_home_advantage": 0.6,
            },
            {
                "match_id": 2,
                "home_strength": 0.82,
                "away_strength": 0.80,
                "home_form": 0.6,
                "away_form": 0.8,
                "h2h_home_advantage": 0.5,
            },
            {
                "match_id": 3,
                "home_strength": 0.90,
                "away_strength": 0.75,
                "home_form": 0.95,
                "away_form": 0.65,
                "h2h_home_advantage": 0.7,
            },
            {
                "match_id": 4,
                "home_strength": 0.88,
                "away_strength": 0.92,
                "home_form": 0.7,
                "away_form": 0.85,
                "h2h_home_advantage": 0.4,
            },
            {
                "match_id": 5,
                "home_strength": 0.93,
                "away_strength": 0.81,
                "home_form": 0.88,
                "away_form": 0.72,
                "h2h_home_advantage": 0.65,
            },
        ],
        "targets": [
            {"match_id": 1, "result": "home_win", "home_goals": 2, "away_goals": 1},
            {"match_id": 2, "result": "draw", "home_goals": 0, "away_goals": 0},
            {"match_id": 3, "result": "home_win", "home_goals": 3, "away_goals": 1},
            {"match_id": 4, "result": "away_win", "home_goals": 1, "away_goals": 2},
            {"match_id": 5, "result": "home_win", "home_goals": 4, "away_goals": 2},
        ],
    }


@pytest.fixture
def admin_headers():
    """管理员认证头信息"""
    return {"Authorization": "Bearer admin_token"}


@pytest.fixture
def mock_external_api_responses():
    """模拟外部API响应"""
    return {
        "football_api": {
            "match_data": {
                "id": 12345,
                "home_team": {"name": "Manchester United", "id": 1},
                "away_team": {"name": "Liverpool", "id": 2},
                "score": {"home": 0, "away": 0},
                "status": "SCHEDULED",
                "match_date": "2024-12-01T20:00:00Z",
            }
        },
        "odds_api": {
            "match_odds": {
                "match_id": 12345,
                "home_win": 2.10,
                "draw": 3.40,
                "away_win": 3.20,
                "over_2_5": 1.85,
                "under_2_5": 1.95,
            }
        },
        "user_api": {
            "user_data": {
                "id": 123,
                "username": "testuser",
                "email": "test@example.com",
                "is_active": True,
                "role": "user",
            }
        },
    }


@pytest.fixture
def performance_benchmarks():
    """性能测试基准数据"""
    return {
        "response_time_limits": {
            "health_check": 0.1,  # 100ms
            "prediction_creation": 0.5,  # 500ms
            "prediction_retrieval": 0.2,  # 200ms
            "bulk_predictions": 2.0,  # 2s
            "user_registration": 0.3,  # 300ms
            "data_sync": 5.0,  # 5s
        },
        "throughput_limits": {
            "requests_per_second": 100,
            "concurrent_users": 50,
            "bulk_prediction_size": 1000,
        },
        "memory_limits": {
            "max_memory_mb": 512,
            "memory_leak_threshold_mb": 50,
        },
    }


@pytest.fixture
def test_user_data():
    """测试用户数据"""
    return {
        "users": [
            {
                "id": 1,
                "username": "testuser1",
                "email": "user1@test.com",
                "is_active": True,
                "role": "user",
                "created_at": datetime.utcnow() - timedelta(days=30),
            },
            {
                "id": 2,
                "username": "testuser2",
                "email": "user2@test.com",
                "is_active": True,
                "role": "user",
                "created_at": datetime.utcnow() - timedelta(days=20),
            },
            {
                "id": 3,
                "username": "adminuser",
                "email": "admin@test.com",
                "is_active": True,
                "role": "admin",
                "created_at": datetime.utcnow() - timedelta(days=60),
            },
            {
                "id": 4,
                "username": "inactiveuser",
                "email": "inactive@test.com",
                "is_active": False,
                "role": "user",
                "created_at": datetime.utcnow() - timedelta(days=10),
            },
        ]
    }


@pytest.fixture
def temp_directory():
    """临时目录fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def mock_redis():
    """增强的模拟Redis客户端"""
    redis_mock = AsyncMock()
    redis_mock.ping.return_value = True
    redis_mock.get.return_value = None
    redis_mock.set.return_value = True
    redis_mock.delete.return_value = 1
    redis_mock.exists.return_value = False
    redis_mock.expire.return_value = True
    redis_mock.hget.return_value = None
    redis_mock.hset.return_value = True
    redis_mock.hgetall.return_value = {}
    redis_mock.incr.return_value = 1
    redis_mock.decr.return_value = 0
    return redis_mock


@pytest.fixture
def cache_test_data():
    """缓存测试数据"""
    return {
        "prediction_cache_key": "prediction:user_123:match_456",
        "user_stats_key": "user_stats:123",
        "match_stats_key": "match_stats:456",
        "session_key": "session:abc123",
        "ttl_seconds": 3600,
        "test_value": {
            "predicted_home": 2,
            "predicted_away": 1,
            "confidence": 0.85,
            "created_at": datetime.utcnow().isoformat(),
        },
    }


@pytest.fixture
def mock_external_services():
    """模拟外部服务"""
    services = {
        "notification_service": AsyncMock(),
        "email_service": AsyncMock(),
        "analytics_service": AsyncMock(),
        "payment_service": AsyncMock(),
        "audit_service": AsyncMock(),
    }

    # 设置默认返回值
    services["notification_service"].send_notification.return_value = {"status": "sent"}
    services["email_service"].send_email.return_value = {"status": "delivered"}
    services["analytics_service"].track_event.return_value = {"status": "recorded"}
    services["payment_service"].process_payment.return_value = {"status": "success"}
    services["audit_service"].log_event.return_value = {"status": "logged"}

    return services


@pytest.fixture
def bulk_test_data():
    """批量测试数据"""
    return {
        "bulk_predictions": [
            {
                "user_id": i,
                "match_id": i + 1000,
                "predicted_home": (i % 5) + 1,
                "predicted_away": (i % 3) + 1,
                "confidence": 0.5 + (i % 5) * 0.1,
            }
            for i in range(1, 101)  # 100个预测
        ],
        "bulk_users": [
            {
                "username": f"user{i}",
                "email": f"user{i}@test.com",
                "is_active": i % 10 != 0,  # 10%的用户不活跃
            }
            for i in range(1, 51)  # 50个用户
        ],
        "bulk_matches": [
            {
                "home_team_id": (i % 20) + 1,
                "away_team_id": ((i + 1) % 20) + 1,
                "match_date": datetime.utcnow() + timedelta(days=i),
                "status": "SCHEDULED",
            }
            for i in range(1, 51)  # 50场比赛
        ],
    }


@pytest.fixture
def error_test_data():
    """错误测试数据"""
    return {
        "invalid_predictions": [
            {"user_id": -1, "match_id": 1},  # 无效用户ID
            {"user_id": 1, "match_id": -1},  # 无效比赛ID
            {"predicted_home": -1, "predicted_away": 1},  # 无效比分
            {"predicted_home": 1, "predicted_away": -1},  # 无效比分
            {"confidence": 1.5},  # 超出范围的置信度
            {"confidence": -0.1},  # 超出范围的置信度
        ],
        "network_errors": [
            "timeout",
            "connection_refused",
            "dns_resolution_failed",
            "ssl_error",
        ],
        "database_errors": [
            "connection_timeout",
            "constraint_violation",
            "deadlock",
            "query_timeout",
        ],
    }


# V23.0 修复：移除全局自动清理，避免死锁
# 将清理操作改为手动标记，避免单元测试触发数据库初始化
@pytest_asyncio.fixture
async def cleanup_test_data(test_db_session: AsyncSession):
    """手动测试数据清理fixture - 不再自动使用"""
    yield

    try:
        # 确保数据库连接仍然有效
        if test_db_session and not test_db_session.closed:
            # 清理所有表
            for table in reversed(Base.metadata.sorted_tables):
                await test_db_session.execute(text(f"DELETE FROM {table.name}"))
            await test_db_session.commit()
    except Exception as e:
        # 记录错误但不阻塞测试
        import warnings

        warnings.warn(f"Cleanup failed: {e}", UserWarning, stacklevel=2)
    finally:
        # 确保会话关闭
        try:
            if test_db_session and not test_db_session.closed:
                await test_db_session.close()
        except Exception:
            pass


# 标记定义
def pytest_configure(config):
    """配置自定义标记"""
    markers = [
        ("integration: 集成测试"),
        ("e2e: 端到端测试"),
        ("api: API测试"),
        ("domain: 领域层测试"),
        ("services: 服务层测试"),
        ("database: 数据库测试"),
        ("cache: 缓存测试"),
        ("performance: 性能测试"),
        ("slow: 慢速测试"),
        ("auth: 认证测试"),
        ("bulk: 批量操作测试"),
        ("error: 错误处理测试"),
        ("security: 安全测试"),
        ("workflow: 业务流程测试"),
    ]

    for marker in markers:
        config.addinivalue_line("markers", marker)
