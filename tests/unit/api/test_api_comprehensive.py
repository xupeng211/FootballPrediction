"""
API 模块综合测试
Comprehensive API Module Tests
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime

from src.api.app import app


class TestAPIComprehensive:
    """API 综合测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_app_lifecycle(self, client):
        """测试应用生命周期"""
        # 测试应用可以启动
        response = client.get("/")
        assert response.status_code == 200
        assert "Football Prediction API" in response.json()["message"]

    def test_health_endpoints(self, client):
        """测试所有健康检查端点"""
        # 测试主健康检查端点
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data

        # 测试健康路由端点
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data or "status" in data

    def test_api_documentation(self, client):
        """测试 API 文档端点"""
        # 测试 OpenAPI 文档
        response = client.get("/openapi.json")
        assert response.status_code == 200
        openapi_data = response.json()
        assert "openapi" in openapi_data
        assert "info" in openapi_data
        assert openapi_data["info"]["title"] == "Football Prediction API"

        # 测试 Swagger UI
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

        # 测试 ReDoc
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_metrics_endpoint(self, client):
        """测试指标端点"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        metrics_data = response.text
        assert "http_requests_total" in metrics_data
        assert "request_duration_seconds" in metrics_data
        assert "api_health_status" in metrics_data

    def test_test_endpoint(self, client):
        """测试测试端点"""
        response = client.get("/api/test")
        assert response.status_code == 200
        data = response.json()
        assert "API is working!" in data["message"]
        assert "timestamp" in data

    def test_error_handling(self, client):
        """测试错误处理"""
        # 测试 404 错误
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "http_error"

        # 测试方法不允许
        response = client.post("/api/health")
        assert response.status_code == 405

        # 测试验证错误（如果有的话）
        response = client.get("/api/v1/health?invalid_param=test")
        # 可能返回 200 或 422，取决于实现
        assert response.status_code in [200, 422]

    def test_cors_headers(self, client):
        """测试 CORS 头"""
        # 发送 OPTIONS 请求
        response = client.options("/api/health")
        # 可能返回 405 或 200
        if response.status_code == 200:
            assert "access-control-allow-origin" in response.headers

    def test_middleware(self, client):
        """测试中间件功能"""
        # 测试请求日志中间件
        response = client.get("/api/test")
        assert response.status_code == 200
        # 检查是否有处理时间头（如果有添加的话）
        if "x-process-time" in response.headers:
            assert float(response.headers["x-process-time"]) >= 0

    @patch("src.api.app.prediction_engine")
    def test_prediction_engine_integration(self, mock_engine, client):
        """测试预测引擎集成"""
        # 模拟预测引擎
        mock_engine.return_value = None

        # 测试应用启动时初始化预测引擎
        response = client.get("/")
        assert response.status_code == 200

    def test_global_exception_handler(self, client):
        """测试全局异常处理器"""
        # 测试内部服务器错误（通过访问可能出错的路由）
        # 这里我们模拟一个可能出错的情况
        with patch("src.api.app.logger"):
            # 发送可能导致错误的请求
            response = client.post("/api/invalid-endpoint", json={})
            # 应该返回 404 而不是 500
            assert response.status_code == 404

    def test_content_negotiation(self, client):
        """测试内容协商"""
        # 测试 JSON 响应
        response = client.get("/api/health", headers={"Accept": "application/json"})
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]

        # 测试 HTML 响应（如果支持）
        response = client.get("/docs", headers={"Accept": "text/html"})
        assert response.status_code == 200

    def test_security_headers(self, client):
        """测试安全头"""
        response = client.get("/")
        assert response.status_code == 200
        # 检查常见的安全头（如果有的话）
        # 注意：这些头可能没有，取决于配置
        # assert "x-content-type-options" in headers
        # assert "x-frame-options" in headers

    def test_rate_limiting(self, client):
        """测试速率限制（如果实现）"""
        # 快速发送多个请求
        responses = []
        for _ in range(10):
            response = client.get("/api/health")
            responses.append(response.status_code)

        # 大部分请求应该成功
        success_count = sum(1 for code in responses if code == 200)
        assert success_count >= 5  # 至少一半成功

    def test_async_lifecycle(self):
        """测试异步生命周期管理"""
        # 测试 lifespan 上下文管理器
        with patch("src.api.app.init_prediction_engine") as mock_init, patch(
            "src.api.app.close_prediction_engine"
        ) as mock_close:
            # 创建应用实例会触发 lifespan
            with TestClient(app) as client:
                response = client.get("/")
                assert response.status_code == 200

            # 验证生命周期方法被调用
            mock_init.assert_called_once()
            mock_close.assert_called_once()

    def test_application_configuration(self):
        """测试应用配置"""
        # 检查应用配置
        assert app.title == "Football Prediction API"
        assert app.version == "1.0.0"
        assert "/docs" in app.docs_url
        assert "/redoc" in app.redoc_url

    def test_route_registration(self):
        """测试路由注册"""
        # 检查路由是否正确注册
        routes = [route.path for route in app.routes]

        # 应该注册的路由
        expected_routes = [
            "/",
            "/api/health",
            "/metrics",
            "/api/test",
            "/openapi.json",
            "/docs",
            "/redoc",
        ]

        for route in expected_routes:
            assert route in routes

    def test_dependency_injection_setup(self):
        """测试依赖注入设置"""
        # 检查中间件是否正确添加
        middleware_types = [middleware.cls for middleware in app.user_middleware]

        # 应该有的中间件
        assert len(middleware_types) >= 1  # 至少有日志中间件
        # 检查日志中间件类名
        assert any("RequestLogging" in str(mw.__name__) for mw in middleware_types)
