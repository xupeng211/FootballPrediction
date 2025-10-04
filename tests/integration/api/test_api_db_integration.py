"""集成测试模板"""

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker


@pytest.mark.integration
class TestAPIIntegration:
    """API集成测试"""

    @pytest.fixture
    async def test_db(self):
        """测试数据库连接"""

        engine = create_async_engine(
            "sqlite+aiosqlite:///:memory:",
            echo=False
        )

        # 创建表
        from src.database.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        yield engine
        await engine.dispose()

    @pytest.fixture
    async def db_session(self, test_db):
        """数据库会话"""
        async_session = sessionmaker(
            test_db, class_=AsyncSession, expire_on_commit=False
        )

        async with async_session() as session:
            yield session

    async def test_create_user_and_prediction_flow(self, async_client, db_session):
        """测试创建用户和预测的完整流程"""
        # 1. 创建用户
        user_data = {
            "email": "integration@test.com",
            "username": "integration_user",
            "password": "TestPass123!"
        }

        response = await async_client.post("/api/users", json=user_data)
        assert response.status_code == 201
        user_id = response.json()["id"]

        # 2. 用户登录
        login_data = {
            "username": "integration_user",
            "password": "TestPass123!"
        }

        response = await async_client.post("/api/auth/login", json=login_data)
        assert response.status_code == 200
        token = response.json()["access_token"]

        # 3. 创建预测
        headers = {"Authorization": f"Bearer {token}"}
        prediction_data = {
            "match_id": 54321,
            "home_team": "Integration Team A",
            "away_team": "Integration Team B",
            "predicted_home_score": 2,
            "predicted_away_score": 1
        }

        response = await async_client.post(
            "/api/predictions",
            json=prediction_data,
            headers=headers
        )
        assert response.status_code == 201
        prediction_id = response.json()["id"]

        # 4. 获取预测
        response = await async_client.get(
            f"/api/predictions/{prediction_id}",
            headers=headers
        )
        assert response.status_code == 200
        assert response.json()["id"] == prediction_id

        # 5. 验证数据库中的数据
        from src.database.models import User, Prediction
        result = await db_session.get(User, user_id)
        assert result is not None
        assert result.email == "integration@test.com"

        result = await db_session.get(Prediction, prediction_id)
        assert result is not None
        assert result.match_id == 54321


@pytest.mark.integration
@pytest.mark.slow
class TestCacheIntegration:
    """缓存集成测试"""

    async def test_prediction_caching(self, async_client, mock_redis):
        """测试预测缓存"""
        # 模拟Redis
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        # 创建预测
        prediction_data = {
            "match_id": 12345,
            "home_team": "Cache Test A",
            "away_team": "Cache Test B",
            "predicted_home_score": 3,
            "predicted_away_score": 1
        }

        response = await async_client.post("/api/predictions", json=prediction_data)
        assert response.status_code == 201

        # 验证缓存设置
        mock_redis.set.assert_called()

        # 再次获取预测
        mock_redis.get.return_value = b'{"id": 1, "result": "3-1"}'

        response = await async_client.get("/api/predictions/1")
        assert response.status_code == 200
