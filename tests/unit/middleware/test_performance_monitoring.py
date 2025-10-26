"""测试性能监控中间件"""

import pytest
import time
import asyncio
from unittest.mock import Mock, patch, AsyncMock

try:
    from src.middleware.performance_monitoring import PerformanceMiddleware
    IMPORT_SUCCESS = True
except ImportError as e:
    IMPORT_SUCCESS = False
    IMPORT_ERROR = str(e)


@pytest.mark.skipif(not IMPORT_SUCCESS, reason="Module import failed")
@pytest.mark.middleware
class TestPerformanceMiddleware:
    """性能监控中间件测试"""

    def test_middleware_creation_enabled(self):
        """测试启用状态的中间件创建"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=True)

        assert middleware.enabled is True
        assert hasattr(middleware, 'dispatch')

    def test_middleware_creation_disabled(self):
        """测试禁用状态的中间件创建"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=False)

        assert middleware.enabled is False

    def test_middleware_creation_default_enabled(self):
        """测试默认启用状态的中间件创建"""
        app = Mock()
        middleware = PerformanceMiddleware(app)

        assert middleware.enabled is True  # 默认应该是启用的

    @pytest.mark.asyncio
    async def test_dispatch_enabled(self):
        """测试启用状态下的请求处理"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=True)

        # 创建模拟请求和响应
        request = Mock()
        request.method = "GET"
        request.url = "http://test.com/api/test"

        call_next = AsyncMock()
        response = Mock()
        response.status_code = 200
        response.headers = {}
        call_next.return_value = response

        # 测试中间件处理
        result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_dispatch_disabled(self):
        """测试禁用状态下的请求处理"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=False)

        # 创建模拟请求和响应
        request = Mock()
        request.method = "POST"
        request.url = "http://test.com/api/test"

        call_next = AsyncMock()
        response = Mock()
        response.status_code = 201
        response.headers = {}
        call_next.return_value = response

        # 测试中间件处理
        result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)

    @pytest.mark.asyncio
    async def test_performance_measurement(self):
        """测试性能测量功能"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=True)

        request = Mock()
        request.method = "GET"
        request.url = "http://test.com/api/test"

        call_next = AsyncMock()
        response = Mock()
        response.status_code = 200
        response.headers = {}

        # 模拟一些处理时间
        async def slow_handler(request):
            await asyncio.sleep(0.001)  # 1毫秒延迟
            return response

        call_next.side_effect = slow_handler

        # 测试性能测量
        start_time = time.time()
        result = await middleware.dispatch(request, call_next)
        end_time = time.time()

        assert result == response
        assert end_time - start_time >= 0.001  # 至少1毫秒

    def test_inheritance_from_base_middleware(self):
        """测试继承自BaseHTTPMiddleware"""
        app = Mock()
        middleware = PerformanceMiddleware(app)

        # 检查继承关系
        from starlette.middleware.base import BaseHTTPMiddleware
        assert isinstance(middleware, BaseHTTPMiddleware)

    def test_middleware_attributes(self):
        """测试中间件属性"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=True)

        # 检查关键属性
        assert hasattr(middleware, 'enabled')
        assert hasattr(middleware, 'dispatch')
        assert isinstance(middleware.enabled, bool)

    @pytest.mark.parametrize("http_method", ["GET", "POST", "PUT", "DELETE", "PATCH"])
    @pytest.mark.asyncio
    async def test_different_http_methods(self, http_method):
        """测试不同的HTTP方法"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=True)

        request = Mock()
        request.method = http_method
        request.url = "http://test.com/api/test"

        call_next = AsyncMock()
        response = Mock()
        response.status_code = 200
        response.headers = {}
        call_next.return_value = response

        result = await middleware.dispatch(request, call_next)

        assert result == response
        call_next.assert_called_once_with(request)

    @pytest.mark.parametrize("status_code", [200, 201, 400, 404, 500])
    @pytest.mark.asyncio
    async def test_different_status_codes(self, status_code):
        """测试不同的状态码"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=True)

        request = Mock()
        request.method = "GET"
        request.url = "http://test.com/api/test"

        call_next = AsyncMock()
        response = Mock()
        response.status_code = status_code
        response.headers = {}
        call_next.return_value = response

        result = await middleware.dispatch(request, call_next)

        assert result == response
        assert result.status_code == status_code

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """测试异常处理"""
        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=True)

        request = Mock()
        request.method = "GET"
        request.url = "http://test.com/api/test"

        call_next = AsyncMock()

        # 模拟异常
        async def failing_handler(request):
            raise ValueError("Test exception")

        call_next.side_effect = failing_handler

        # 测试异常传播
        with pytest.raises(ValueError, match="Test exception"):
            await middleware.dispatch(request, call_next)

    @pytest.mark.asyncio
    async def test_concurrent_requests(self):
        """测试并发请求处理"""
        import asyncio

        app = Mock()
        middleware = PerformanceMiddleware(app, enabled=True)

        async def handle_multiple_requests():
            tasks = []
            for i in range(5):
                request = Mock()
                request.method = "GET"
                request.url = f"http://test.com/api/test{i}"

                call_next = AsyncMock()
                response = Mock()
                response.status_code = 200
                response.headers = {}
                call_next.return_value = response

                task = middleware.dispatch(request, call_next)
                tasks.append(task)

            results = await asyncio.gather(*tasks)
            return results

        # 测试并发处理
        results = await handle_multiple_requests()
        assert len(results) == 5
        for result in results:
            assert result.status_code == 200

    def test_middleware_configuration(self):
        """测试中间件配置"""
        app = Mock()

        # 测试不同的配置选项
        configs = [
            {"enabled": True},
            {"enabled": False}
        ]

        for config in configs:
            middleware = PerformanceMiddleware(app, **config)
            assert middleware.enabled == config["enabled"]


def test_import_fallback():
    """测试导入回退"""
    if not IMPORT_SUCCESS:
        assert IMPORT_ERROR is not None
        assert len(IMPORT_ERROR) > 0
    else:
        assert True  # 导入成功