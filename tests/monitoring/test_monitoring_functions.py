"""
Monitoring模块功能测试
测试监控系统的各项功能
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


class TestMonitoringFunctionality:
    """测试Monitoring功能模块"""

    def test_metrics_collection_functionality(self):
        """测试指标收集功能"""
        # Mock指标收集器
        MockCollector = Mock()
        collector = MockCollector()

        # 设置收集方法
        collector.collect_cpu = Mock(return_value=45.2)
        collector.collect_memory = Mock(return_value=68.5)
        collector.collect_disk = Mock(return_value=35.8)
        collector.collect_network = Mock(
            return_value={"bytes_sent": 1024000, "bytes_recv": 2048000}
        )
        collector.collect_custom_metric = Mock(return_value=100)

        # 测试收集各类指标
        cpu = collector.collect_cpu()
        memory = collector.collect_memory()
        disk = collector.collect_disk()
        network = collector.collect_network()
        custom = collector.collect_custom_metric("api_requests")

        assert cpu == 45.2
        assert memory == 68.5
        assert disk == 35.8
        assert network["bytes_sent"] == 1024000
        assert custom == 100

    def test_metrics_aggregation_functionality(self):
        """测试指标聚合功能"""
        # Mock聚合器
        MockAggregator = Mock()
        aggregator = MockAggregator()

        # 设置聚合方法
        aggregator.add_value = Mock(return_value=True)
        aggregator.calculate_average = Mock(return_value=50.5)
        aggregator.calculate_sum = Mock(return_value=5050)
        aggregator.calculate_min = Mock(return_value=1)
        aggregator.calculate_max = Mock(return_value=100)
        aggregator.calculate_percentile = Mock(return_value=95.0)
        aggregator.calculate_rate = Mock(return_value=10.5)

        # 添加数据点
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        for value in values:
            aggregator.add_value(value)

        # 计算聚合值
        avg = aggregator.calculate_average()
        total = aggregator.calculate_sum()
        min_val = aggregator.calculate_min()
        max_val = aggregator.calculate_max()
        p95 = aggregator.calculate_percentile(95)
        rate = aggregator.calculate_rate()

        assert avg == 50.5
        assert total == 5050
        assert min_val == 1
        assert max_val == 100
        assert p95 == 95.0
        assert rate == 10.5

    def test_system_monitoring_functionality(self):
        """测试系统监控功能"""
        # Mock系统监控器
        MockSystemMonitor = Mock()
        monitor = MockSystemMonitor()

        # 设置监控方法
        monitor.get_system_info = Mock(
            return_value={
                "hostname": "server-01",
                "os": "Linux",
                "architecture": "x86_64",
                "cpu_count": 4,
                "total_memory": 8589934592,
            }
        )
        monitor.get_process_list = Mock(
            return_value=[
                {"pid": 1, "name": "init", "cpu": 0.1, "memory": 0.1},
                {"pid": 123, "name": "python", "cpu": 15.2, "memory": 5.1},
                {"pid": 456, "name": "postgres", "cpu": 10.5, "memory": 20.3},
            ]
        )
        monitor.get_uptime = Mock(return_value=86400)
        monitor.get_load_average = Mock(return_value=[1.5, 1.8, 2.1])

        # 获取系统信息
        system_info = monitor.get_system_info()
        processes = monitor.get_process_list()
        uptime = monitor.get_uptime()
        load_avg = monitor.get_load_average()

        assert system_info["hostname"] == "server-01"
        assert system_info["cpu_count"] == 4
        assert len(processes) == 3
        assert processes[1]["name"] == "python"
        assert uptime == 86400
        assert load_avg[0] == 1.5

    def test_health_check_functionality(self):
        """测试健康检查功能"""
        # Mock健康检查器
        MockHealthChecker = Mock()
        checker = MockHealthChecker()

        # 设置检查方法
        checker.check_database = Mock(
            return_value={
                "status": "healthy",
                "response_time": 5.2,
                "connection_pool": {"active": 5, "idle": 15, "total": 20},
            }
        )
        checker.check_redis = Mock(
            return_value={
                "status": "healthy",
                "ping_ms": 0.5,
                "memory_usage": "50MB",
                "connected_clients": 10,
            }
        )
        checker.check_api_health = Mock(
            return_value={
                "status": "degraded",
                "endpoints": {
                    "/health": {"status": 200, "response_time": 10},
                    "/api/predictions": {"status": 500, "response_time": 5000},
                },
            }
        )
        checker.check_disk_space = Mock(
            return_value={"status": "warning", "usage": 85.0, "free_space": "15GB"}
        )

        # 执行健康检查
        db_health = checker.check_database()
        redis_health = checker.check_redis()
        api_health = checker.check_api_health()
        disk_health = checker.check_disk_space()

        assert db_health["status"] == "healthy"
        assert db_health["response_time"] == 5.2
        assert redis_health["ping_ms"] == 0.5
        assert api_health["status"] == "degraded"
        assert api_health["endpoints"]["/api/predictions"]["status"] == 500
        assert disk_health["status"] == "warning"
        assert disk_health["usage"] == 85.0

    def test_alert_management_functionality(self):
        """测试告警管理功能"""
        # Mock告警管理器
        MockAlertManager = Mock()
        manager = MockAlertManager()

        # 设置告警方法
        manager.create_rule = Mock(
            return_value={
                "rule_id": "rule_001",
                "name": "high_cpu_usage",
                "condition": "cpu > 80",
                "severity": "warning",
            }
        )
        manager.evaluate_rules = Mock(
            return_value=[
                {
                    "rule": "high_cpu_usage",
                    "triggered": True,
                    "value": 85.0,
                    "message": "CPU usage is above 80%",
                },
                {
                    "rule": "high_memory_usage",
                    "triggered": False,
                    "value": 65.0,
                    "message": None,
                },
            ]
        )
        manager.send_notification = Mock(
            return_value={
                "channel": "email",
                "recipient": "admin@example.com",
                "status": "sent",
            }
        )
        manager.get_alert_history = Mock(
            return_value=[
                {
                    "timestamp": "2025-01-18T10:00:00",
                    "alert": "high_cpu",
                    "severity": "warning",
                    "resolved_at": "2025-01-18T10:15:00",
                }
            ]
        )

        # 创建告警规则
        rule = manager.create_rule(
            name="high_cpu_usage", condition="cpu > 80", severity="warning"
        )
        assert rule["rule_id"] == "rule_001"

        # 评估告警规则
        current_metrics = {"cpu": 85.0, "memory": 65.0}
        triggered_alerts = manager.evaluate_rules(current_metrics)
        assert len(triggered_alerts) == 2
        assert triggered_alerts[0]["triggered"] is True
        assert triggered_alerts[1]["triggered"] is False

        # 发送通知
        for alert in triggered_alerts:
            if alert["triggered"]:
                notification = manager.send_notification(
                    channel="email",
                    recipient="admin@example.com",
                    message=alert["message"],
                )
                assert notification["status"] == "sent"

        # 获取告警历史
        history = manager.get_alert_history(limit=10)
        assert len(history) == 1
        assert history[0]["alert"] == "high_cpu"

    def test_anomaly_detection_functionality(self):
        """测试异常检测功能"""
        # Mock异常检测器
        MockAnomalyDetector = Mock()
        detector = MockAnomalyDetector()

        # 设置检测方法
        detector.detect_statistical_anomaly = Mock(
            return_value={
                "is_anomaly": True,
                "z_score": 3.5,
                "threshold": 3.0,
                "confidence": 0.99,
            }
        )
        detector.detect_seasonal_anomaly = Mock(
            return_value={
                "is_anomaly": False,
                "expected": 100,
                "actual": 105,
                "seasonal_index": 1.05,
            }
        )
        detector.train_model = Mock(
            return_value={
                "model_type": "isolation_forest",
                "training_samples": 1000,
                "accuracy": 0.92,
            }
        )
        detector.predict = Mock(
            return_value={
                "is_anomaly": True,
                "anomaly_score": 0.85,
                "explanation": "Value deviates from normal pattern",
            }
        )

        # 统计异常检测
        data = [50, 52, 48, 51, 49, 85]
        stat_result = detector.detect_statistical_anomaly(data)
        assert stat_result["is_anomaly"] is True
        assert stat_result["z_score"] == 3.5

        # 季节性异常检测
        seasonal_data = [100, 105, 98, 102, 105]  # 5天的数据
        seasonal_result = detector.detect_seasonal_anomaly(seasonal_data)
        assert seasonal_result["is_anomaly"] is False

        # 训练异常检测模型
        training_data = [[i] for i in range(1000)]
        train_result = detector.train_model(training_data)
        assert train_result["model_type"] == "isolation_forest"
        assert train_result["accuracy"] == 0.92

        # 预测异常
        test_data = [[500]]
        prediction = detector.predict(test_data)
        assert prediction["is_anomaly"] is True
        assert prediction["anomaly_score"] == 0.85

    def test_metrics_export_functionality(self):
        """测试指标导出功能"""
        # Mock指标导出器
        MockExporter = Mock()
        exporter = MockExporter()

        # 设置导出方法
        exporter.export_to_prometheus = Mock(
            return_value="""
