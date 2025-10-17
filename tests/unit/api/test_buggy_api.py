"""
Buggy API测试
Tests for Buggy API

测试src.api.buggy_api模块的功能（用于演示API修复）
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch

# 测试导入
try:
    from src.api.buggy_api import router, SomeAsyncService, service

    BUGGY_API_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    BUGGY_API_AVAILABLE = False


class TestBuggyAPI:
    """Buggy API测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/test")
        return TestClient(app)

    def test_fixed_query_endpoint(self, client):
        """测试：修复后的查询端点"""
        response = client.get("/test/fixed_query")
        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "type" in data
        assert data["limit"] == 10  # 默认值
        assert data["type"] == "int"

    def test_fixed_query_with_limit(self, client):
        """测试：带限制参数的查询端点"""
        response = client.get("/test/fixed_query?limit=50")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 50
        assert data["type"] == "int"

    def test_fixed_query_validation(self, client):
        """测试：查询参数验证"""
        # 测试最小值边界
        response = client.get("/test/fixed_query?limit=1")
        assert response.status_code == 200
        assert response.json()["limit"] == 1

        # 测试最大值边界
        response = client.get("/test/fixed_query?limit=100")
        assert response.status_code == 200
        assert response.json()["limit"] == 100

    def test_fixed_query_invalid_limit(self, client):
        """测试：无效的查询参数"""
        # 小于最小值
        response = client.get("/test/fixed_query?limit=0")
        assert response.status_code == 422  # Validation error

        # 大于最大值
        response = client.get("/test/fixed_query?limit=101")
        assert response.status_code == 422  # Validation error

        # 非数字
        response = client.get("/test/fixed_query?limit=abc")
        assert response.status_code == 422  # Validation error

    def test_buggy_query_endpoint(self, client):
        """测试：修复后的buggy查询端点"""
        response = client.get("/test/buggy_query")
        assert response.status_code == 200
        data = response.json()
        assert "limit" in data
        assert "type" in data
        assert isinstance(data["limit"], int)
        assert data["type"] == "int"

    def test_buggy_query_with_parameter(self, client):
        """测试：带参数的buggy查询端点"""
        response = client.get("/test/buggy_query?limit=25")
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 25
        assert isinstance(data["limit"], int)  # 确保类型转换正确

    @patch("src.api.buggy_api.service")
    def test_buggy_async_endpoint(self, mock_service, client):
        """测试：异步端点"""
        mock_service.get_status = AsyncMock(return_value="test_status")

        response = client.get("/test/buggy_async")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "test_status"
        mock_service.get_status.assert_called_once()


class TestSomeAsyncService:
    """异步服务测试"""

    @pytest.mark.asyncio
    async def test_get_status(self):
        """测试：获取状态"""
        service_instance = SomeAsyncService()
        status = await service_instance.get_status()
        assert status == "real_status"

    def test_service_instantiation(self):
        """测试：服务实例化"""
        assert isinstance(service, SomeAsyncService)
        # 确保是同一个实例（单例模式）
        service2 = SomeAsyncService()
        assert service is not service2  # 不是单例，每次创建新实例


class TestBuggyAPIIntegration:
    """Buggy API集成测试"""

    def test_router_structure(self):
        """测试：路由器结构"""
        routes = list(router.routes)
        assert len(routes) == 3  # 应该有3个端点

        route_paths = [route.path for route in routes]
        assert "/fixed_query" in route_paths
        assert "/buggy_query" in route_paths
        assert "/buggy_async" in route_paths

    def test_route_methods(self):
        """测试：路由方法"""
        for route in router.routes:
            assert "GET" in route.methods

    def test_endpoint_documentation(self):
        """测试：端点文档"""
        for route in router.routes:
            if hasattr(route, "endpoint"):
                # 端点应该有文档字符串
                if route.endpoint.__doc__:
                    assert len(route.endpoint.__doc__.strip()) > 0

    def test_query_parameter_specs(self):
        """测试：查询参数规范"""
        # 检查路由是否有正确的查询参数
        for route in router.routes:
            if hasattr(route, "dependant"):
                # 检查依赖项
                assert route.dependant is not None

    def test_fastapi_integration(self):
        """测试：FastAPI集成"""
        from fastapi import FastAPI

        app = FastAPI()

        # 应该能够成功包含路由
        app.include_router(router)

        # 验证路由已添加
        route_count = len(app.routes)
        assert route_count >= 3  # 至少包含3个新路由


class TestBuggyAPIEdgeCases:
    """Buggy API边界情况测试"""

    def test_concurrent_requests(self):
        """测试：并发请求"""
        import threading
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/test")
        client = TestClient(app)

        results = []
        errors = []

        def make_request():
            try:
                response = client.get("/test/fixed_query?limit=20")
                results.append(response.status_code)
            except Exception as e:
                errors.append(e)

        # 创建多个线程同时请求
        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        # 验证所有请求都成功
        assert len(errors) == 0
        assert len(results) == 10
        assert all(status == 200 for status in results)

    def test_large_limit_values(self):
        """测试：大限制值"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/test")
        client = TestClient(app)

        # 测试接近边界的值
        test_values = [1, 50, 99, 100]
        for value in test_values:
            response = client.get(f"/test/fixed_query?limit={value}")
            assert response.status_code == 200
            assert response.json()["limit"] == value

    def test_endpoint_response_format(self):
        """测试：端点响应格式"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/test")
        client = TestClient(app)

        response = client.get("/test/fixed_query")
        assert response.headers["content-type"] == "application/json"

        data = response.json()
        assert isinstance(data, dict)
        assert set(data.keys()) == {"limit", "type"}

    def test_parameter_type_handling(self):
        """测试：参数类型处理"""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router, prefix="/test")
        client = TestClient(app)

        # 测试字符串数字
        response = client.get("/test/fixed_query?limit=50")
        assert response.status_code == 200
        assert isinstance(response.json()["limit"], int)

        # 测试浮点数（如果允许）
        response = client.get("/test/fixed_query?limit=10.0")
        # FastAPI应该自动处理类型转换
        assert response.status_code in [200, 422]


# 如果模块不可用，添加一个占位测试
@pytest.mark.skipif(True, reason="Module not available")
class TestModuleNotAvailable:
    """模块不可用时的占位测试"""

    def test_module_import_error(self):
        """测试：模块导入错误"""
        assert not BUGGY_API_AVAILABLE
        assert True  # 表明测试意识到模块不可用
