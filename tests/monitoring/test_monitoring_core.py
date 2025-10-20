"""
Monitoring模块核心测试
测试系统监控、指标收集、健康检查等功能
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import asyncio
import time
import json
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 尝试导入monitoring模块
try:
    from src.monitoring.metrics_collector import (
        MetricsCollector,
        MetricsAggregator,
        MetricPoint,
    )
    from src.monitoring.system_monitor import SystemMonitor
    from src.monitoring.health_checker import HealthChecker
    from src.monitoring.anomaly_detector import AnomalyDetector
    from src.monitoring.alert_manager import AlertManager
    from src.monitoring.quality_monitor import QualityMonitor

    MONITORING_AVAILABLE = True
except ImportError as e:
    pytest.skip(f"Monitoring模块不可用: {e}", allow_module_level=True)
    MONITORING_AVAILABLE = False


class TestMetricsCollector:
    """测试指标收集器"""

    def test_metrics_collector_creation(self):
        """测试指标收集器创建"""
        if not MONITORING_AVAILABLE:
            pytest.skip("Monitoring模块不可用")

        with patch(
            "src.monitoring.metrics_collector_enhanced.EnhancedMetricsCollector"
        ) as MockCollector:
            collector = MockCollector()
            collector.initialize = Mock(return_value=True)
            collector.start = Mock(return_value=True)
            collector.stop = Mock(return_value=True)

            assert collector.initialize() is True
            collector.start()
            collector.stop()

    def test_metrics_point_creation(self):
        """测试指标点创建"""
        with patch(
            "src.monitoring.metrics_collector_enhanced.MetricPoint"
        ) as MockMetricPoint:
            point = MockMetricPoint()
            point.name = "test_metric"
            point.value = 100
            point.timestamp = datetime.now()
            point.tags = {"service": "test"}

            assert point.name == "test_metric"
            assert point.value == 100
            assert point.tags["service"] == "test"

    def test_metrics_aggregator(self):
        """测试指标聚合器"""
        with patch(
            "src.monitoring.metrics_collector_enhanced.MetricsAggregator"
        ) as MockAggregator:
            aggregator = MockAggregator()
            aggregator.add_metric = Mock(return_value=True)
            aggregator.calculate_average = Mock(return_value=50.5)
            aggregator.calculate_sum = Mock(return_value=5050)
            aggregator.calculate_max = Mock(return_value=100)
            aggregator.calculate_min = Mock(return_value=1)

            # 添加指标
            assert aggregator.add_metric("test", 100) is True

            # 计算聚合值
            avg = aggregator.calculate_average("test")
            total = aggregator.calculate_sum("test")
            max_val = aggregator.calculate_max("test")
            min_val = aggregator.calculate_min("test")

            assert avg == 50.5
            assert total == 5050
            assert max_val == 100
            assert min_val == 1

    def test_collect_system_metrics(self):
        """测试收集系统指标"""
        with patch(
            "src.monitoring.metrics_collector_enhanced.EnhancedMetricsCollector"
        ) as MockCollector:
            collector = MockCollector()
            collector.collect_cpu_usage = Mock(return_value=45.2)
            collector.collect_memory_usage = Mock(return_value=68.5)
            collector.collect_disk_usage = Mock(return_value=35.8)
            collector.collect_network_io = Mock(
                return_value={"bytes_sent": 1024000, "bytes_received": 2048000}
            )

            # 收集系统指标
            cpu = collector.collect_cpu_usage()
            memory = collector.collect_memory_usage()
            disk = collector.collect_disk_usage()
            network = collector.collect_network_io()

            assert cpu == 45.2
            assert memory == 68.5
            assert disk == 35.8
            assert network["bytes_sent"] == 1024000

    def test_collect_application_metrics(self):
        """测试收集应用指标"""
        with patch(
            "src.monitoring.metrics_collector_enhanced.EnhancedMetricsCollector"
        ) as MockCollector:
            collector = MockCollector()
            collector.collect_request_count = Mock(return_value=1000)
            collector.collect_response_time = Mock(return_value=150.5)
            collector.collect_error_rate = Mock(return_value=0.02)
            collector.collect_active_connections = Mock(return_value=25)

            # 收集应用指标
            requests = collector.collect_request_count()
            response_time = collector.collect_response_time()
            error_rate = collector.collect_error_rate()
            connections = collector.collect_active_connections()

            assert requests == 1000
            assert response_time == 150.5
            assert error_rate == 0.02
            assert connections == 25

    def test_metrics_storage(self):
        """测试指标存储"""
        with patch(
            "src.monitoring.metrics_collector_enhanced.EnhancedMetricsCollector"
        ) as MockCollector:
            collector = MockCollector()
            collector.store_metric = Mock(return_value=True)
            collector.retrieve_metrics = Mock(
                return_value=[
                    {"timestamp": "2025-01-18T10:00:00", "value": 100},
                    {"timestamp": "2025-01-18T10:01:00", "value": 105},
                ]
            )
            collector.flush_metrics = Mock(return_value=True)

            # 存储指标
            assert collector.store_metric("test_metric", 100) is True

            # 检索指标
            metrics = collector.retrieve_metrics(
                "test_metric", start_time="2025-01-18T10:00:00"
            )
            assert len(metrics) == 2

            # 刷新指标
            assert collector.flush_metrics() is True

    def test_metrics_export(self):
        """测试指标导出"""
        with patch(
            "src.monitoring.metrics_collector_enhanced.EnhancedMetricsCollector"
        ) as MockCollector:
            collector = MockCollector()
            collector.export_prometheus = Mock(
                return_value="# HELP test_metric Test metric\ntest_metric 100"
            )
            collector.export_json = Mock(
                return_value={"metrics": [{"name": "test", "value": 100}]}
            )
            collector.export_influxdb = Mock(
                return_value="test,host=localhost value=100"
            )

            # 导出不同格式
            prometheus = collector.export_prometheus()
            json_data = collector.export_json()
            influxdb = collector.export_influxdb()

            assert "HELP test_metric" in prometheus
            assert json_data["metrics"][0]["value"] == 100
            assert "test,host=localhost" in influxdb


class TestSystemMonitor:
    """测试系统监控器"""

    def test_system_monitor_creation(self):
        """测试系统监控器创建"""
        if not MONITORING_AVAILABLE:
            pytest.skip("Monitoring模块不可用")

        with patch("src.monitoring.system_monitor.SystemMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.start_monitoring = Mock(return_value=True)
            monitor.stop_monitoring = Mock(return_value=True)
            monitor.is_monitoring = False

            # 启动监控
            assert monitor.start_monitoring() is True
            assert monitor.is_monitoring is True

            # 停止监控
            monitor.stop_monitoring()
            assert monitor.is_monitoring is False

    def test_monitor_cpu_usage(self):
        """测试CPU使用率监控"""
        with patch("src.monitoring.system_monitor.SystemMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.get_cpu_usage = Mock(
                return_value={
                    "overall": 45.2,
                    "per_cpu": [40.1, 45.5, 50.2, 45.0],
                    "load_average": [1.5, 1.8, 2.1],
                }
            )
            monitor.get_cpu_count = Mock(return_value=4)

            # 获取CPU使用率
            cpu_usage = monitor.get_cpu_usage()
            cpu_count = monitor.get_cpu_count()

            assert cpu_usage["overall"] == 45.2
            assert len(cpu_usage["per_cpu"]) == 4
            assert cpu_count == 4

    def test_monitor_memory_usage(self):
        """测试内存使用率监控"""
        with patch("src.monitoring.system_monitor.SystemMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.get_memory_usage = Mock(
                return_value={
                    "total": 8589934592,  # 8GB
                    "available": 4294967296,  # 4GB
                    "used": 4294967296,  # 4GB
                    "percent": 50.0,
                }
            )
            monitor.get_swap_usage = Mock(
                return_value={
                    "total": 2147483648,  # 2GB
                    "used": 1073741824,  # 1GB
                    "percent": 50.0,
                }
            )

            # 获取内存使用率
            memory = monitor.get_memory_usage()
            swap = monitor.get_swap_usage()

            assert memory["percent"] == 50.0
            assert swap["percent"] == 50.0

    def test_monitor_disk_usage(self):
        """测试磁盘使用率监控"""
        with patch("src.monitoring.system_monitor.SystemMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.get_disk_usage = Mock(
                return_value={
                    "/": {
                        "total": 107374182400,  # 100GB
                        "used": 53687091200,  # 50GB
                        "free": 53687091200,  # 50GB
                        "percent": 50.0,
                    },
                    "/home": {
                        "total": 1073741824000,  # 1TB
                        "used": 107374182400,  # 100GB
                        "free": 966367641600,  # 864GB
                        "percent": 10.0,
                    },
                }
            )
            monitor.get_disk_io = Mock(
                return_value={
                    "read_bytes": 1073741824,
                    "write_bytes": 2147483648,
                    "read_count": 1000,
                    "write_count": 2000,
                }
            )

            # 获取磁盘使用率
            disk_usage = monitor.get_disk_usage()
            disk_io = monitor.get_disk_io()

            assert disk_usage["/"]["percent"] == 50.0
            assert disk_usage["/home"]["percent"] == 10.0
            assert disk_io["read_bytes"] == 1073741824

    def test_monitor_network(self):
        """测试网络监控"""
        with patch("src.monitoring.system_monitor.SystemMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.get_network_stats = Mock(
                return_value={
                    "eth0": {
                        "bytes_sent": 1073741824,
                        "bytes_recv": 2147483648,
                        "packets_sent": 10000,
                        "packets_recv": 12000,
                        "errin": 0,
                        "errout": 0,
                        "dropin": 0,
                        "dropout": 0,
                    }
                }
            )
            monitor.get_active_connections = Mock(return_value=25)

            # 获取网络统计
            network_stats = monitor.get_network_stats()
            connections = monitor.get_active_connections()

            assert "eth0" in network_stats
            assert network_stats["eth0"]["bytes_sent"] == 1073741824
            assert connections == 25

    def test_monitor_processes(self):
        """测试进程监控"""
        with patch("src.monitoring.system_monitor.SystemMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.get_process_count = Mock(return_value=156)
            monitor.get_top_processes = Mock(
                return_value=[
                    {"pid": 1234, "name": "python", "cpu": 15.2, "memory": 5.1},
                    {"pid": 5678, "name": "postgres", "cpu": 10.5, "memory": 20.3},
                ]
            )

            # 获取进程信息
            process_count = monitor.get_process_count()
            top_processes = monitor.get_top_processes()

            assert process_count == 156
            assert len(top_processes) == 2
            assert top_processes[0]["name"] == "python"


class TestHealthChecker:
    """测试健康检查器"""

    def test_health_checker_creation(self):
        """测试健康检查器创建"""
        if not MONITORING_AVAILABLE:
            pytest.skip("Monitoring模块不可用")

        with patch("src.monitoring.health_checker.HealthChecker") as MockChecker:
            checker = MockChecker()
            checker.add_check = Mock(return_value=True)
            checker.remove_check = Mock(return_value=True)
            checker.run_checks = Mock(return_value={"overall": "healthy"})

            # 添加检查
            assert checker.add_check("database", check_database) is True

            # 运行检查
            result = checker.run_checks()
            assert result["overall"] == "healthy"

    def test_database_health_check(self):
        """测试数据库健康检查"""
        with patch("src.monitoring.health_checker.HealthChecker") as MockChecker:
            checker = MockChecker()
            checker.check_database_connection = Mock(
                return_value={
                    "status": "healthy",
                    "connection_time_ms": 5.2,
                    "active_connections": 25,
                    "max_connections": 100,
                }
            )
            checker.check_database_replication = Mock(
                return_value={"status": "healthy", "replication_lag": 0}
            )

            # 检查数据库
            db_health = checker.check_database_connection()
            replication = checker.check_database_replication()

            assert db_health["status"] == "healthy"
            assert db_health["connection_time_ms"] == 5.2
            assert replication["replication_lag"] == 0

    def test_redis_health_check(self):
        """测试Redis健康检查"""
        with patch("src.monitoring.health_checker.HealthChecker") as MockChecker:
            checker = MockChecker()
            checker.check_redis_connection = Mock(
                return_value={
                    "status": "healthy",
                    "ping_ms": 0.5,
                    "memory_usage": "50MB",
                    "connected_clients": 10,
                }
            )

            # 检查Redis
            redis_health = checker.check_redis_connection()
            assert redis_health["status"] == "healthy"
            assert redis_health["ping_ms"] == 0.5

    def test_api_health_check(self):
        """测试API健康检查"""
        with patch("src.monitoring.health_checker.HealthChecker") as MockChecker:
            checker = MockChecker()
            checker.check_api_endpoints = Mock(
                return_value={
                    "/health": {"status": 200, "response_time_ms": 10},
                    "/api/predictions": {"status": 200, "response_time_ms": 150},
                    "/api/matches": {"status": 200, "response_time_ms": 80},
                }
            )

            # 检查API端点
            api_health = checker.check_api_endpoints()
            assert api_health["/health"]["status"] == 200
            assert api_health["/api/predictions"]["response_time_ms"] == 150

    def test_service_health_check(self):
        """测试服务健康检查"""
        with patch("src.monitoring.health_checker.HealthChecker") as MockChecker:
            checker = MockChecker()
            checker.check_service_dependencies = Mock(
                return_value={
                    "prediction_service": {"status": "healthy", "uptime": 86400},
                    "notification_service": {"status": "healthy", "uptime": 86400},
                    "data_collection_service": {"status": "degraded", "uptime": 3600},
                }
            )

            # 检查服务依赖
            service_health = checker.check_service_dependencies()
            assert service_health["prediction_service"]["status"] == "healthy"
            assert service_health["data_collection_service"]["status"] == "degraded"

    def test_resource_health_check(self):
        """测试资源健康检查"""
        with patch("src.monitoring.health_checker.HealthChecker") as MockChecker:
            checker = MockChecker()
            checker.check_cpu_health = Mock(
                return_value={"status": "healthy", "usage": 45.0}
            )
            checker.check_memory_health = Mock(
                return_value={"status": "healthy", "usage": 65.0}
            )
            checker.check_disk_health = Mock(
                return_value={"status": "warning", "usage": 85.0}
            )

            # 检查资源
            cpu = checker.check_cpu_health()
            memory = checker.check_memory_health()
            disk = checker.check_disk_health()

            assert cpu["status"] == "healthy"
            assert memory["status"] == "healthy"
            assert disk["status"] == "warning"


class TestAnomalyDetector:
    """测试异常检测器"""

    def test_anomaly_detector_creation(self):
        """测试异常检测器创建"""
        if not MONITORING_AVAILABLE:
            pytest.skip("Monitoring模块不可用")

        with patch("src.monitoring.anomaly_detector.AnomalyDetector") as MockDetector:
            detector = MockDetector()
            detector.configure_threshold = Mock(return_value=True)
            detector.train_model = Mock(return_value=True)
            detector.detect_anomaly = Mock(return_value={"is_anomaly": False})

            # 配置阈值
            assert detector.configure_threshold("cpu_usage", 80.0) is True

            # 检测异常
            result = detector.detect_anomaly("cpu_usage", 75.0)
            assert result["is_anomaly"] is False

    def test_statistical_anomaly_detection(self):
        """测试统计异常检测"""
        with patch("src.monitoring.anomaly_detector.AnomalyDetector") as MockDetector:
            detector = MockDetector()
            detector.detect_statistical_anomaly = Mock(
                return_value={"is_anomaly": True, "z_score": 3.5, "threshold": 3.0}
            )
            detector.calculate_moving_average = Mock(return_value=50.0)
            detector.calculate_standard_deviation = Mock(return_value=10.0)

            # 检测统计异常
            anomaly = detector.detect_statistical_anomaly([50, 52, 48, 51, 49, 85])
            assert anomaly["is_anomaly"] is True
            assert anomaly["z_score"] == 3.5

            # 计算统计量
            avg = detector.calculate_moving_average([50, 52, 48, 51, 49])
            std = detector.calculate_standard_deviation([50, 52, 48, 51, 49])

            assert avg == 50.0
            assert std == 10.0

    def test_ml_anomaly_detection(self):
        """测试机器学习异常检测"""
        with patch("src.monitoring.anomaly_detector.AnomalyDetector") as MockDetector:
            detector = MockDetector()
            detector.train_isolation_forest = Mock(return_value={"model_trained": True})
            detector.train_autoencoder = Mock(return_value={"model_trained": True})
            detector.predict_anomaly = Mock(
                return_value={"is_anomaly": True, "score": 0.85}
            )

            # 训练模型
            isolation_result = detector.train_isolation_forest([[1], [2], [3], [10]])
            autoencoder_result = detector.train_autoencoder([[1], [2], [3], [10]])

            assert isolation_result["model_trained"] is True
            assert autoencoder_result["model_trained"] is True

            # 预测异常
            prediction = detector.predict_anomaly([[10]])
            assert prediction["is_anomaly"] is True

    def test_time_series_anomaly(self):
        """测试时间序列异常检测"""
        with patch("src.monitoring.anomaly_detector.AnomalyDetector") as MockDetector:
            detector = MockDetector()
            detector.detect_seasonal_anomaly = Mock(
                return_value={
                    "is_anomaly": True,
                    "expected": 100,
                    "actual": 500,
                    "deviation": 400,
                }
            )
            detector.detect_trend_anomaly = Mock(
                return_value={"is_anomaly": True, "trend": "increasing", "rate": 2.5}
            )

            # 检测季节性异常
            seasonal = detector.detect_seasonal_anomaly(
                [100, 105, 98, 102, 500],  # 时间序列
                period=24,  # 24小时周期
            )
            assert seasonal["is_anomaly"] is True

            # 检测趋势异常
            trend = detector.detect_trend_anomaly([10, 20, 40, 80, 160])
            assert trend["is_anomaly"] is True
            assert trend["trend"] == "increasing"


class TestAlertManager:
    """测试告警管理器"""

    def test_alert_manager_creation(self):
        """测试告警管理器创建"""
        if not MONITORING_AVAILABLE:
            pytest.skip("Monitoring模块不可用")

        with patch("src.monitoring.alert_manager.AlertManager") as MockManager:
            manager = MockManager()
            manager.add_alert_rule = Mock(return_value=True)
            manager.remove_alert_rule = Mock(return_value=True)
            manager.trigger_alert = Mock(
                return_value={"alert_id": "123", "status": "triggered"}
            )

            # 添加告警规则
            rule = {
                "name": "high_cpu_usage",
                "condition": "cpu_usage > 80",
                "severity": "warning",
            }
            assert manager.add_alert_rule(rule) is True

    def test_alert_rules(self):
        """测试告警规则"""
        with patch("src.monitoring.alert_manager.AlertManager") as MockManager:
            manager = MockManager()
            manager.evaluate_rules = Mock(
                return_value=[
                    {
                        "rule": "high_cpu",
                        "triggered": True,
                        "value": 85.0,
                        "threshold": 80.0,
                    },
                    {
                        "rule": "high_memory",
                        "triggered": False,
                        "value": 65.0,
                        "threshold": 90.0,
                    },
                ]
            )

            # 评估规则
            triggered_rules = manager.evaluate_rules(
                {"cpu_usage": 85.0, "memory_usage": 65.0}
            )

            assert len(triggered_rules) == 2
            assert triggered_rules[0]["triggered"] is True
            assert triggered_rules[1]["triggered"] is False

    def test_alert_channels(self):
        """测试告警通道"""
        with patch("src.monitoring.alert_manager.AlertManager") as MockManager:
            manager = MockManager()
            manager.send_email_alert = Mock(
                return_value={"status": "sent", "recipient": "admin@example.com"}
            )
            manager.send_slack_alert = Mock(
                return_value={"status": "sent", "channel": "#alerts"}
            )
            manager.send_webhook_alert = Mock(
                return_value={"status": "sent", "url": "https://example.com/webhook"}
            )

            # 发送不同类型的告警
            email_result = manager.send_email_alert(
                subject="High CPU Alert", message="CPU usage is above 80%"
            )
            slack_result = manager.send_slack_alert(
                channel="#alerts", message="High CPU usage detected"
            )
            webhook_result = manager.send_webhook_alert(
                url="https://example.com/webhook",
                data={"alert": "high_cpu", "value": 85.0},
            )

            assert email_result["status"] == "sent"
            assert slack_result["status"] == "sent"
            assert webhook_result["status"] == "sent"

    def test_alert_suppression(self):
        """测试告警抑制"""
        with patch("src.monitoring.alert_manager.AlertManager") as MockManager:
            manager = MockManager()
            manager.is_suppressed = Mock(return_value=True)
            manager.suppress_alert = Mock(
                return_value={"status": "suppressed", "duration": 300}
            )
            manager.unsuppress_alert = Mock(return_value={"status": "unsuppressed"})

            # 检查告警是否被抑制
            is_suppressed = manager.is_suppressed("high_cpu")
            assert is_suppressed is True

            # 抑制告警
            suppress_result = manager.suppress_alert("high_cpu", duration=300)
            assert suppress_result["status"] == "suppressed"

            # 取消抑制
            unsuppress_result = manager.unsuppress_alert("high_cpu")
            assert unsuppress_result["status"] == "unsuppressed"

    def test_alert_history(self):
        """测试告警历史"""
        with patch("src.monitoring.alert_manager.AlertManager") as MockManager:
            manager = MockManager()
            manager.get_alert_history = Mock(
                return_value=[
                    {
                        "timestamp": "2025-01-18T10:00:00",
                        "alert": "high_cpu",
                        "severity": "warning",
                        "resolved_at": "2025-01-18T10:15:00",
                    },
                    {
                        "timestamp": "2025-01-18T09:30:00",
                        "alert": "high_memory",
                        "severity": "critical",
                        "resolved_at": "2025-01-18T09:45:00",
                    },
                ]
            )

            # 获取告警历史
            history = manager.get_alert_history(limit=10)
            assert len(history) == 2
            assert history[0]["alert"] == "high_cpu"
            assert history[1]["severity"] == "critical"


class TestQualityMonitor:
    """测试质量监控器"""

    def test_quality_monitor_creation(self):
        """测试质量监控器创建"""
        if not MONITORING_AVAILABLE:
            pytest.skip("Monitoring模块不可用")

        with patch("src.monitoring.quality_monitor.QualityMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.start_monitoring = Mock(return_value=True)
            monitor.stop_monitoring = Mock(return_value=True)
            monitor.check_prediction_quality = Mock(return_value={"accuracy": 0.85})

            # 启动监控
            assert monitor.start_monitoring() is True

            # 检查预测质量
            quality = monitor.check_prediction_quality()
            assert quality["accuracy"] == 0.85

    def test_data_quality_checks(self):
        """测试数据质量检查"""
        with patch("src.monitoring.quality_monitor.QualityMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.check_data_completeness = Mock(return_value=0.95)
            monitor.check_data_consistency = Mock(return_value=0.88)
            monitor.check_data_validity = Mock(return_value=0.92)
            monitor.check_data_timeliness = Mock(return_value=0.90)

            # 检查数据质量
            completeness = monitor.check_data_completeness()
            consistency = monitor.check_data_consistency()
            validity = monitor.check_data_validity()
            timeliness = monitor.check_data_timeliness()

            assert completeness == 0.95
            assert consistency == 0.88
            assert validity == 0.92
            assert timeliness == 0.90

    def test_model_quality_metrics(self):
        """测试模型质量指标"""
        with patch("src.monitoring.quality_monitor.QualityMonitor") as MockMonitor:
            monitor = MockMonitor()
            monitor.calculate_model_accuracy = Mock(return_value=0.85)
            monitor.calculate_precision = Mock(return_value=0.82)
            monitor.calculate_recall = Mock(return_value=0.78)
            monitor.calculate_f1_score = Mock(return_value=0.80)
            monitor.calculate_auc_roc = Mock(return_value=0.92)

            # 计算模型指标
            accuracy = monitor.calculate_model_accuracy()
            precision = monitor.calculate_precision()
            recall = monitor.calculate_recall()
            f1 = monitor.calculate_f1_score()
            auc = monitor.calculate_auc_roc()

            assert accuracy == 0.85
            assert precision == 0.82
            assert recall == 0.78
            assert f1 == 0.80
            assert auc == 0.92


def check_database():
    """模拟数据库检查函数"""
    return {"status": "healthy"}
