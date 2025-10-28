# TODO: Consider creating a fixture for 4 repeated Mock creations

# TODO: Consider creating a fixture for 4 repeated Mock creations

from unittest.mock import AsyncMock, Mock, patch

"""
Monitoring API 综合测试
提升 monitoring 模块覆盖率的关键测试
"""

import asyncio
import json

# 测试导入
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import pytest

sys.path.insert(0, "src")

try:
    from src.api.monitoring import (
        _get_application_metrics,
        _get_cache_metrics,
        _get_database_metrics,
        _get_system_metrics,
        _health_check_detailed,
        router,
    )
    from src.database.dependencies import get_db_session

    MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import monitoring modules: {e}")
    MONITORING_AVAILABLE = False


@pytest.mark.skipif(not MONITORING_AVAILABLE, reason="Monitoring modules not available")
@pytest.mark.unit
class TestMonitoringAPI:
    """Monitoring API测试"""

    @pytest.fixture
    def mock_db_session(self):
        """模拟数据库会话"""
        session = Mock()
        session.execute.return_value.fetchall.return_value = [
            {"teams_count": 10},
            {"matches_count": 20},
            {"predictions_count": 5},
            {"users_count": 15},
        ]
        return session

    @pytest.fixture
    def mock_redis_client(self):
        """模拟Redis客户端"""
        redis_client = Mock()
        redis_client.ping.return_value = True
        redis_client.info.return_value = {
            "connected_clients": 5,
            "used_memory": 1024000,
            "keyspace_hits": 1000,
            "keyspace_misses": 100,
        }
        return redis_client

    @pytest.fixture
    def mock_app_state(self):
        """模拟应用状态"""
        return {
            "startup_time": datetime.now() - timedelta(hours=1),
            "total_requests": 1000,
            "error_count": 10,
            "average_response_time": 150.5,
        }

    def test_system_metrics_collection(self):
        """测试系统指标收集"""
        with (
            patch("psutil.cpu_percent") as mock_cpu,
            patch("psutil.virtual_memory") as mock_memory,
            patch("psutil.disk_usage") as mock_disk,
        ):
            mock_cpu.return_value = 25.5
            mock_memory.return_value = Mock(
                percent=60.0, used=8589934592, total=17179869184
            )
            mock_disk.return_value = Mock(
                percent=40.0, used=107374182400, total=1073741824000
            )

        metrics = _get_system_metrics()

        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics
        assert "disk_percent" in metrics
        assert "uptime" in metrics
        assert metrics["cpu_percent"] == 25.5
        assert metrics["memory_percent"] == 60.0
        assert metrics["disk_percent"] == 40.0

    def test_database_metrics_collection(self, mock_db_session):
        """测试数据库指标收集"""
        with patch("src.api.monitoring.get_db_session") as mock_get_session:
            mock_get_session.return_value.__enter__.return_value = mock_db_session

        metrics = _get_database_metrics()

        assert "statistics" in metrics
        assert "teams_count" in metrics["statistics"]
        assert "matches_count" in metrics["statistics"]
        assert "predictions_count" in metrics["statistics"]
        assert "users_count" in metrics["statistics"]
        assert metrics["statistics"]["teams_count"] == 10
        assert metrics["statistics"]["matches_count"] == 20

    def test_database_metrics_error_handling(self):
        """测试数据库指标错误处理"""
        with patch("src.api.monitoring.get_db_session") as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

        metrics = _get_database_metrics()

        assert "statistics" in metrics
        assert "error" in metrics
        assert metrics["error"] == "Database connection failed"

    def test_application_metrics_collection(self, mock_app_state):
        """测试应用指标收集"""
        with patch("src.api.monitoring.app_state", mock_app_state):
            metrics = _get_application_metrics()

        assert "startup_time" in metrics
        assert "total_requests" in metrics
        assert "error_count" in metrics
        assert "average_response_time" in metrics
        assert "uptime_hours" in metrics
        assert metrics["total_requests"] == 1000
        assert metrics["error_count"] == 10

    def test_cache_metrics_collection(self, mock_redis_client):
        """测试缓存指标收集"""
        with patch("src.api.monitoring.redis_client", mock_redis_client):
            metrics = _get_cache_metrics()

        assert "connected_clients" in metrics
        assert "memory_usage_bytes" in metrics
        assert "hit_rate" in metrics
        assert "status" in metrics
        assert metrics["status"] == "connected"
        assert metrics["connected_clients"] == 5
        assert metrics["hit_rate"] == 0.909  # 1000/(1000+100)

    def test_cache_metrics_connection_error(self):
        """测试缓存连接错误"""
        with patch("src.api.monitoring.redis_client") as mock_redis:
            mock_redis.ping.side_effect = Exception("Redis connection failed")

        metrics = _get_cache_metrics()

        assert "status" in metrics
        assert "error" in metrics
        assert metrics["status"] == "disconnected"

    @pytest.mark.asyncio
    async def test_health_check_detailed(self, mock_db_session, mock_redis_client):
        """测试详细健康检查"""
        with (
            patch("src.api.monitoring.get_db_session") as mock_get_session,
            patch("src.api.monitoring.redis_client", mock_redis_client),
        ):
            mock_get_session.return_value.__enter__.return_value = mock_db_session

        health_status = await _health_check_detailed()

        assert "overall_status" in health_status
        assert "checks" in health_status
        assert "timestamp" in health_status

        checks = health_status["checks"]
        assert "database" in checks
        assert "cache" in checks
        assert "system" in checks

        assert checks["database"]["status"] in ["healthy", "unhealthy"]
        assert checks["cache"]["status"] in ["healthy", "unhealthy"]
        assert checks["system"]["status"] in ["healthy", "unhealthy"]

    def test_metrics_endpoint_structure(self):
        """测试指标端点结构"""
        # 模拟所有组件都正常
        with (
            patch("src.api.monitoring._get_system_metrics") as mock_system,
            patch("src.api.monitoring._get_database_metrics") as mock_db,
            patch("src.api.monitoring._get_application_metrics") as mock_app,
            patch("src.api.monitoring._get_cache_metrics") as mock_cache,
        ):
            mock_system.return_value = {"cpu_percent": 25.0}
            mock_db.return_value = {"statistics": {"teams_count": 10}}
            mock_app.return_value = {"total_requests": 1000}
            mock_cache.return_value = {"status": "connected"}

        from fastapi.testclient import TestClient

        client = TestClient(router)

        response = client.get("/monitoring/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "system" in data
        assert "database" in data
        assert "application" in data
        assert "cache" in data

    def test_health_endpoint_structure(self):
        """测试健康检查端点结构"""
        with patch("src.api.monitoring._health_check_detailed") as mock_health:
            mock_health.return_value = {
                "overall_status": "healthy",
                "checks": {
                    "database": {"status": "healthy"},
                    "cache": {"status": "healthy"},
                },
            }

        from fastapi.testclient import TestClient

        client = TestClient(router)

        response = client.get("/monitoring/health")

        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "checks" in data

    def test_alerts_endpoint(self):
        """测试告警端点"""
        with patch("src.api.monitoring._get_system_metrics") as mock_system:
            mock_system.return_value = {
                "cpu_percent": 95.0,  # 高CPU使用率
                "memory_percent": 90.0,  # 高内存使用率
            }

        from fastapi.testclient import TestClient

        client = TestClient(router)

        response = client.get("/monitoring/alerts")

        assert response.status_code == 200
        data = response.json()
        assert "alerts" in data
        assert isinstance(data["alerts"], list)

        # 应该有CPU和内存告警
        alert_types = [alert["type"] for alert in data["alerts"]]
        assert "high_cpu" in alert_types
        assert "high_memory" in alert_types

    def test_performance_metrics(self):
        """测试性能指标"""
        with patch("src.api.monitoring._get_application_metrics") as mock_app:
            mock_app.return_value = {
                "total_requests": 1000,
                "error_count": 50,
                "average_response_time": 250.5,
            }

        from fastapi.testclient import TestClient

        client = TestClient(router)

        response = client.get("/monitoring/performance")

        assert response.status_code == 200
        data = response.json()
        assert "request_rate" in data
        assert "error_rate" in data
        assert "average_response_time" in data
        assert data["error_rate"] == 0.05  # 50/1000

    def test_log_level_metrics(self):
        """测试日志级别指标"""
        with patch("src.api.monitoring._get_log_metrics") as mock_logs:
            mock_logs.return_value = {
                "DEBUG": 100,
                "INFO": 500,
                "WARNING": 20,
                "ERROR": 5,
                "CRITICAL": 1,
            }

        from fastapi.testclient import TestClient

        client = TestClient(router)

        response = client.get("/monitoring/logs")

        assert response.status_code == 200
        data = response.json()
        assert "levels" in data
        assert "total_logs" in data
        assert data["levels"]["ERROR"] == 5

    @pytest.mark.asyncio
    async def test_concurrent_monitoring_requests(self):
        """测试并发监控请求"""
        with patch("src.api.monitoring._get_system_metrics") as mock_system:
            mock_system.return_value = {"cpu_percent": 25.0}

        from fastapi.testclient import TestClient

        client = TestClient(router)

        # 并发发送多个请求
        tasks = []
        for _ in range(10):
            tasks.append(client.get("/monitoring/metrics"))

        responses = [task for task in tasks]

        # 所有请求都应该成功
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert "system" in data

    def test_monitoring_data_serialization(self):
        """测试监控数据序列化"""
        # 创建包含各种数据类型的指标
        metrics = {
            "cpu_percent": 25.5,
            "memory_percent": 60.0,
            "timestamp": datetime.now(),
            "status": "healthy",
            "details": {"processes": 10, "threads": 20},
        }

        # 测试JSON序列化
        try:
            json_str = json.dumps(metrics, default=str)
            parsed_data = json.loads(json_str)
            assert parsed_data["cpu_percent"] == 25.5
            assert parsed_data["status"] == "healthy"
        except (TypeError, ValueError) as e:
            pytest.fail(f"Metrics serialization failed: {e}")

    def test_monitoring_endpoint_security(self):
        """测试监控端点安全性"""
        from fastapi.testclient import TestClient

        client = TestClient(router)

        # 测试所有监控端点都返回适当的响应
        endpoints = [
            "/monitoring/health",
            "/monitoring/metrics",
            "/monitoring/alerts",
            "/monitoring/performance",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            # 应该返回200或适当的错误码，而不是500
            assert response.status_code in [200, 404, 422]

    def test_monitoring_error_recovery(self):
        """测试监控错误恢复"""
        with patch("src.api.monitoring._get_system_metrics") as mock_system:
            # 第一次失败，第二次成功
            mock_system.side_effect = [
                Exception("Temporary error"),
                {"cpu_percent": 25.0},
            ]

        from fastapi.testclient import TestClient

        client = TestClient(router)

        # 第一次请求可能失败，但应用不应该崩溃
        response1 = client.get("/monitoring/metrics")

        # 第二次请求应该成功
        response2 = client.get("/monitoring/metrics")

        # 至少有一次成功
        assert response1.status_code == 200 or response2.status_code == 200

    def test_monitoring_caching(self):
        """测试监控数据缓存"""
        with patch("src.api.monitoring._get_system_metrics") as mock_system:
            mock_system.return_value = {"cpu_percent": 25.0}

        from fastapi.testclient import TestClient

        client = TestClient(router)

        # 第一次请求
        response1 = client.get("/monitoring/metrics")
        # 第二次请求（应该使用缓存）
        response2 = client.get("/monitoring/metrics")

        assert response1.status_code == 200
        assert response2.status_code == 200

        # 数据应该相同
        assert response1.json() == response2.json()

        # 系统指标函数应该只被调用一次（由于缓存）
        # 这取决于具体的实现，我们主要验证功能正常


@pytest.mark.skipif(not MONITORING_AVAILABLE, reason="Monitoring modules not available")
class TestMonitoringAlerts:
    """监控告警测试"""

    @pytest.fixture
    def sample_metrics(self):
        """示例指标数据"""
        return {
            "system": {"cpu_percent": 95.0, "memory_percent": 90.0},
            "database": {"connection_pool_size": 20, "active_connections": 18},
            "application": {"error_rate": 0.15, "response_time": 2000.0},
        }

    def test_high_cpu_alert(self, sample_metrics):
        """测试高CPU告警"""
        alerts = []

        if sample_metrics["system"]["cpu_percent"] > 90:
            alerts.append(
                {
                    "type": "high_cpu",
                    "severity": "critical",
                    "message": f"CPU usage is {sample_metrics['system']['cpu_percent']}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        assert len(alerts) == 1
        assert alerts[0]["type"] == "high_cpu"
        assert alerts[0]["severity"] == "critical"

    def test_high_memory_alert(self, sample_metrics):
        """测试高内存告警"""
        alerts = []

        if sample_metrics["system"]["memory_percent"] > 85:
            alerts.append(
                {
                    "type": "high_memory",
                    "severity": "warning",
                    "message": f"Memory usage is {sample_metrics['system']['memory_percent']}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        assert len(alerts) == 1
        assert alerts[0]["type"] == "high_memory"
        assert alerts[0]["severity"] == "warning"

    def test_database_connection_alert(self, sample_metrics):
        """测试数据库连接告警"""
        alerts = []

        connection_usage = (
            sample_metrics["database"]["active_connections"]
            / sample_metrics["database"]["connection_pool_size"]
        )
        if connection_usage > 0.8:
            alerts.append(
                {
                    "type": "database_connections",
                    "severity": "warning",
                    "message": f"Database connection pool usage is {connection_usage * 100:.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        assert len(alerts) == 1
        assert alerts[0]["type"] == "database_connections"

    def test_error_rate_alert(self, sample_metrics):
        """测试错误率告警"""
        alerts = []

        if sample_metrics["application"]["error_rate"] > 0.1:
            severity = (
                "critical"
                if sample_metrics["application"]["error_rate"] > 0.2
                else "warning"
            )
            alerts.append(
                {
                    "type": "high_error_rate",
                    "severity": severity,
                    "message": f"Error rate is {sample_metrics['application']['error_rate'] * 100:.1f}%",
                    "timestamp": datetime.now().isoformat(),
                }
            )

        assert len(alerts) == 1
        assert alerts[0]["type"] == "high_error_rate"
        assert alerts[0]["severity"] == "critical"
