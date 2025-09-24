"""
阶段2：监控指标收集器测试
目标：补齐核心逻辑测试覆盖率达到70%+
重点：测试指标收集、性能监控、数据聚合、错误处理
"""

import time
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.monitoring.metrics_collector import MetricsCollector


class TestMetricsCollectorPhase2:
    """监控指标收集器阶段2测试"""

    def setup_method(self):
        """设置测试环境"""
        self.collector = MetricsCollector()

    def test_initialization(self):
        """测试初始化"""
        assert self.collector is not None
        assert hasattr(self.collector, "logger")
        assert hasattr(self.collector, "metrics")
        assert hasattr(self.collector, "registry")

    def test_metrics_storage(self):
        """测试指标存储"""
        assert isinstance(self.collector.metrics, dict)
        assert len(self.collector.metrics) == 0  # 初始为空

    def test_logger_configuration(self):
        """测试日志配置"""
        assert self.collector.logger is not None
        assert hasattr(self.collector.logger, "error")
        assert hasattr(self.collector.logger, "info")
        assert hasattr(self.collector.logger, "warning")

    def test_registry_configuration(self):
        """测试注册表配置"""
        assert self.collector.registry is not None

    def test_counter_methods(self):
        """测试计数器方法"""
        # 验证计数器方法存在
        assert hasattr(self.collector, "increment_counter")
        assert hasattr(self.collector, "get_counter_value")
        assert hasattr(self.collector, "reset_counter")

    def test_gauge_methods(self):
        """测试测量值方法"""
        # 验证测量值方法存在
        assert hasattr(self.collector, "set_gauge")
        assert hasattr(self.collector, "get_gauge_value")
        assert hasattr(self.collector, "increment_gauge")
        assert hasattr(self.collector, "decrement_gauge")

    def test_histogram_methods(self):
        """测试直方图方法"""
        # 验证直方图方法存在
        assert hasattr(self.collector, "observe_histogram")
        assert hasattr(self.collector, "get_histogram_stats")
        assert hasattr(self.collector, "reset_histogram")

    def test_timer_methods(self):
        """测试计时器方法"""
        # 验证计时器方法存在
        assert hasattr(self.collector, "start_timer")
        assert hasattr(self.collector, "stop_timer")
        assert hasattr(self.collector, "record_timing")

    def test_counter_basic(self):
        """测试基本计数器"""
        metric_name = "test_counter"
        initial_value = self.collector.get_counter_value(metric_name)
        assert initial_value == 0

        self.collector.increment_counter(metric_name)
        new_value = self.collector.get_counter_value(metric_name)
        assert new_value == 1

        self.collector.increment_counter(metric_name, 5)
        final_value = self.collector.get_counter_value(metric_name)
        assert final_value == 6

    def test_counter_with_labels(self):
        """测试带标签的计数器"""
        metric_name = "labeled_counter"
        labels = {"method": "GET", "endpoint": "/api/test"}

        self.collector.increment_counter(metric_name, labels=labels)
        value = self.collector.get_counter_value(metric_name, labels=labels)
        assert value == 1

    def test_gauge_basic(self):
        """测试基本测量值"""
        metric_name = "test_gauge"
        value = 42.5

        self.collector.set_gauge(metric_name, value)
        retrieved_value = self.collector.get_gauge_value(metric_name)
        assert retrieved_value == value

    def test_gauge_increment_decrement(self):
        """测试测量值增减"""
        metric_name = "test_gauge_inc_dec"
        initial_value = 10.0

        self.collector.set_gauge(metric_name, initial_value)
        self.collector.increment_gauge(metric_name, 2.5)
        self.collector.decrement_gauge(metric_name, 1.0)

        final_value = self.collector.get_gauge_value(metric_name)
        assert final_value == 11.5

    def test_histogram_basic(self):
        """测试基本直方图"""
        metric_name = "test_histogram"
        values = [1.0, 2.0, 3.0, 4.0, 5.0]

        for value in values:
            self.collector.observe_histogram(metric_name, value)

        stats = self.collector.get_histogram_stats(metric_name)
        assert "count" in stats
        assert "sum" in stats
        assert "mean" in stats
        assert stats["count"] == 5
        assert stats["sum"] == 15.0
        assert stats["mean"] == 3.0

    def test_timer_basic(self):
        """测试基本计时器"""
        metric_name = "test_timer"

        # 开始计时
        timer_id = self.collector.start_timer(metric_name)
        assert timer_id is not None

        # 模拟一些处理时间
        time.sleep(0.01)

        # 停止计时
        self.collector.stop_timer(timer_id)

        # 验证计时被记录
        timing_value = self.collector.get_gauge_value(f"{metric_name}_duration")
        assert timing_value > 0

    def test_timing_recording(self):
        """测试计时记录"""
        metric_name = "test_timing"
        duration = 0.5

        self.collector.record_timing(metric_name, duration)

        timing_value = self.collector.get_gauge_value(f"{metric_name}_duration")
        assert timing_value == duration

    def test_metrics_reset(self):
        """测试指标重置"""
        metric_name = "reset_test_counter"

        self.collector.increment_counter(metric_name, 10)
        assert self.collector.get_counter_value(metric_name) == 10

        self.collector.reset_counter(metric_name)
        assert self.collector.get_counter_value(metric_name) == 0

    def test_metrics_aggregation(self):
        """测试指标聚合"""
        base_metric = "aggregation_test"

        # 增加多个标签组合
        self.collector.increment_counter(base_metric, labels={"status": "success"})
        self.collector.increment_counter(base_metric, labels={"status": "success"})
        self.collector.increment_counter(base_metric, labels={"status": "error"})

        # 聚合所有值
        aggregated = self.collector.get_aggregated_counter(base_metric)
        assert aggregated == 3

    def test_metrics_filtering(self):
        """测试指标过滤"""
        # 创建不同模式的指标
        self.collector.increment_counter("api_requests_total")
        self.collector.increment_counter("db_queries_total")
        self.collector.set_gauge("active_connections", 5)

        # 按模式过滤
        api_metrics = self.collector.get_metrics_by_pattern("api_*")
        assert len(api_metrics) >= 1
        assert "api_requests_total" in api_metrics

    def test_metrics_export(self):
        """测试指标导出"""
        # 创建一些指标
        self.collector.increment_counter("test_counter", 5)
        self.collector.set_gauge("test_gauge", 10.5)

        # 导出指标
        exported = self.collector.export_metrics()

        assert isinstance(exported, dict)
        assert "test_counter" in exported
        assert "test_gauge" in exported

    def test_metrics_persistence(self):
        """测试指标持久化"""
        # 创建指标
        self.collector.increment_counter("persistent_counter", 3)

        # 模拟持久化
        persisted = self.collector.get_persistent_metrics()
        assert isinstance(persisted, dict)
        assert "persistent_counter" in persisted

    def test_metrics_validation(self):
        """测试指标验证"""
        # 测试无效指标名
        with pytest.raises(ValueError):
            self.collector.increment_counter("")

        # 测试负值计数器
        with pytest.raises(ValueError):
            self.collector.increment_counter("test", -1)

    def test_concurrent_access(self):
        """测试并发访问"""
        import concurrent.futures
        import threading

        metric_name = "concurrent_counter"
        num_threads = 10
        increments_per_thread = 100

        def increment_counter():
            for _ in range(increments_per_thread):
                self.collector.increment_counter(metric_name)

        # 创建多个线程并发增加计数器
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=increment_counter)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证最终值
        expected_value = num_threads * increments_per_thread
        actual_value = self.collector.get_counter_value(metric_name)
        assert actual_value == expected_value

    def test_memory_efficiency(self):
        """测试内存效率"""
        # 创建大量指标
        for i in range(1000):
            self.collector.increment_counter(f"metric_{i}")

        # 验证内存使用合理
        assert len(self.collector.metrics) == 1000

        # 清理旧指标
        self.collector.cleanup_old_metrics(age_threshold=timedelta(hours=1))

        # 验证清理效果
        assert len(self.collector.metrics) < 1000

    def test_performance_monitoring(self):
        """测试性能监控"""
        # 监控收集器自身性能
        start_time = time.time()

        # 执行大量操作
        for i in range(1000):
            self.collector.increment_counter(f"perf_test_{i}")

        end_time = time.time()
        duration = end_time - start_time

        # 验证性能合理
        assert duration < 1.0  # 应该在1秒内完成

    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效输入处理
        with patch.object(self.collector.logger, "error") as mock_logger:
            try:
                self.collector.increment_counter(None)
            except Exception:
                pass

            # 验证错误被记录
            mock_logger.assert_called()

    def test_metric_lifecycle(self):
        """测试指标生命周期"""
        metric_name = "lifecycle_test"

        # 创建指标
        self.collector.increment_counter(metric_name)
        assert self.collector.get_counter_value(metric_name) == 1

        # 更新指标
        self.collector.increment_counter(metric_name, 2)
        assert self.collector.get_counter_value(metric_name) == 3

        # 重置指标
        self.collector.reset_counter(metric_name)
        assert self.collector.get_counter_value(metric_name) == 0

        # 删除指标
        self.collector.remove_metric(metric_name)
        assert not self.collector.metric_exists(metric_name)

    def test_metric_groups(self):
        """测试指标组"""
        group_name = "api_metrics"

        # 创建组内指标
        self.collector.increment_counter("api_requests_total", group=group_name)
        self.collector.set_gauge("api_response_time", 0.5, group=group_name)

        # 获取组内所有指标
        group_metrics = self.collector.get_metrics_by_group(group_name)
        assert len(group_metrics) == 2
        assert "api_requests_total" in group_metrics
        assert "api_response_time" in group_metrics

    def test_metric_labels_management(self):
        """测试指标标签管理"""
        metric_name = "labeled_metric"

        # 创建带不同标签的指标
        labels1 = {"method": "GET", "endpoint": "/api/users"}
        labels2 = {"method": "POST", "endpoint": "/api/users"}

        self.collector.increment_counter(metric_name, labels=labels1)
        self.collector.increment_counter(metric_name, labels=labels2)

        # 获取所有标签组合
        all_labels = self.collector.get_metric_labels(metric_name)
        assert len(all_labels) == 2
        assert labels1 in all_labels
        assert labels2 in all_labels

    def test_metric_statistics(self):
        """测试指标统计"""
        metric_name = "stats_test"

        # 创建一系列观察值
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        for value in values:
            self.collector.observe_histogram(metric_name, value)

        # 获取统计信息
        stats = self.collector.get_metric_statistics(metric_name)
        assert "count" in stats
        assert "sum" in stats
        assert "mean" in stats
        assert "min" in stats
        assert "max" in stats
        assert stats["count"] == 5
        assert stats["sum"] == 15.0
        assert stats["mean"] == 3.0
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0

    def test_metric_alerting(self):
        """测试指标告警"""
        # 设置告警阈值
        self.collector.set_alert_threshold("error_rate", 0.05)

        # 触发告警
        self.collector.increment_counter("errors", 10)
        self.collector.increment_counter("total", 100)

        # 检查告警状态
        alerts = self.collector.check_alerts()
        assert len(alerts) > 0

    def test_metric_health_check(self):
        """测试指标健康检查"""
        # 创建指标
        self.collector.set_gauge("health_metric", 95.0)

        # 健康检查
        health_status = self.collector.health_check()
        assert "status" in health_status
        assert "metrics_count" in health_status
        assert "timestamp" in health_status

    def test_metric_backup(self):
        """测试指标备份"""
        # 创建指标
        self.collector.increment_counter("backup_test", 42)

        # 备份指标
        backup_data = self.collector.backup_metrics()
        assert isinstance(backup_data, dict)
        assert "backup_test" in backup_data

        # 恢复指标
        self.collector.reset_counter("backup_test")
        self.collector.restore_metrics(backup_data)
        assert self.collector.get_counter_value("backup_test") == 42

    def test_metric_export_formats(self):
        """测试指标导出格式"""
        # 创建指标
        self.collector.increment_counter("export_test", 10)

        # 导出为不同格式
        json_format = self.collector.export_metrics(format="json")
        prometheus_format = self.collector.export_metrics(format="prometheus")

        assert isinstance(json_format, dict)
        assert isinstance(prometheus_format, str)
        assert "export_test" in str(json_format)
        assert "export_test" in prometheus_format

    def test_metric_rate_calculation(self):
        """测试指标速率计算"""
        metric_name = "rate_test"

        # 模拟时间序列数据
        self.collector.increment_counter(metric_name, 5)
        time.sleep(0.1)
        self.collector.increment_counter(metric_name, 3)

        # 计算速率
        rate = self.collector.calculate_rate(metric_name)
        assert isinstance(rate, float)
        assert rate > 0

    def test_metric_percentile_calculation(self):
        """测试指标百分位计算"""
        metric_name = "percentile_test"

        # 创建分布数据
        values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        for value in values:
            self.collector.observe_histogram(metric_name, value)

        # 计算百分位
        p50 = self.collector.get_percentile(metric_name, 50)
        p95 = self.collector.get_percentile(metric_name, 95)
        p99 = self.collector.get_percentile(metric_name, 99)

        assert p50 == 5.5  # 中位数
        assert p95 == 9.55
        assert p99 == 9.91

    def test_metric_correlation(self):
        """测试指标相关性"""
        # 创建相关指标
        self.collector.increment_counter("requests", 100)
        self.collector.increment_counter("errors", 5)

        # 计算相关性
        correlation = self.collector.calculate_correlation("requests", "errors")
        assert isinstance(correlation, float)
        assert -1 <= correlation <= 1

    def test_metric_anomaly_detection(self):
        """测试指标异常检测"""
        metric_name = "anomaly_test"

        # 创建正常数据
        for i in range(10):
            self.collector.observe_histogram(metric_name, 10.0 + i * 0.1)

        # 创建异常数据
        self.collector.observe_histogram(metric_name, 100.0)

        # 检测异常
        anomalies = self.collector.detect_anomalies(metric_name)
        assert len(anomalies) > 0

    def test_metric_forecasting(self):
        """测试指标预测"""
        metric_name = "forecast_test"

        # 创建历史数据
        historical_values = [10, 12, 11, 13, 15, 14, 16, 18, 17, 19]
        for value in historical_values:
            self.collector.observe_histogram(metric_name, value)

        # 预测未来值
        forecast = self.collector.forecast_metric(metric_name, periods=3)
        assert len(forecast) == 3
        assert all(isinstance(value, float) for value in forecast)

    def test_metric_validation_comprehensive(self):
        """测试全面指标验证"""
        # 测试各种无效输入
        invalid_inputs = [
            ("", 1),  # 空名称
            ("test", -1),  # 负值
            (None, 1),  # None名称
            ("test", "invalid"),  # 无效值类型
        ]

        for name, value in invalid_inputs:
            with pytest.raises((ValueError, TypeError)):
                self.collector.increment_counter(name, value)

    def test_metric_configuration_management(self):
        """测试指标配置管理"""
        # 设置配置
        config = {
            "retention_period": "7d",
            "aggregation_interval": "1m",
            "alert_thresholds": {"error_rate": 0.05},
        }
        self.collector.update_configuration(config)

        # 验证配置
        assert self.collector.get_config_value("retention_period") == "7d"

    def test_metric_integration_points(self):
        """测试指标集成点"""
        # 验证各种集成点
        integration_points = [
            "integrate_with_prometheus",
            "integrate_with_grafana",
            "integrate_with_alertmanager",
            "integrate_with_logging",
        ]

        for point in integration_points:
            assert hasattr(self.collector, point)

    def test_metric_advanced_features(self):
        """测试高级指标特性"""
        # 验证高级特性
        advanced_features = [
            "calculate_derivative",
            "calculate_integral",
            "apply_smoothing",
            "detect_trends",
            "calculate_seasonality",
        ]

        for feature in advanced_features:
            assert hasattr(self.collector, feature)

    def test_metric_scaling_capabilities(self):
        """测试指标扩展能力"""
        # 验证扩展能力
        scaling_features = [
            "scale_horizontally",
            "scale_vertically",
            "distribute_metrics",
            "shard_metrics",
        ]

        for feature in scaling_features:
            assert hasattr(self.collector, feature)

    def test_metric_monitoring_dashboards(self):
        """测试指标监控仪表板"""
        # 验证仪表板功能
        dashboard_features = [
            "create_dashboard",
            "update_dashboard",
            "share_dashboard",
            "export_dashboard",
        ]

        for feature in dashboard_features:
            assert hasattr(self.collector, feature)

    def test_metric_reporting_and_notifications(self):
        """测试指标报告和通知"""
        # 验证报告和通知功能
        reporting_features = [
            "generate_report",
            "schedule_report",
            "send_notification",
            "subscribe_to_alerts",
        ]

        for feature in reporting_features:
            assert hasattr(self.collector, feature)

    def test_metric_data_retention(self):
        """测试指标数据保留"""
        # 验证数据保留功能
        retention_features = [
            "set_retention_policy",
            "cleanup_old_data",
            "archive_data",
            "restore_archived_data",
        ]

        for feature in retention_features:
            assert hasattr(self.collector, feature)

    def test_metric_security_and_compliance(self):
        """测试指标安全和合规"""
        # 验证安全和合规功能
        security_features = [
            "encrypt_metrics",
            "mask_sensitive_data",
            "audit_access",
            "compliance_check",
        ]

        for feature in security_features:
            assert hasattr(self.collector, feature)

    def test_metric_performance_optimization(self):
        """测试指标性能优化"""
        # 验证性能优化功能
        optimization_features = [
            "optimize_storage",
            "compress_data",
            "cache_frequently_accessed",
            "optimize_queries",
        ]

        for feature in optimization_features:
            assert hasattr(self.collector, feature)
