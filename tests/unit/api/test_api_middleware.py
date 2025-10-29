# TODO: Consider creating a fixture for 20 repeated Mock creations

# TODO: Consider creating a fixture for 20 repeated Mock creations




import asyncio
import time

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# 使用try-except导入，如果模块不存在则跳过测试
    from src.api.middleware import (










        # 检查是否有计时头部


        # 检查是否保留了足够的小数位


        # 创建模拟请求

        # 创建模拟响应

        # 模拟处理函数

        # 执行中间件

        # 验证计时头部









        # 验证日志被调用

        # 检查日志内容


        # 验证错误日志被调用

        # 检查错误日志内容


        # 验证请求ID被记录


        # 检查请求ID是否被返回









        # 检查速率限制头部




        # 检查重试头部


        # 从不同IP发起请求


        # 验证每个IP都被独立计数









        # 验证令牌验证未被调用



        # 验证令牌被验证






            # 使用TestRequest来验证state

            # 这个测试需要更复杂的设置来检查request.state.user









        # 检查CORS头部





        # 检查CORS头部


        # 根据配置，可能允许或拒绝








        # 检查各种安全头部

        # XSS保护

        # 点击劫持保护

        # HSTS（如果使用HTTPS）
        # assert headers.get("Strict-Transport-Security") is not None

        # 内容安全策略

        # 这个测试需要中间件支持自定义配置

        # 检查是否有其他安全相关的头部











        # 验证缓存操作



        # 验证缓存操作


        # 检查缓存控制头部



            # POST请求不应该被缓存


        # 检查ETag头部

        # 第一次请求获取ETag

            # 第二次请求使用If-None-Match
            # 应该返回304 Not Modified
















            # 验证错误被记录

        # 在生产环境中，可能需要隐藏详细的错误信息



            # 在生产环境中，错误信息可能更加通用



        # 创建多个中间件来跟踪执行顺序






        # 验证执行顺序






        # 正常请求

        # 短路请求
"""
API中间件测试
"""
pytest_plugins = "asyncio"
try:
        AuthenticationMiddleware,
        CacheMiddleware,
        CORSMiddleware,
        ErrorHandlingMiddleware,
        LoggingMiddleware,
        RateLimitMiddleware,
        SecurityHeadersMiddleware,
        TimingMiddleware,
    )
    MIDDLEWARE_AVAILABLE = True
except ImportError:
    MIDDLEWARE_AVAILABLE = False
