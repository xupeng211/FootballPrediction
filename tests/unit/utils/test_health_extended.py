"""API健康检查扩展测试"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock


class TestAPIHealthExtended:
    """API健康检查扩展测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.api.app import app

        return TestClient(app)

    def test_health_check_all_components(self, client):
        """测试健康检查所有组件"""
        with (
            patch("src.api.health.check_database_health") as mock_db,
            patch("src.api.health.check_redis_health") as mock_redis,
            patch("src.api.health.check_kafka_health") as mock_kafka,
        ):
            mock_db.return_value = {"status": "healthy", "latency_ms": 10}
            mock_redis.return_value = {"status": "healthy", "latency_ms": 5}
            mock_kafka.return_value = {"status": "healthy", "latency_ms": 20}

            response = client.get("/api/health")
            assert response.status_code == 200
            _data = response.json()
            assert data["status"] == "healthy"
            assert "checks" in data

    def test_health_check_database_failure(self, client):
        """测试数据库健康检查失败"""
        with patch("src.api.health.check_database_health") as mock_db:
            mock_db.return_value = {
                "status": "unhealthy",
                "error": "Connection timeout",
            }

            response = client.get("/api/health")
            assert response.status_code == 503

    def test_health_check_with_middleware(self, client):
        """测试带中间件的健康检查"""
        response = client.get("/api/health", headers={"X-Request-ID": "test-123"})
        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

    def test_health_metrics(self, client):
        """测试健康指标端点"""
        response = client.get("/api/health/metrics")
        assert response.status_code == 200
        _data = response.json()
        assert "uptime" in data
        assert "version" in data
