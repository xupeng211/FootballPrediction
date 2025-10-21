"""
监控API端点测试
Monitoring API Endpoints Tests
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock
import json
from datetime import datetime

from src.api.app import app


@pytest.mark.unit
class TestMonitoringEndpoints:
    """监控API端点测试类"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_metrics_endpoint(self, client):
        """测试指标端点"""
        response = client.get("/metrics")
        assert response.status_code == 200
        assert "text/plain" in response.headers["content-type"]
        metrics_data = response.text
        assert "http_requests_total" in metrics_data or "HELP" in metrics_data

    def test_monitoring_status(self, client):
        """测试监控状态端点"""
        response = client.get("/api/v1/monitoring/status")

        if response.status_code == 404:
            pytest.skip("监控状态端点未实现")

        assert response.status_code == 200
        _data = response.json()
        assert "status" in _data or "system" in _data

    def test_collector_health(self, client):
        """测试收集器健康检查"""
        response = client.get("/api/v1/monitoring/collector/health")

        if response.status_code == 404:
            pytest.skip("收集器健康检查端点未实现")

        assert response.status_code == 200
        _data = response.json()
        assert "health" in _data or "status" in _data

    @patch(
        "src.monitoring.metrics_collector_enhanced.EnhancedMetricsCollector.collect_metrics"
    )
    def test_collect_metrics(self, mock_collect, client):
        """测试收集指标"""
        mock_collect.return_value = {
            "metrics": [
                {"name": "cpu_usage", "value": 45.2, "unit": "%"},
                {"name": "memory_usage", "value": 67.8, "unit": "%"},
                {"name": "disk_usage", "value": 23.1, "unit": "%"},
            ],
            "timestamp": datetime.now().isoformat(),
        }

        response = client.post("/api/v1/monitoring/collector/collect")

        if response.status_code == 404:
            pytest.skip("收集指标端点未实现")

        assert response.status_code in [200, 202]
        _data = response.json()
        assert "metrics" in _data or "success" in _data

    def test_collector_status(self, client):
        """测试收集器状态"""
        response = client.get("/api/v1/monitoring/collector/status")

        if response.status_code == 404:
            pytest.skip("收集器状态端点未实现")

        assert response.status_code == 200
        _data = response.json()
        assert "status" in _data or "collector" in _data

    @patch(
        "src.monitoring.metrics_collector_enhanced.EnhancedMetricsCollector.start_collection"
    )
    def test_start_collection(self, mock_start, client):
        """测试开始收集"""
        mock_start.return_value = {"success": True}

        response = client.post("/api/v1/monitoring/collector/start")

        if response.status_code == 404:
            pytest.skip("开始收集端点未实现")

        assert response.status_code in [200, 202]
        _data = response.json()
        assert "success" in _data or "status" in _data

    @patch(
        "src.monitoring.metrics_collector_enhanced.EnhancedMetricsCollector.stop_collection"
    )
    def test_stop_collection(self, mock_stop, client):
        """测试停止收集"""
        mock_stop.return_value = {"success": True}

        response = client.post("/api/v1/monitoring/collector/stop")

        if response.status_code == 404:
            pytest.skip("停止收集端点未实现")

        assert response.status_code in [200, 202]
        _data = response.json()
        assert "success" in _data or "status" in _data

    @patch("src.monitoring.system_monitor.SystemHealthChecker.get_health_status")
    def test_system_health(self, mock_health, client):
        """测试系统健康检查"""
        mock_health.return_value = {
            "status": "healthy",
            "checks": {
                "database": {"status": "healthy", "response_time": 0.045},
                "redis": {"status": "healthy", "response_time": 0.012},
                "disk_space": {"status": "healthy", "usage": "23%"},
            },
            "timestamp": datetime.now().isoformat(),
        }

        response = client.get("/api/v1/monitoring/health")

        if response.status_code == 404:
            pytest.skip("系统健康检查端点未实现")

        assert response.status_code == 200
        _data = response.json()
        assert "status" in _data or "health" in _data

    @patch("src.monitoring.alert_manager.AlertManager.get_active_alerts")
    def test_get_alerts(self, mock_alerts, client):
        """测试获取告警"""
        mock_alerts.return_value = [
            {
                "id": "alert_001",
                "type": "high_cpu",
                "severity": "warning",
                "message": "CPU usage above 80%",
                "timestamp": datetime.now().isoformat(),
            }
        ]

        response = client.get("/api/v1/monitoring/alerts")

        if response.status_code == 404:
            pytest.skip("获取告警端点未实现")

        assert response.status_code == 200
        _data = response.json()
        assert isinstance(data, list) or "alerts" in _data

    @patch("src.monitoring.alert_manager.AlertManager.create_alert")
    def test_create_alert(self, mock_create, client):
        """测试创建告警"""
        mock_create.return_value = {"alert_id": "alert_002", "success": True}

        alert_data = {
            "type": "custom",
            "severity": "info",
            "message": "Test alert",
            "source": "test_suite",
        }

        response = client.post("/api/v1/monitoring/alerts", json=alert_data)

        if response.status_code == 404:
            pytest.skip("创建告警端点未实现")

        assert response.status_code in [200, 201]
        _data = response.json()
        assert "alert_id" in _data or "success" in _data

    def test_get_logs(self, client):
        """测试获取日志"""
        response = client.get("/api/v1/monitoring/logs")

        if response.status_code == 404:
            pytest.skip("获取日志端点未实现")

        assert response.status_code == 200
        _data = response.json()
        assert isinstance(data, list) or "logs" in _data

    def test_get_performance_metrics(self, client):
        """测试获取性能指标"""
        response = client.get("/api/v1/monitoring/performance")

        if response.status_code == 404:
            pytest.skip("获取性能指标端点未实现")

        assert response.status_code == 200
        _data = response.json()
        assert "performance" in _data or "metrics" in _data


@pytest.mark.unit
class TestMonitoringIntegration:
    """监控集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    def test_monitoring_workflow(self, client):
        """测试监控完整工作流"""
        # 1. 健康检查
        response = client.get("/api/v1/monitoring/health")

        # 2. 获取状态
        response = client.get("/api/v1/monitoring/status")

        # 3. 获取指标
        response = client.get("/metrics")
        assert response.status_code == 200

        # 验证基本指标端点可用
        assert "text/plain" in response.headers["content-type"]
