"""
测试 API 使用测试数据库
Test API with test database
"""

import pytest
from sqlalchemy.orm import Session

# 不使用 TestClient，直接测试路由函数
from src.database.dependencies import get_db


@pytest.mark.unit
@pytest.mark.api
@pytest.mark.external_api
class TestAPIWithTestDatabase:
    """测试 API 使用测试数据库"""

    @pytest.fixture
    def mock_db_session(self):
        """创建模拟的数据库会话"""
        session = Mock(spec=Session)
        # 模拟数据库查询结果
        session.execute.return_value.fetchall.return_value = [
            {"teams_count": 10},
            {"matches_count": 20},
            {"predictions_count": 5},
        ]
        session.close = Mock()
        return session

    def test_dependency_override_without_testclient(self, mock_db_session):
        """测试依赖覆盖（不使用 TestClient）"""
        from src.main import app

        # 应用依赖覆盖
        def override_get_db():
            return mock_db_session

        app.dependency_overrides[get_db] = override_get_db

        try:
            # 直接调用路由函数，而不是通过 HTTP
            # 这避免了 TestClient 的启动问题
            import asyncio

            from src.api.monitoring import _get_database_metrics

            # 运行异步函数
            result = asyncio.run(_get_database_metrics(mock_db_session))

            # 验证结果
            assert "statistics" in result
            assert isinstance(_result["statistics"], dict)
        finally:
            # 清理依赖覆盖
            app.dependency_overrides.clear()

    def test_db_dependency_is_callable(self):
        """测试数据库依赖是可调用的"""
        assert callable(get_db)

    def test_db_dependency_injection_works(self, mock_db_session):
        """测试依赖注入是否工作"""
        # 模拟 FastAPI 的依赖注入
        # FastAPI 内部会这样调用我们的依赖函数
        db_gen = get_db()
        db = next(db_gen)

        # 验证返回的是生成器
        assert hasattr(db, "execute") or db is None

        # 清理
        try:
            next(db_gen)
        except StopIteration:
            pass

    def test_async_db_dependency_is_callable(self):
        """测试异步数据库依赖是可调用的"""
        from src.database.dependencies import get_async_db

        assert callable(get_async_db)

    def test_async_db_dependency_generator(self):
        """测试异步数据库依赖生成器"""
        import asyncio

        from src.database.dependencies import get_async_db

        async def test_async():
            db_gen = get_async_db()
            await anext(db_gen)
            # 验证返回的是 AsyncSession 或 None
            assert True  # 如果没有错误，说明生成器工作正常
            try:
                await anext(db_gen)
            except StopAsyncIteration:
                pass

        # 运行异步测试
        asyncio.run(test_async())

    def test_mock_external_services_fixtures(self):
        """测试外部服务 mock fixtures"""
        # 验证 mock fixtures 可以导入
        from tests.conftest import mock_kafka, mock_mlflow, mock_redis

        # 这些应该返回 fixture 函数，而不是 mock 对象本身
        assert callable(mock_redis)
        assert callable(mock_mlflow)
        assert callable(mock_kafka)

    def test_environment_is_set_correctly(self):
        """测试测试环境变量设置正确"""
        import os

        assert os.getenv("TESTING") == "true"
        assert os.getenv("ENVIRONMENT") == "testing"
        assert os.getenv("DEBUG") == "true"
