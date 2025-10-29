"""
API 简单测试
测试基本的API功能
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """创建FastAPI应用实例"""
    app = FastAPI(title="Test API")

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    return app


@pytest.fixture
def client(app):
    """创建测试客户端"""
    return TestClient(app)


class TestBasicAPI:
    """基本API测试"""

    def test_root_endpoint(self, client):
        """测试根端点"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert data["message"] == "Hello World"

    def test_health_endpoint(self, client):
        """测试健康检查端点"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"

    def test_404_endpoint(self, client):
        """测试404端点"""
        response = client.get("/nonexistent")
        assert response.status_code == 404