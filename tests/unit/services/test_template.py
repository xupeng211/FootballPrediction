"""服务层测试模板"""

import pytest
from unittest.mock import patch

from tests.helpers import (
    MockRedis,
    create_sqlite_memory_engine,
    create_sqlite_sessionmaker,
)


class TestExampleService:
    """示例服务测试 - 使用统一 Mock 架构"""

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

    @pytest.fixture(autouse=True)
    async def setup_test_data(self, db_session, mock_redis):
        """准备测试数据"""
        # 可以在这里添加初始化逻辑
        pass

    @pytest.fixture
    def service(self, db_session, mock_redis):
        """创建服务实例"""
        from src.services.example_service import ExampleService
        return ExampleService(db=db_session, redis=mock_redis)

    @pytest.mark.asyncio
    async def test_service_method_success(self, service, db_session, mock_redis):
        """测试服务方法成功"""
        # 模拟依赖
        mock_redis.get.return_value = None
        mock_redis.set.return_value = True

        # 执行测试
        result = await service.method_name()

        # 断言
        assert result is not None
        mock_redis.get.assert_called_once()
        mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_service_method_with_db(self, service, db_session):
        """测试服务方法与数据库交互"""
        # 使用真实的内存数据库会话
        # 不需要 mock，因为使用的是 SQLite 内存数据库

        result = await service.db_method_name()

        assert result is not None

    @pytest.mark.asyncio
    async def test_service_method_error_handling(self, service):
        """测试服务方法错误处理"""
        # 模拟错误情况
        with patch.object(service, 'dependency', side_effect=Exception("Test error")):
            with pytest.raises(Exception, match="Test error"):
                await service.method_name()