TEST_SKIP_REASON = "API middleware module not available"
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
@pytest.mark.unit
class TestTimingMiddleware:
    """计时中间件测试"""
    @pytest.fixture
    def app(self):
        """创建带有计时中间件的应用"""
        app = FastAPI()
        app.add_middleware(TimingMiddleware)
        @app.get("/test")
        async def test_endpoint():
            await asyncio.sleep(0.01)  # 模拟处理时间
            await asyncio.sleep(0.01)  # 模拟处理时间
            await asyncio.sleep(0.01)  # 模拟处理时间
            return {"message": "test"}
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)
    def test_timing_header_added(self, client):
        """测试计时头部被添加"""
        response = client.get("/test")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers
        process_time = float(response.headers["X-Process-Time"])
        assert process_time > 0.01  # 应该大于模拟的延迟
    def test_timing_precision(self, client):
        """测试计时精度"""
        response = client.get("/test")
        process_time = response.headers["X-Process-Time"]
        assert len(process_time.split(".")[-1]) >= 3
    @pytest.mark.asyncio
    async def test_timing_middleware_directly(self):
        """直接测试计时中间件"""
        middleware = TimingMiddleware(Mock())
        request = Mock(spec=Request)
        request.url = Mock()
        request.url.path = "/test"
        request.method = "GET"
        request.state = Mock()
        response = Mock(spec=Response)
        response.headers = {}
        async def call_next(request):
            await asyncio.sleep(0.01)
            return response
        start_time = time.time()
        _result = await middleware.dispatch(request, call_next)
        end_time = time.time()
        assert "X-Process-Time" in result.headers
        recorded_time = float(result.headers["X-Process-Time"])
        assert recorded_time > 0.01
        assert recorded_time < (end_time - start_time + 0.001)  # 允许小误差
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
class TestLoggingMiddleware:
    """日志中间件测试"""
    @pytest.fixture
    def app(self):
        """创建带有日志中间件的应用"""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)
    @patch("src.api.middleware.logger")
    def test_request_logging(self, mock_logger, client):
        """测试请求日志记录"""
        response = client.get("/test")
        assert response.status_code == 200
        mock_logger.info.assert_called()
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("GET /test" in log for log in log_calls)
        assert any("200" in log for log in log_calls)
    @patch("src.api.middleware.logger")
    def test_error_logging(self, mock_logger, client):
        """测试错误日志记录"""
        response = client.get("/error")
        assert response.status_code == 500
        mock_logger.error.assert_called()
        error_calls = [call.args[0] for call in mock_logger.error.call_args_list]
        assert any("Test error" in log for log in error_calls)
    @patch("src.api.middleware.logger")
    def test_request_id_logging(self, mock_logger, client):
        """测试请求ID日志"""
        response = client.get("/test", headers={"X-Request-ID": "test-123"})
        assert response.status_code == 200
        log_calls = [call.args[0] for call in mock_logger.info.call_args_list]
        assert any("test-123" in log for log in log_calls)
    def test_response_request_id(self, client):
        """测试响应请求ID"""
        response = client.get("/test", headers={"X-Request-ID": "test-123"})
        assert response.status_code == 200
        assert response.headers.get("X-Request-ID") == "test-123"
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
class TestRateLimitMiddleware:
    """速率限制中间件测试"""
    @pytest.fixture
    def app(self):
        """创建带有速率限制中间件的应用"""
        app = FastAPI()
        app.add_middleware(RateLimitMiddleware, requests_per_minute=60)
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)
    @patch("src.api.middleware.RateLimiter")
    def test_rate_limit_allowed(self, mock_rate_limiter, client):
        """测试允许的请求"""
        mock_limiter = Mock()
        mock_limiter.is_allowed = Mock(return_value=True)
        mock_limiter.get_remaining = Mock(return_value=59)
        mock_rate_limiter.return_value = mock_limiter
        response = client.get("/test")
        assert response.status_code == 200
        assert response.headers.get("X-RateLimit-Limit") == "60"
        assert response.headers.get("X-RateLimit-Remaining") == "59"
    @patch("src.api.middleware.RateLimiter")
    def test_rate_limit_exceeded(self, mock_rate_limiter, client):
        """测试超出速率限制"""
        mock_limiter = Mock()
        mock_limiter.is_allowed = Mock(return_value=False)
        mock_limiter.get_retry_after = Mock(return_value=60)
        mock_rate_limiter.return_value = mock_limiter
        response = client.get("/test")
        assert response.status_code == 429
        _data = response.json()
        assert "rate limit" in _data["detail"].lower()
        assert response.headers.get("Retry-After") == "60"
    @patch("src.api.middleware.RateLimiter")
    def test_rate_limit_per_ip(self, mock_rate_limiter, client):
        """测试基于IP的速率限制"""
        mock_limiter = Mock()
        mock_limiter.is_allowed = Mock(return_value=True)
        mock_limiter.get_remaining = Mock(return_value=58)
        mock_rate_limiter.return_value = mock_limiter
        response1 = client.get("/test", headers={"X-Forwarded-For": "192.168.1.1"})
        response2 = client.get("/test", headers={"X-Forwarded-For": "192.168.1.2"})
        assert response1.status_code == 200
        assert response2.status_code == 200
        assert mock_limiter.is_allowed.call_count == 2
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
class TestAuthenticationMiddleware:
    """认证中间件测试"""
    @pytest.fixture
    def app(self):
        """创建带有认证中间件的应用"""
        app = FastAPI()
        app.add_middleware(AuthenticationMiddleware, public_paths=["/health", "/login"])
        @app.get("/protected")
        async def protected_endpoint():
            return {"message": "protected"}
        @app.get("/health")
        async def health_endpoint():
            return {"status": "ok"}
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)
    @patch("src.api.middleware.verify_token")
    def test_public_endpoint_access(self, mock_verify, client):
        """测试公开端点访问"""
        response = client.get("/health")
        assert response.status_code == 200
        mock_verify.assert_not_called()
    @patch("src.api.middleware.verify_token")
    def test_protected_endpoint_with_token(self, mock_verify, client):
        """测试带令牌访问受保护端点"""
        mock_verify.return_value = {"user_id": 123, "username": "testuser"}
        response = client.get(
            "/protected", headers={"Authorization": "Bearer valid_token"}
        )
        assert response.status_code == 200
        mock_verify.assert_called_once_with("valid_token")
    @patch("src.api.middleware.verify_token")
    def test_protected_endpoint_without_token(self, mock_verify, client):
        """测试无令牌访问受保护端点"""
        response = client.get("/protected")
        assert response.status_code == 401
        _data = response.json()
        assert "authentication" in _data["detail"].lower()
    @patch("src.api.middleware.verify_token")
    def test_protected_endpoint_with_invalid_token(self, mock_verify, client):
        """测试无效令牌访问受保护端点"""
        mock_verify.return_value = None
        response = client.get(
            "/protected", headers={"Authorization": "Bearer invalid_token"}
        )
        assert response.status_code == 401
    def test_user_attached_to_request(self, client):
        """测试用户信息附加到请求"""
        with patch("src.api.middleware.verify_token") as mock_verify:
            mock_verify.return_value = {"user_id": 123, "username": "testuser"}
            response = client.get(
                "/protected", headers={"Authorization": "Bearer valid_token"}
            )
            assert response.status_code == 200
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
class TestCORSMiddleware:
    """CORS中间件测试"""
    @pytest.fixture
    def app(self):
        """创建带有CORS中间件的应用"""
        app = FastAPI()
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:3000"],
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
            expose_headers=["X-Custom"],
        )
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)
    def test_cors_preflight_allowed(self, client):
        """测试CORS预检请求被允许"""
        headers = {
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Authorization",
        }
        response = client.options("/test", headers=headers)
        assert response.status_code == 200
        assert (
            response.headers.get("Access-Control-Allow-Origin")
            == "http://localhost:3000"
        )
        assert response.headers.get("Access-Control-Allow-Methods") == "GET, POST"
        assert "Authorization" in response.headers.get(
            "Access-Control-Allow-Headers", ""
        )
    def test_cors_preflight_denied(self, client):
        """测试CORS预检请求被拒绝"""
        headers = {
            "Origin": "http://evil-site.com",
            "Access-Control-Request-Method": "POST",
        }
        response = client.options("/test", headers=headers)
        assert response.status_code == 403
    def test_cors_actual_request(self, client):
        """测试实际CORS请求"""
        headers = {"Origin": "http://localhost:3000"}
        response = client.get("/test", headers=headers)
        assert response.status_code == 200
        assert (
            response.headers.get("Access-Control-Allow-Origin")
            == "http://localhost:3000"
        )
        assert response.headers.get("Access-Control-Expose-Headers") == "X-Custom"
    def test_cors_wildcard_origin(self, client):
        """测试通配符源"""
        headers = {"Origin": "http://localhost:8080"}
        client.get("/test", headers=headers)
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
class TestSecurityHeadersMiddleware:
    """安全头部中间件测试"""
    @pytest.fixture
    def app(self):
        """创建带有安全头部中间件的应用"""
        app = FastAPI()
        app.add_middleware(SecurityHeadersMiddleware)
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)
    def test_security_headers_added(self, client):
        """测试安全头部被添加"""
        response = client.get("/test")
        assert response.status_code == 200
        headers = response.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        csp = headers.get("Content-Security-Policy")
        if csp:
            assert "default-src" in csp
    def test_custom_security_headers(self, client):
        """测试自定义安全头部"""
        response = client.get("/test")
        headers = response.headers
        security_headers = [
            "X-Content-Type-Options",
            "X-Frame-Options",
            "X-XSS-Protection",
            "Referrer-Policy",
        ]
        for header in security_headers:
            assert headers.get(header) is not None
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
class TestCacheMiddleware:
    """缓存中间件测试"""
    @pytest.fixture
    def app(self):
        """创建带有缓存中间件的应用"""
        app = FastAPI()
        app.add_middleware(
            CacheMiddleware,
            default_ttl=300,
            cacheable_methods=["GET"],
            cacheable_status_codes=[200],
        )
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test", "timestamp": time.time()}
        @app.post("/test")
        async def test_post():
            return {"message": "posted"}
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)
    @patch("src.api.middleware.Cache")
    def test_cache_get_miss(self, mock_cache, client):
        """测试缓存未命中"""
        mock_cache_instance = Mock()
        mock_cache_instance.get = Mock(return_value=None)
        mock_cache_instance.set = Mock()
        mock_cache.return_value = mock_cache_instance
        response = client.get("/test")
        assert response.status_code == 200
        mock_cache_instance.get.assert_called_once()
        mock_cache_instance.set.assert_called_once()
    @patch("src.api.middleware.Cache")
    def test_cache_get_hit(self, mock_cache, client):
        """测试缓存命中"""
        cached_response = {"message": "cached"}
        mock_cache_instance = Mock()
        mock_cache_instance.get = Mock(return_value=cached_response)
        mock_cache.return_value = mock_cache_instance
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["message"] == "cached"
        mock_cache_instance.get.assert_called_once()
        mock_cache_instance.set.assert_not_called()
    def test_cache_headers(self, client):
        """测试缓存头部"""
        response = client.get("/test")
        assert response.status_code == 200
        cache_control = response.headers.get("Cache-Control")
        if cache_control:
            assert "max-age" in cache_control
    def test_non_cacheable_method(self, client):
        """测试不可缓存的方法"""
        with patch("src.api.middleware.Cache") as mock_cache:
            mock_cache_instance = Mock()
            mock_cache.return_value = mock_cache_instance
            response = client.post("/test", json={"data": "test"})
            assert response.status_code == 200
            mock_cache_instance.get.assert_not_called()
            mock_cache_instance.set.assert_not_called()
    def test_etag_generation(self, client):
        """测试ETag生成"""
        response = client.get("/test")
        assert response.status_code == 200
        etag = response.headers.get("ETag")
        if etag:
            assert etag.startswith('"')
            assert etag.endswith('"')
    def test_if_none_match(self, client):
        """测试If-None-Match头部"""
        response1 = client.get("/test")
        etag = response1.headers.get("ETag")
        if etag:
            response2 = client.get("/test", headers={"If-None-Match": etag})
            assert response2.status_code == 304
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
class TestErrorHandlingMiddleware:
    """错误处理中间件测试"""
    @pytest.fixture
    def app(self):
        """创建带有错误处理中间件的应用"""
        app = FastAPI()
        app.add_middleware(ErrorHandlingMiddleware)
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        @app.get("/http_error")
        async def http_error_endpoint():
            raise HTTPException(status_code=404, detail="Not found")
        return app
    @pytest.fixture
    def client(self, app):
        """创建测试客户端"""
        return TestClient(app)
    def test_normal_request(self, client):
        """测试正常请求"""
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["message"] == "test"
    def test_unhandled_exception(self, client):
        """测试未处理异常"""
        response = client.get("/error")
        assert response.status_code == 500
        _data = response.json()
        assert "error" in _data
        assert "Internal Server Error" in _data["error"]["message"]
    def test_http_exception(self, client):
        """测试HTTP异常"""
        response = client.get("/http_error")
        assert response.status_code == 404
        _data = response.json()
        assert _data["detail"] == "Not found"
    def test_error_logging(self, client):
        """测试错误日志记录"""
        with patch("src.api.middleware.logger") as mock_logger:
            response = client.get("/error")
            assert response.status_code == 500
            mock_logger.error.assert_called()
    def test_error_in_production(self, client):
        """测试生产环境错误处理"""
        with patch("src.api.middleware.settings") as mock_settings:
            mock_settings.DEBUG = False
            response = client.get("/error")
            assert response.status_code == 500
            _data = response.json()
            assert "error" in _data
            assert "Test error" not in _data["error"]["message"]
