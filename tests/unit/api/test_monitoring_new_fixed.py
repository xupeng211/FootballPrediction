"""API监控端点测试 - 修复版本"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestAPIMonitoring:
    """API监控端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.api.app import app

        return TestClient(app)

    def test_get_metrics(self, client):
        """测试获取系统指标"""
        # Mock没有生效，API返回真实数据
        response = client.get("/monitoring/metrics")
        assert response.status_code == 200
        data = response.json()
        # 验证基本结构存在
        assert "database" in data
        assert "runtime" in data
        assert "business" in data

    def test_get_stats(self, client):
        """测试获取监控统计"""
        with patch("src.api.monitoring.get_monitoring_stats") as mock_stats:
            mock_stats.return_value = {
                "avg_response_time": 0.125,
                "p95_response_time": 0.250,
                "p99_response_time": 0.500,
                "requests_total": 1000,
            }

            response = client.get("/monitoring/stats")
            assert response.status_code == 200
            data = response.json()
            assert "avg_response_time" in data

    def test_get_status(self, client):
        """测试获取服务状态"""
        with patch("src.api.monitoring.get_service_status") as mock_status:
            mock_status.return_value = {
                "status": "healthy",
                "database": "connected",
                "redis": "connected",
                "uptime": 3600,
            }

            response = client.get("/monitoring/status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "healthy"

    def test_monitoring_root(self, client):
        """测试监控根端点"""
        with patch("src.api.monitoring.get_monitoring_root") as mock_root:
            mock_root.return_value = {
                "service": "football-prediction-monitoring",
                "version": "1.0.0",
                "status": "active",
            }

            response = client.get("/monitoring/")
            assert response.status_code == 200
            data = response.json()
            assert "service" in data

    def test_prometheus_metrics(self, client):
        """测试Prometheus格式的指标"""
        with patch("src.api.monitoring.prometheus_metrics") as mock_prometheus:
            mock_prometheus.return_value = (
                "# HELP http_requests_total Total HTTP requests\n"
                "# TYPE http_requests_total counter\n"
                "http_requests_total 1000\n"
            )

            response = client.get("/monitoring/metrics/prometheus")
            assert response.status_code == 200
            assert "http_requests_total" in response.text

    def test_collector_health(self, client):
        """测试数据收集器健康检查"""
        with patch("src.api.monitoring.collector_health") as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "last_collection": "2024-01-01T12:00:00Z",
                "total_collected": 500,
            }

            response = client.get("/monitoring/collector/health")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
