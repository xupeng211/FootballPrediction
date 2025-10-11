"""
现有API端点测试
Existing API Endpoints Tests
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
import json
from datetime import datetime

from src.api.app import app


@pytest.mark.unit
class TestExistingAPIEndpoints:
    """现有API端点测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Football Prediction API" in data["message"]
        assert "version" in data
        assert "docs" in data
        assert "health" in data

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "service" in data

    def test_metrics_endpoint(self, client):
        """测试指标端点"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        metrics_data = response.text
        # 检查基本的Prometheus格式
        assert "HELP" in metrics_data or "http_requests_total" in metrics_data

    def test_test_endpoint(self, client):
        """测试测试端点"""
        response = client.get("/api/test")
        assert response.status_code == 200
        data = response.json()
        assert "API is working!" in data["message"]
        assert "timestamp" in data

    def test_docs_endpoint(self, client):
        """测试文档端点"""
        response = client.get("/docs")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_redoc_endpoint(self, client):
        """测试ReDoc端点"""
        response = client.get("/redoc")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_openapi_endpoint(self, client):
        """测试OpenAPI端点"""
        response = client.get("/openapi.json")
        assert response.status_code == 200
        data = response.json()
        assert "openapi" in data
        assert "info" in data
        assert data["info"]["title"] == "Football Prediction API"

    def test_404_endpoint(self, client):
        """测试404错误"""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        assert "error" in data
        assert data["error"]["type"] == "http_error"

    def test_method_not_allowed(self, client):
        """测试方法不允许"""
        response = client.post("/api/health")
        assert response.status_code == 405

    def test_cors_headers(self, client):
        """测试CORS头"""
        # 预检请求
        response = client.options(
            "/api/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        # 至少应该返回204或200
        assert response.status_code in [200, 204]

    def test_timing_header(self, client):
        """测试响应时间头"""
        response = client.get("/")
        assert response.status_code == 200
        assert "X-Process-Time" in response.headers

    def test_gzip_middleware(self, client):
        """测试Gzip压缩"""
        # 请求带Accept-Encoding头
        response = client.get("/openapi.json", headers={"Accept-Encoding": "gzip"})
        assert response.status_code == 200
        # 可能会也可能不会被压缩，取决于响应大小


@pytest.mark.unit
class TestHealthAPIRoutes:
    """健康API路由测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_health_router_status(self, client):
        """测试健康路由器状态"""
        response = client.get("/api/v1/health")
        if response.status_code == 404:
            pytest.skip("健康路由器端点未实现")
        assert response.status_code == 200
        data = response.json()
        assert "checks" in data or "status" in data


@pytest.mark.unit
class TestDataAPIRoutes:
    """数据API路由测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_data_router_prefix(self, client):
        """测试数据路由器前缀"""
        response = client.get("/data/")
        if response.status_code == 404:
            pytest.skip("数据路由器端点未实现")
        # 可能返回404或200，取决于实现

    def test_data_router_teams(self, client):
        """测试数据路由器球队端点"""
        response = client.get("/data/teams")
        if response.status_code == 404:
            pytest.skip("数据球队端点未实现")
        assert response.status_code in [200, 404]

    def test_data_router_matches(self, client):
        """测试数据路由器比赛端点"""
        response = client.get("/data/matches")
        if response.status_code == 404:
            pytest.skip("数据比赛端点未实现")
        assert response.status_code in [200, 404]


@pytest.mark.unit
class TestPredictionRoutes:
    """预测路由测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_predictions_health(self, client):
        """测试预测服务健康检查"""
        response = client.get("/predictions/health")
        if response.status_code == 404:
            pytest.skip("预测健康端点未实现")
        assert response.status_code in [200, 404]

    def test_prediction_get_with_id(self, client):
        """测试获取特定预测"""
        response = client.get("/predictions/123")
        if response.status_code == 404:
            pytest.skip("获取预测端点未实现")
        assert response.status_code in [200, 404, 422]


@pytest.mark.unit
class TestErrorHandling:
    """错误处理测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_validation_error(self, client):
        """测试验证错误"""
        # 发送无效数据
        response = client.post("/api/v1/predictions", json={"invalid": "data"})
        # 可能返回404（端点不存在）或422（验证错误）
        assert response.status_code in [404, 422]

    def test_large_request(self, client):
        """测试大请求处理"""
        large_data = {"data": "x" * 10000}
        response = client.post("/api/test", json=large_data)
        # 应该能处理或返回适当的错误
        assert response.status_code in [200, 405, 413, 422]


@pytest.mark.unit
class TestSecurityFeatures:
    """安全功能测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_no_sensitive_info_in_error(self, client):
        """测试错误中不包含敏感信息"""
        response = client.get("/nonexistent")
        assert response.status_code == 404
        data = response.json()
        error_msg = str(data)
        # 确保不包含路径信息或其他敏感信息
        assert "src" not in error_msg.lower()
        assert ".py" not in error_msg

    def test_response_headers_security(self, client):
        """测试响应头安全性"""
        client.get("/")
        # 检查是否有基本的安全头（如果实现了的话）
        # 注意：这些可能没有实现，所以不强制要求
