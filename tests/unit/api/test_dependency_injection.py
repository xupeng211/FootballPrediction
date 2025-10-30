# TODO: Consider creating a fixture for 8 repeated Mock creations

# TODO: Consider creating a fixture for 8 repeated Mock creations


"""
测试依赖注入机制
Test dependency injection mechanism
"""

import pytest
from fastapi.testclient import TestClient

from src.database.dependencies import async_db_session, db_session, get_async_db, get_db
from src.main import app


@pytest.mark.unit
@pytest.mark.api
class TestDependencyInjectionFixtures:
    """测试依赖注入 fixtures 是否正常工作"""

    def test_db_session_fixture_exists(self):
        """测试 db_session fixture 是否存在"""
        # 这个测试验证依赖注入函数是否正确定义
        assert callable(get_db), "get_db 应该是可调用的"
        assert db_session.dependency == get_db, "db_session 应该使用 get_db"

    def test_async_db_session_fixture_exists(self):
        """测试 async_db_session fixture 是否存在"""
        assert callable(get_async_db), "get_async_db 应该是可调用的"
        assert async_db_session.dependency == get_async_db, "async_db_session 应该使用 get_async_db"

    def test_dependency_override_mechanism(self):
        """测试依赖覆盖机制"""
        # 创建模拟的数据库会话
        mock_db = Mock()
        mock_db.execute.return_value = Mock()
        mock_db.close = Mock()

        # 定义覆盖函数
        def override_get_db():
            try:
                yield mock_db
            finally:
                pass

        # 应用覆盖
        app.dependency_overrides[get_db] = override_get_db

        # 验证覆盖已应用
        assert get_db in app.dependency_overrides

        # 清理
        app.dependency_overrides.clear()

        # 验证清理成功
        assert get_db not in app.dependency_overrides

    def test_multiple_dependencies_override(self):
        """测试多个依赖同时覆盖"""
        mock_db = Mock()
        mock_async_db = Mock()

        def override_get_db():
            yield mock_db

        async def override_get_async_db():
            yield mock_async_db

        # 应用多个覆盖
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_async_db] = override_get_async_db

        # 验证两个覆盖都存在
        assert get_db in app.dependency_overrides
        assert get_async_db in app.dependency_overrides

        # 清理
        app.dependency_overrides.clear()


class TestTestClientWithDependencyOverrides:
    """测试使用依赖覆盖的测试客户端"""

    def test_test_client_with_db_override(self):
        """测试测试客户端使用数据库依赖覆盖"""
        # 创建模拟数据库会话
        mock_db = Mock()
        mock_db.execute.return_value.fetchall.return_value = [{"count": 5}]

        def override_get_db():
            yield mock_db

        # 应用依赖覆盖
        app.dependency_overrides[get_db] = override_get_db

        try:
            # 创建测试客户端
            with TestClient(app) as client:
                # 测试健康检查（不需要数据库）
                response = client.get("/")
                assert response.status_code in [200, 404]
        finally:
            # 确保清理
            app.dependency_overrides.clear()

    def test_dependency_isolation(self):
        """测试依赖在不同测试间隔离"""
        # 测试1
        mock_db_1 = Mock()

        def override_1():
            yield mock_db_1

        app.dependency_overrides[get_db] = override_1
        assert app.dependency_overrides[get_db] == override_1

        # 清理
        app.dependency_overrides.clear()

        # 测试2
        mock_db_2 = Mock()

        def override_2():
            yield mock_db_2

        app.dependency_overrides[get_db] = override_2
        assert app.dependency_overrides[get_db] == override_2

        # 清理
        app.dependency_overrides.clear()


class TestNoMonkeypatchMode:
    """测试不使用 monkeypatch 的模式"""

    def test_environment_variables_set_without_monkeypatch(self):
        """测试环境变量设置（不使用 monkeypatch）"""
        import os

        # 验证测试环境变量已设置
        assert os.getenv("ENVIRONMENT") == "testing"
        assert os.getenv("TESTING") == "true"
        assert os.getenv("DEBUG") == "true"

    def test_no_global_sys_modules_mocks(self):
        """测试没有全局 sys.modules mock"""
        import sys

        # 检查没有全局 mock requests 模块
        if "requests" in sys.modules:
            # 如果模块已加载,确保不是我们的 mock
            import requests

            assert hasattr(requests, "get")
            assert hasattr(requests, "post")

    def test_mock_fixtures_available(self):
        """测试 mock fixtures 是否可用"""
        # 这些 fixtures 应该可以在测试中按需使用
        from tests.conftest import mock_kafka, mock_mlflow, mock_redis

        assert callable(mock_redis)
        assert callable(mock_mlflow)
        assert callable(mock_kafka)