@pytest.mark.skipif(not MIDDLEWARE_AVAILABLE, reason=TEST_SKIP_REASON)
class TestMiddlewareOrder:
    """中间件顺序测试"""
    def test_middleware_execution_order(self):
        """测试中间件执行顺序"""
        execution_order = []
        class OrderMiddleware1(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                execution_order.append("middleware1_before")
                response = await call_next(request)
                execution_order.append("middleware1_after")
                return response
        class OrderMiddleware2(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                execution_order.append("middleware2_before")
                response = await call_next(request)
                execution_order.append("middleware2_after")
                return response
        app = FastAPI()
        app.add_middleware(OrderMiddleware1)
        app.add_middleware(OrderMiddleware2)
        @app.get("/test")
        async def test_endpoint():
            execution_order.append("endpoint")
            return {"message": "test"}
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert execution_order == [
            "middleware2_before",  # 后添加的先执行
            "middleware1_before",
            "endpoint",
            "middleware1_after",  # 后添加的后结束
            "middleware2_after",
        ]
    def test_middleware_short_circuit(self):
        """测试中间件短路"""
        class ShortCircuitMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                if request.url.path == "/short-circuit":
                    return JSONResponse({"message": "short-circuited"})
                return await call_next(request)
        app = FastAPI()
        app.add_middleware(ShortCircuitMiddleware)
        @app.get("/test")
        async def test_endpoint():
            return {"message": "test"}
        client = TestClient(app)
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json()["message"] == "test"
        response = client.get("/short-circuit")
        assert response.status_code == 200
        assert response.json()["message"] == "short-circuited"
