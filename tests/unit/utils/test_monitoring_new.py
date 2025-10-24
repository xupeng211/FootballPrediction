from unittest.mock import patch, MagicMock
"""API监控端点测试"""

import pytest
from fastapi.testclient import TestClient
import time


@pytest.mark.unit
@pytest.mark.monitoring

class TestAPIMonitoring:
    """API监控端点测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        from src.api.app import app

        return TestClient(app)

    def test_get_metrics(self, client):
        """测试获取系统指标"""
        with patch("src.api.monitoring.get_system_metrics") as mock_metrics:
            mock_metrics.return_value = {
                "cpu_usage": 45.2,
                "memory_usage": 68.5,
                "disk_usage": 32.1,
                "active_connections": 125,
                "requests_per_second": 15.3,
            }

            response = client.get("/api/monitoring/metrics")
            assert response.status_code == 200
            _data = response.json()
            assert "cpu_usage" in _data

            assert isinstance(_data["cpu_usage"], (int, float))

    def test_get_performance_stats(self, client):
        """测试获取性能统计"""
        with patch("src.api.monitoring.get_performance_stats") as mock_stats:
            mock_stats.return_value = {
                "avg_response_time": 0.125,
                "p95_response_time": 0.250,
                "p99_response_time": 0.500,
                "total_requests": 10000,
                "error_rate": 0.02,
            }

            response = client.get("/api/monitoring/performance")
            assert response.status_code == 200
            _data = response.json()
            assert "avg_response_time" in _data

    def test_get_alerts(self, client):
        """测试获取告警信息"""
        with patch("src.api.monitoring.get_active_alerts") as mock_alerts:
            mock_alerts.return_value = [
                {
                    "id": 1,
                    "type": "high_cpu",
                    "message": "CPU usage above 80%",
                    "severity": "warning",
                    "timestamp": "2024-01-01T12:00:00Z",
                }
            ]

            response = client.get("/api/monitoring/alerts")
            assert response.status_code == 200
            _data = response.json()
            assert len(data) == 1
            assert _data[0]["type"] == "high_cpu"

    def test_trigger_alert(self, client):
        """测试触发告警"""
        alert_data = {"type": "custom", "message": "Test alert", "severity": "info"}

        with patch("src.api.monitoring.trigger_alert") as mock_trigger:
            mock_trigger.return_value = {"id": 999, "status": "triggered"}

            response = client.post("/api/monitoring/alerts", json=alert_data)
            assert response.status_code == 201
            _data = response.json()
            assert _data["status"] == "triggered"

    def test_acknowledge_alert(self, client):
        """测试确认告警"""
        with patch("src.api.monitoring.acknowledge_alert") as mock_ack:
            mock_ack.return_value = {"status": "acknowledged"}

            response = client.post("/api/monitoring/alerts/1/acknowledge")
            assert response.status_code == 200
            _data = response.json()
            assert _data["status"] == "acknowledged"

    def test_health_check_with_metrics(self, client):
        """测试带指标的健康检查"""
        with patch("src.api.monitoring.get_health_summary") as mock_health:
            mock_health.return_value = {
                "status": "healthy",
                "checks": {
                    "database": {"status": "healthy", "response_time": 10},
                    "redis": {"status": "healthy", "response_time": 5},
                    "kafka": {"status": "degraded", "response_time": 200},
                },
                "metrics": {"uptime": 86400, "version": "1.0.0"},
            }

            response = client.get("/api/monitoring/health")
            assert response.status_code == 200
            _data = response.json()
            assert _data["status"] in ["healthy", "degraded", "unhealthy"]
            assert "checks" in _data
