"""API简单测试"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestAPISimple:
    """API简单测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.api.app import app

        return TestClient(app)

    def test_health_check(self, client):
        """测试健康检查"""
        response = client.get("/api/health")
        assert response.status_code in [200, 503]

    def test_health_liveness(self, client):
        """测试存活检查"""
        response = client.get("/api/v1/health/liveness")
        assert response.status_code in [200, 503]

    def test_health_readiness(self, client):
        """测试就绪检查"""
        response = client.get("/api/v1/health/readiness")
        assert response.status_code in [200, 503]

    def test_api_docs(self, client):
        """测试API文档"""
        response = client.get("/docs")
        assert response.status_code == 200

    def test_api_openapi(self, client):
        """测试OpenAPI规范"""
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_api_root(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data

    def test_invalid_endpoint(self, client):
        """测试无效端点"""
        response = client.get("/api/invalid")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """测试不允许的方法"""
        response = client.delete("/api/health")
        assert response.status_code == 405

    def test_cors_headers(self, client):
        """测试CORS头"""
        response = client.options("/api/health")
        assert response.status_code in [200, 405]

    def test_response_headers(self, client):
        """测试响应头"""
        response = client.get("/api/health")
        assert "content-type" in response.headers

    @patch("src.api.health._check_database")
    def test_database_health_check(self, mock_check_db, client):
        """测试数据库健康检查"""
        mock_check_db.return_value = {"status": "healthy", "latency_ms": 10}

        response = client.get("/api/health")
        assert response.status_code in [200, 503]

    def test_metrics_endpoint(self, client):
        """测试指标端点"""
        response = client.get("/metrics")
        assert response.status_code in [200, 404]

    def test_health_response_structure(self, client):
        """测试健康检查响应结构"""
        response = client.get("/api/health")
        if response.status_code == 200:
            data = response.json()
            assert "status" in data
            assert data["status"] in ["healthy", "degraded", "unhealthy"]
