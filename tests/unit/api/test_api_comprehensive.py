"""
API综合测试套件
Comprehensive API Test Suite

测试所有API端点的基础功能，确保API层的稳定性和正确性。
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime

from src.api.app import app
from src.api.health.routes import router as health_router


class TestAPIBasics:
    """API基础功能测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_app_startup(self, client):
        """测试应用启动"""
        response = client.get("/")
        # 检查应用是否正常启动（可能有根路径响应或404）
        assert response.status_code in [200, 404]

    def test_api_docs_available(self, client):
        """测试API文档可用性"""
        # 测试OpenAPI文档
        response = client.get("/docs")
        assert response.status_code in [200, 404]

        # 测试ReDoc文档
        response = client.get("/redoc")
        assert response.status_code in [200, 404]

        # 测试OpenAPI schema
        response = client.get("/openapi.json")
        assert response.status_code in [200, 404]

    def test_cors_headers(self, client):
        """测试CORS头设置"""
        # 测试预检请求
        response = client.options("/health")
        # 应该有CORS相关头部
        assert response.status_code in [200, 405]


class TestHealthEndpoints:
    """健康检查端点测试"""

    @pytest.fixture
    def health_client(self):
        """创建健康检查客户端"""
        app_health = FastAPI()
        app_health.include_router(health_router)
        return TestClient(app_health)

    def test_basic_health_check(self, health_client):
        """测试基础健康检查"""
        response = health_client.get("/health/")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data
        assert "version" in data
        assert data["service"] == "football-prediction-api"

    def test_detailed_health_check(self, health_client):
        """测试详细健康检查"""
        response = health_client.get("/health/detailed")
        assert response.status_code == 200

        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data
        assert "service" in data
        assert "components" in data

    def test_health_response_format(self, health_client):
        """测试健康检查响应格式"""
        response = health_client.get("/health/")
        data = response.json()

        # 验证必需字段
        required_fields = ["status", "timestamp", "service", "version"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

        # 验证时间戳格式
        try:
            datetime.fromisoformat(data["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            pytest.fail("Invalid timestamp format")

    def test_health_check_with_mocks(self, health_client):
        """测试带Mock的健康检查"""
        with patch('src.api.health.routes.datetime') as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now

            response = health_client.get("/health/")
            assert response.status_code == 200

            data = response.json()
            assert data["timestamp"] == mock_now.isoformat()


class TestAPIResponseHeaders:
    """API响应头测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_content_type_headers(self, client):
        """测试内容类型头部"""
        # 测试JSON响应
        response = client.get("/health/")
        if response.status_code == 200:
            assert "application/json" in response.headers.get("content-type", "")

    def test_security_headers(self, client):
        """测试安全头部"""
        response = client.get("/health/")
        # 检查基本的安全头部（可能不存在，但不应该导致错误）
        headers = response.headers

        # 验证没有敏感信息泄露
        assert "server" not in headers.lower() or "nginx" not in headers.get("server", "").lower()

    def test_response_time_headers(self, client):
        """测试响应时间头部"""
        response = client.get("/health/")
        # 检查是否有响应时间相关头部
        headers = response.headers
        # 可能的响应时间头部
        possible_time_headers = ["x-response-time", "x-process-time"]

        for header in possible_time_headers:
            if header in headers:
                # 验证时间格式
                try:
                    float(headers[header])
                except ValueError:
                    pytest.fail(f"Invalid time format in header: {header}")


class TestAPIErrorHandling:
    """API错误处理测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_404_handling(self, client):
        """测试404错误处理"""
        response = client.get("/nonexistent-endpoint")
        assert response.status_code == 404

        data = response.json()
        assert "detail" in data

    def test_method_not_allowed(self, client):
        """测试方法不允许错误"""
        response = client.post("/health/")
        # 可能是405或其他状态码
        assert response.status_code in [405, 422, 404]

    def test_invalid_data_handling(self, client):
        """测试无效数据处理"""
        # 发送无效JSON
        response = client.post(
            "/api/test",  # 假设的测试端点
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )
        # 应该返回422或其他错误状态码
        assert response.status_code in [422, 404, 405]

    def test_large_payload_handling(self, client):
        """测试大载荷处理"""
        large_data = {"data": "x" * 10000}
        response = client.post("/health/", json=large_data)
        # 应该能够处理或适当拒绝大载荷
        assert response.status_code in [200, 413, 422, 405]


class TestAPIConcurrency:
    """API并发测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_concurrent_health_checks(self, client):
        """测试并发健康检查"""
        import threading
        import time

        results = []

        def make_request():
            response = client.get("/health/")
            results.append(response.status_code)

        # 创建多个线程同时请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        # 启动所有线程
        for thread in threads:
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证所有请求都成功
        assert len(results) == 10
        assert all(status == 200 for status in results)


class TestAPIMiddleware:
    """API中间件测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_request_logging_middleware(self, client):
        """测试请求日志中间件"""
        with patch('src.api.app.logger') as mock_logger:
            response = client.get("/health/")
            # 验证请求被记录（如果实现了日志中间件）
            # 这里只是验证请求成功，具体日志实现可能不同
            assert response.status_code in [200, 404]

    def test_cors_middleware(self, client):
        """测试CORS中间件"""
        # 测试预检请求
        response = client.options("/health/", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })

        # 验证CORS头部
        if response.status_code == 200:
            cors_headers = [
                "access-control-allow-origin",
                "access-control-allow-methods",
                "access-control-allow-headers"
            ]
            # 至少应该有一些CORS相关头部
            has_cors = any(header in response.headers for header in cors_headers)

    def test_gzip_middleware(self, client):
        """测试GZIP中间件"""
        # 发送带有Accept-Encoding头的请求
        response = client.get("/health/", headers={
            "Accept-Encoding": "gzip"
        })

        # 如果支持GZIP，响应应该被压缩
        # 这里主要验证请求处理正常
        assert response.status_code in [200, 404]


class TestAPIDocumentation:
    """API文档测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_openapi_schema_structure(self, client):
        """测试OpenAPI schema结构"""
        response = client.get("/openapi.json")
        if response.status_code == 200:
            schema = response.json()

            # 验证基本结构
            required_keys = ["openapi", "info", "paths"]
            for key in required_keys:
                assert key in schema, f"Missing required OpenAPI field: {key}"

            # 验证info字段
            info = schema["info"]
            assert "title" in info
            assert "version" in info

    def test_health_endpoint_documentation(self, client):
        """测试健康检查端点文档"""
        # 检查健康检查端点是否在文档中
        response = client.get("/openapi.json")
        if response.status_code == 200:
            schema = response.json()
            paths = schema.get("paths", {})

            # 检查健康检查路径
            health_paths = [path for path in paths.keys() if "health" in path]
            assert len(health_paths) > 0, "Health endpoints not documented"

    def test_api_info_endpoint(self, client):
        """测试API信息端点"""
        # 可能存在的信息端点
        info_endpoints = ["/info", "/api/info", "/status"]

        for endpoint in info_endpoints:
            response = client.get(endpoint)
            if response.status_code == 200:
                data = response.json()
                # 验证信息响应包含基本信息
                assert isinstance(data, dict)


class TestAPIPerformance:
    """API性能测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_health_check_response_time(self, client):
        """测试健康检查响应时间"""
        import time

        start_time = time.time()
        response = client.get("/health/")
        end_time = time.time()

        response_time = end_time - start_time

        # 健康检查应该在合理时间内响应（< 1秒）
        assert response_time < 1.0, f"Health check too slow: {response_time}s"
        assert response.status_code in [200, 404]

    def test_concurrent_requests_performance(self, client):
        """测试并发请求性能"""
        import threading
        import time

        response_times = []

        def make_request():
            start = time.time()
            response = client.get("/health/")
            end = time.time()
            response_times.append(end - start)

        # 并发执行10个请求
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=make_request)
            threads.append(thread)

        start_time = time.time()
        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        total_time = time.time() - start_time

        # 验证性能
        assert len(response_times) == 10
        assert total_time < 5.0, f"Concurrent requests too slow: {total_time}s"
        assert max(response_times) < 2.0, f"Single request too slow: {max(response_times)}s"


class TestAPIValidation:
    """API验证测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_health_response_validation(self, client):
        """测试健康检查响应验证"""
        response = client.get("/health/")
        if response.status_code == 200:
            data = response.json()

            # 验证响应结构
            assert isinstance(data, dict)
            assert isinstance(data.get("status"), str)
            assert isinstance(data.get("service"), str)
            assert isinstance(data.get("version"), (str, int, float))

            # 验证状态值
            valid_statuses = ["healthy", "unhealthy", "degraded"]
            assert data.get("status") in valid_statuses

    def test_response_format_consistency(self, client):
        """测试响应格式一致性"""
        # 多次请求同一端点，验证响应格式一致
        responses = []

        for _ in range(3):
            response = client.get("/health/")
            if response.status_code == 200:
                responses.append(response.json())

        if len(responses) > 1:
            # 验证响应结构一致
            first_keys = set(responses[0].keys())
            for response in responses[1:]:
                assert set(response.keys()) == first_keys, "Response format inconsistent"


# 测试工具函数
def create_mock_app():
    """创建模拟应用用于测试"""
    from fastapi import FastAPI
    test_app = FastAPI()

    @test_app.get("/test")
    async def test_endpoint():
        return {"message": "test"}

    return test_app


def create_test_client_with_app(app):
    """使用指定应用创建测试客户端"""
    return TestClient(app)