"""服务层测试模板"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from tests.helpers import (
    MockRedis,
    create_sqlite_memory_engine,
    create_sqlite_sessionmaker,
)


class TestPredictionService:
    """预测服务测试"""

    @pytest.fixture
    async def db_session(self):
        """内存数据库会话"""
        engine = create_sqlite_memory_engine()
        sessionmaker = create_sqlite_sessionmaker(engine)
        async with sessionmaker() as session:
            yield session
        engine.dispose()

    @pytest.fixture
    def mock_redis(self):
        """模拟 Redis 客户端"""
        redis_mock = MockRedis()
        redis_mock.set("__ping__", "ok")
        return redis_mock

    @pytest.fixture
    def service(self, db_session, mock_redis):
        """创建服务实例"""
        from src.services.prediction_service import PredictionService
        return PredictionService(db=db_session, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_create_prediction_success(self, service, sample_prediction_data):
        """测试创建预测成功"""
        # 模拟数据库保存
        service.db.add = MagicMock()
        service.db.commit = AsyncMock()
        service.db.refresh = AsyncMock()

        # 模拟Redis缓存
        service.redis.set = AsyncMock(return_value=True)

        result = await service.create_prediction(sample_prediction_data)

        assert result is not None
        assert result["status"] == "success"
        service.db.add.assert_called_once()
        service.db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_prediction_duplicate(self, service, sample_prediction_data):
        """测试创建重复预测"""
        # 模拟已存在预测
        service.redis.get = AsyncMock(return_value=b'{"exists": true}')

        with pytest.raises(ValueError, match="Prediction already exists"):
            await service.create_prediction(sample_prediction_data)

    @pytest.mark.asyncio
    async def test_get_prediction_success(self, service):
        """测试获取预测成功"""
        # 模拟Redis缓存
        service.redis.get = AsyncMock(return_value=b'{"id": 1, "result": "2-1"}')

        result = await service.get_prediction(1)

        assert result is not None
        assert result["id"] == 1
        assert result["result"] == "2-1"

    @pytest.mark.asyncio
    async def test_get_prediction_not_found(self, service):
        """测试获取不存在的预测"""
        # 模拟Redis无数据
        service.redis.get = AsyncMock(return_value=None)

        # 模拟数据库查询
        service.db.execute = AsyncMock()
        service.db.fetch_one = AsyncMock(return_value=None)

        result = await service.get_prediction(999)

        assert result is None

    @pytest.mark.asyncio
    async def test_update_prediction_confidence(self, service):
        """测试更新预测置信度"""
        # 模拟更新操作
        service.db.execute = AsyncMock()
        service.db.commit = AsyncMock()

        result = await service.update_prediction_confidence(1, 0.85)

        assert result is True
        service.db.execute.assert_called_once()
        service.db.commit.assert_called_once()