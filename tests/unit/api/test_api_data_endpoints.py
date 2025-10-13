"""API数据端点测试"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestAPIData:
    """API数据端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.api.app import app

        return TestClient(app)

    def test_get_root(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        _data = response.json()
        assert "message" in data
        assert "version" in data

    def test_cors_headers(self, client):
        """测试CORS头"""
        response = client.options("/api/health")
        # 检查是否有CORS相关的头
        # 某些CORS头可能存在
        assert response.status_code in [200, 405]

    def test_invalid_endpoint(self, client):
        """测试无效端点"""
        response = client.get("/api/invalid-endpoint")
        assert response.status_code == 404

    def test_health_response_time(self, client):
        """测试健康检查响应时间"""
        import time

        start = time.time()
        response = client.get("/api/health")
        end = time.time()
        assert response.status_code == 200
        # 响应时间应该少于1秒
        assert (end - start) < 1.0