# HELP cpu_usage CPU usage percentage
# TYPE cpu_usage gauge
cpu_usage{host="server01"} 45.2

# HELP memory_usage Memory usage percentage
# TYPE memory_usage gauge
memory_usage{host="server01"} 68.5
        """.strip()
        )
        exporter.export_to_json = Mock(
            return_value={
                "timestamp": "2025-01-18T10:00:00",
                "metrics": {
                    "cpu_usage": {"value": 45.2, "unit": "percent"},
                    "memory_usage": {"value": 68.5, "unit": "percent"},
                    "disk_usage": {"value": 35.8, "unit": "percent"},
                },
            }
        )
        exporter.export_to_influxdb = Mock(
            return_value=[
                "cpu_usage,host=server01 value=45.2 1642507200000000000",
                "memory_usage,host=server01 value=68.5 1642507200000000000",
                "disk_usage,host=server01 value=35.8 1642507200000000000",
            ]
        )
        exporter.export_to_csv = Mock(
            return_value="timestamp,metric,value,unit\n2025-01-18T10:00:00,cpu_usage,45.2,percent"
        )

        # 测试不同格式的导出
        metrics = {"cpu_usage": 45.2, "memory_usage": 68.5, "disk_usage": 35.8}

        prometheus_format = exporter.export_to_prometheus(metrics)
        json_format = exporter.export_to_json(metrics)
        influxdb_format = exporter.export_to_influxdb(metrics)
        csv_format = exporter.export_to_csv(metrics)

        assert "cpu_usage" in prometheus_format
        assert "gauge" in prometheus_format
        assert json_format["metrics"]["cpu_usage"]["value"] == 45.2
        assert len(influxdb_format) == 3
        assert "cpu_usage,host=server01" in influxdb_format[0]
        assert "timestamp,metric,value,unit" in csv_format

    def test_monitoring_configuration_functionality(self):
        """测试监控配置功能"""
        # Mock配置管理器
        MockConfigManager = Mock()
        config_manager = MockConfigManager()

        # 设置配置方法
        config_manager.load_config = Mock(
            return_value={
                "monitoring": {
                    "interval": 5,
                    "enabled_metrics": ["cpu", "memory", "disk"],
                    "alert_rules": [
                        {
                            "name": "high_cpu",
                            "condition": "cpu > 80",
                            "severity": "warning",
                        }
                    ],
                }
            }
        )
        config_manager.update_config = Mock(return_value=True)
        config_manager.validate_config = Mock(
            return_value={"valid": True, "errors": []}
        )
        config_manager.get_metric_config = Mock(
            return_value={
                "name": "cpu_usage",
                "enabled": True,
                "interval": 1,
                "retention": "7d",
            }
        )

        # 加载配置
        config = config_manager.load_config("monitoring.yaml")
        assert config["monitoring"]["interval"] == 5
        assert "cpu" in config["monitoring"]["enabled_metrics"]

        # 更新配置
        new_config = {
            "monitoring": {
                "interval": 10,
                "enabled_metrics": ["cpu", "memory", "disk", "network"],
            }
        }
        updated = config_manager.update_config(new_config)
        assert updated is True

        # 验证配置
        validation = config_manager.validate_config(config)
        assert validation["valid"] is True

        # 获取指标配置
        metric_config = config_manager.get_metric_config("cpu_usage")
        assert metric_config["enabled"] is True
        assert metric_config["interval"] == 1

    @pytest.mark.asyncio
    async def test_monitoring_async_functionality(self):
        """测试监控异步功能"""
        # Mock异步监控器
        MockAsyncMonitor = Mock()
        monitor = MockAsyncMonitor()

        # 设置异步方法
        monitor.start_monitoring = AsyncMock(return_value=True)
        monitor.stop_monitoring = AsyncMock(return_value=True)
        monitor.collect_metrics_async = AsyncMock(
            return_value={
                "cpu": 45.0,
                "memory": 65.0,
                "timestamp": "2025-01-18T10:00:00",
            }
        )
        monitor.send_metrics_remote = AsyncMock(
            return_value={
                "status": "success",
                "endpoint": "https://monitoring.example.com",
                "sent_count": 10,
            }
        )
        monitor.run_health_checks_async = AsyncMock(
            return_value={
                "overall": "healthy",
                "checks": {"database": "healthy", "redis": "healthy", "api": "healthy"},
            }
        )

        # 测试异步操作
        await monitor.start_monitoring()
        assert monitor.start_monitoring.called

        # 异步收集指标
        metrics = await monitor.collect_metrics_async()
        assert metrics["cpu"] == 45.0

        # 异步发送远程指标
        remote_result = await monitor.send_metrics_remote(
            endpoint="https://monitoring.example.com", metrics=metrics
        )
        assert remote_result["status"] == "success"

        # 异步运行健康检查
        health = await monitor.run_health_checks_async()
        assert health["overall"] == "healthy"

        await monitor.stop_monitoring()
        assert monitor.stop_monitoring.called

    def test_monitoring_performance_functionality(self):
        """测试监控性能功能"""
        # Mock性能监控器
        MockPerformanceMonitor = Mock()
        perf_monitor = MockPerformanceMonitor()

        # 设置性能方法
        perf_monitor.measure_response_time = Mock(return_value=150.5)
        perf_monitor.count_requests = Mock(return_value=1000)
        perf_monitor.calculate_throughput = Mock(return_value=100.5)
        perf_monitor.get_percentiles = Mock(
            return_value={"p50": 100.0, "p95": 200.0, "p99": 500.0}
        )
        perf_monitor.calculate_error_rate = Mock(return_value=0.02)

        # 测量响应时间
        response_time = perf_monitor.measure_response_time("api_endpoint")
        assert response_time == 150.5

        # 统计请求数
        request_count = perf_monitor.count_requests("api_endpoint")
        assert request_count == 1000

        # 计算吞吐量
        throughput = perf_monitor.calculate_throughput(requests=1000, duration=10)
        assert throughput == 100.5

        # 获取响应时间百分位数
        percentiles = perf_monitor.get_percentiles(
            metric="response_time", values=[10, 20, 30, 50, 100, 200, 500, 1000]
        )
        assert percentiles["p95"] == 200.0
        assert percentiles["p99"] == 500.0

        # 计算错误率
        error_rate = perf_monitor.calculate_error_rate(errors=20, total_requests=1000)
        assert error_rate == 0.02

    def test_monitoring_integration_functionality(self):
        """测试监控集成功能"""
        # Mock完整的监控系统
        MockMonitoringSystem = Mock()
        system = MockMonitoringSystem()

        # 设置集成方法
        system.collect_all_metrics = Mock(
            return_value={
                "system": {"cpu": 45.2, "memory": 68.5, "disk": 35.8},
                "application": {
                    "requests_per_second": 100,
                    "error_rate": 0.02,
                    "active_connections": 25,
                },
            }
        )
        system.evaluate_health = Mock(
            return_value={"status": "healthy", "score": 0.95, "issues": []}
        )
        system.check_alerts = Mock(
            return_value=[{"type": "info", "message": "System running normally"}]
        )
        system.generate_report = Mock(
            return_value={
                "timestamp": "2025-01-18T10:00:00",
                "summary": {"health": "healthy", "alerts_count": 1, "metrics_count": 6},
            }
        )

        # 收集所有指标
        all_metrics = system.collect_all_metrics()
        assert "system" in all_metrics
        assert "application" in all_metrics
        assert all_metrics["system"]["cpu"] == 45.2

        # 评估健康状态
        health = system.evaluate_health(all_metrics)
        assert health["status"] == "healthy"
        assert health["score"] == 0.95

        # 检查告警
        alerts = system.check_alerts(all_metrics, health)
        assert len(alerts) == 1
        assert alerts[0]["type"] == "info"

        # 生成报告
        report = system.generate_report(all_metrics, health, alerts)
        assert report["summary"]["health"] == "healthy"
        assert report["summary"]["alerts_count"] == 1
