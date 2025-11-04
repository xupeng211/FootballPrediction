"""
健康检查API测试
Health Check API Tests

测试健康检查相关的API端点。
"""

from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# 直接导入健康检查路由，避免有问题的依赖
from src.api.health.routes import router as health_router


class TestHealthAPI:
    """健康检查API测试"""

    @pytest.fixture
    def health_client(self):
        """创建健康检查客户端"""
        app = FastAPI()
        app.include_router(health_router)
        return TestClient(app)

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
        with patch("src.api.health.routes.datetime") as mock_datetime:
            mock_now = datetime(2024, 1, 1, 12, 0, 0)
            mock_datetime.utcnow.return_value = mock_now

            response = health_client.get("/health/")
            assert response.status_code == 200

            data = response.json()
            assert data["timestamp"] == mock_now.isoformat()

    def test_concurrent_health_checks(self, health_client):
        """测试并发健康检查"""
        import threading

        results = []

        def make_request():
            response = health_client.get("/health/")
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

    def test_health_check_response_time(self, health_client):
        """测试健康检查响应时间"""
        import time

        start_time = time.time()
        response = health_client.get("/health/")
        end_time = time.time()

        response_time = end_time - start_time

        # 健康检查应该在合理时间内响应（< 1秒）
        assert response_time < 1.0, f"Health check too slow: {response_time}s"
        assert response.status_code == 200

    def test_health_check_content_type(self, health_client):
        """测试健康检查内容类型"""
        response = health_client.get("/health/")
        assert response.status_code == 200

        content_type = response.headers.get("content-type", "")
        assert "application/json" in content_type

    def test_health_check_headers(self, health_client):
        """测试健康检查响应头"""
        response = health_client.get("/health/")
        assert response.status_code == 200

        # 验证基本响应头
        headers = response.headers
        assert "content-type" in headers
        assert "content-length" in headers


class TestHealthAPIErrorHandling:
    """健康检查API错误处理测试"""

    @pytest.fixture
    def health_client(self):
        """创建健康检查客户端"""
        app = FastAPI()
        app.include_router(health_router)
        return TestClient(app)

    def test_invalid_endpoint(self, health_client):
        """测试无效端点"""
        response = health_client.get("/health/invalid")
        assert response.status_code == 404

    def test_method_not_allowed(self, health_client):
        """测试方法不允许"""
        response = health_client.post("/health/")
        # 可能是405或其他状态码
        assert response.status_code in [405, 422, 404]

    def test_health_with_query_params(self, health_client):
        """测试带查询参数的健康检查"""
        response = health_client.get("/health/?format=json")
        # 应该忽略未知参数或正常处理
        assert response.status_code == 200

        data = response.json()
        assert "status" in data


class TestHealthAPIDocumentation:
    """健康检查API文档测试"""

    @pytest.fixture
    def health_client(self):
        """创建健康检查客户端"""
        app = FastAPI()
        app.include_router(health_router)
        return TestClient(app)

    def test_health_endpoint_tags(self, health_client):
        """测试健康检查端点标签"""
        # 通过检查路由配置验证标签
        app = health_client.app
        routes = app.routes

        health_routes = [route for route in routes if "/health" in route.path]
        assert len(health_routes) > 0

    def test_health_endpoint_path(self, health_client):
        """测试健康检查端点路径"""
        response = health_client.get("/health/")
        assert response.status_code == 200

        # 验证路径结构
        assert "/health/" in response.url


# 测试工具函数
def create_health_test_app():
    """创建健康检查测试应用"""
    from fastapi import FastAPI

    from src.api.health.routes import router as health_router

    app = FastAPI()
    app.include_router(health_router)
    return app


def create_test_client():
    """创建测试客户端"""
    app = create_health_test_app()
    return TestClient(app)
