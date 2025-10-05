"""
监控单元测试 - 指标收集器
"""

import json
import threading
import time
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.monitoring.metrics_collector import (
    MetricsAggregator,
    MetricsCollector,
    PrometheusExporter,
    StatsdExporter,
)


@pytest.mark.unit
class TestMetricsCollector:
    """MetricsCollector测试"""

    @pytest.fixture
    def collector(self):
        """创建收集器实例"""
        collector = MetricsCollector(service_name="test_service", environment="test")
        collector.logger = MagicMock()
        return collector

    def test_collector_initialization(self, collector):
        """测试收集器初始化"""
        assert collector is not None
        assert collector.service_name == "test_service"
        assert collector.environment == "test"
        assert hasattr(collector, "metrics")
        assert hasattr(collector, "counters")
        assert hasattr(collector, "gauges")
        assert hasattr(collector, "histograms")
        assert hasattr(collector, "timers")

    def test_counter_increment(self, collector):
        """测试计数器递增"""
        # 创建计数器
        collector.create_counter(
            name="api_requests_total",
            description="Total API requests",
            labels={"method": "GET", "endpoint": "/api/v1/matches"},
        )

        # 递增计数器
        collector.increment_counter(
            name="api_requests_total",
            labels={"method": "GET", "endpoint": "/api/v1/matches"},
            value=1,
        )

        # 获取计数器值
        value = collector.get_counter_value(
            name="api_requests_total",
            labels={"method": "GET", "endpoint": "/api/v1/matches"},
        )

        assert value == 1

    def test_counter_multiple_increments(self, collector):
        """测试多次递增计数器"""
        collector.create_counter(name="errors_total", description="Total errors")

        # 多次递增
        collector.increment_counter("errors_total", value=2)
        collector.increment_counter("errors_total", value=3)
        collector.increment_counter("errors_total", value=5)

        value = collector.get_counter_value("errors_total")
        assert value == 10

    def test_gauge_set_value(self, collector):
        """测试设置仪表值"""
        collector.create_gauge(
            name="active_connections", description="Number of active connections"
        )

        # 设置值
        collector.set_gauge("active_connections", 50)
        assert collector.get_gauge_value("active_connections") == 50

        # 更新值
        collector.set_gauge("active_connections", 75)
        assert collector.get_gauge_value("active_connections") == 75

    def test_gauge_increment_decrement(self, collector):
        """测试仪表递增和递减"""
        collector.create_gauge(
            name="queue_size", description="Size of processing queue"
        )

        # 设置初始值
        collector.set_gauge("queue_size", 10)

        # 递增
        collector.increment_gauge("queue_size", 5)
        assert collector.get_gauge_value("queue_size") == 15

        # 递减
        collector.decrement_gauge("queue_size", 3)
        assert collector.get_gauge_value("queue_size") == 12

    def test_histogram_observe(self, collector):
        """测试直方图观察"""
        collector.create_histogram(
            name="request_duration_seconds",
            description="Request duration in seconds",
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0],
        )

        # 观察值
        collector.observe_histogram("request_duration_seconds", 0.3)
        collector.observe_histogram("request_duration_seconds", 0.7)
        collector.observe_histogram("request_duration_seconds", 1.5)

        # 获取直方图数据
        histogram_data = collector.get_histogram_data("request_duration_seconds")

        assert histogram_data["count"] == 3
        assert histogram_data["sum"] == 2.5
        assert histogram_data["buckets"][0.5] == 1  # 只有0.3在0.5桶中
        assert histogram_data["buckets"][1.0] == 2  # 0.3和0.7在1.0桶中

    def test_timer_recording(self, collector):
        """测试计时器记录"""
        collector.create_timer(
            name="database_query_time", description="Database query execution time"
        )

        # 使用上下文管理器
        with collector.timer("database_query_time"):
            time.sleep(0.1)  # 模拟操作

        # 获取计时器统计
        stats = collector.get_timer_stats("database_query_time")

        assert stats["count"] == 1
        assert stats["sum"] > 0.1
        assert stats["min"] > 0.1
        assert stats["max"] > 0.1

    def test_timer_manual_recording(self, collector):
        """测试手动记录计时器"""
        collector.create_timer(name="processing_time", description="Processing time")

        # 手动记录
        collector.record_timer("processing_time", 0.5)
        collector.record_timer("processing_time", 0.3)
        collector.record_timer("processing_time", 0.7)

        stats = collector.get_timer_stats("processing_time")

        assert stats["count"] == 3
        assert stats["sum"] == 1.5
        assert stats["avg"] == 0.5

    def test_metric_labels(self, collector):
        """测试指标标签"""
        collector.create_counter(
            name="http_requests_total",
            description="Total HTTP requests",
            label_names=["method", "status", "endpoint"],
        )

        # 使用不同标签
        collector.increment_counter(
            "http_requests_total",
            labels={"method": "GET", "status": "200", "endpoint": "/api/matches"},
        )
        collector.increment_counter(
            "http_requests_total",
            labels={"method": "POST", "status": "201", "endpoint": "/api/predictions"},
        )
        collector.increment_counter(
            "http_requests_total",
            labels={"method": "GET", "status": "200", "endpoint": "/api/matches"},
        )

        # 验证不同的标签组合
        get_requests = collector.get_counter_value(
            "http_requests_total",
            labels={"method": "GET", "status": "200", "endpoint": "/api/matches"},
        )
        post_requests = collector.get_counter_value(
            "http_requests_total",
            labels={"method": "POST", "status": "201", "endpoint": "/api/predictions"},
        )

        assert get_requests == 2
        assert post_requests == 1

    def test_metric_reset(self, collector):
        """测试重置指标"""
        collector.create_counter("test_counter", "Test counter")
        collector.create_gauge("test_gauge", "Test gauge")

        collector.increment_counter("test_counter", 10)
        collector.set_gauge("test_gauge", 50)

        # 重置指标
        collector.reset_metric("test_counter")
        collector.reset_metric("test_gauge")

        assert collector.get_counter_value("test_counter") == 0
        assert collector.get_gauge_value("test_gauge") == 0

    def test_reset_all_metrics(self, collector):
        """测试重置所有指标"""
        collector.create_counter("counter1", "Counter 1")
        collector.create_counter("counter2", "Counter 2")
        collector.create_gauge("gauge1", "Gauge 1")

        collector.increment_counter("counter1", 5)
        collector.increment_counter("counter2", 3)
        collector.set_gauge("gauge1", 10)

        # 重置所有
        collector.reset_all_metrics()

        assert collector.get_counter_value("counter1") == 0
        assert collector.get_counter_value("counter2") == 0
        assert collector.get_gauge_value("gauge1") == 0

    def test_get_all_metrics(self, collector):
        """测试获取所有指标"""
        # 创建多种类型的指标
        collector.create_counter("requests_total", "Total requests")
        collector.create_gauge("cpu_usage", "CPU usage")
        collector.create_histogram("latency", "Latency", buckets=[1, 5, 10])
        collector.create_timer("response_time", "Response time")

        # 设置值
        collector.increment_counter("requests_total", 100)
        collector.set_gauge("cpu_usage", 75.5)
        collector.observe_histogram("latency", 3)
        collector.record_timer("response_time", 0.5)

        # 获取所有指标
        all_metrics = collector.get_all_metrics()

        assert "counters" in all_metrics
        assert "gauges" in all_metrics
        assert "histograms" in all_metrics
        assert "timers" in all_metrics
        assert all_metrics["counters"]["requests_total"] == 100
        assert all_metrics["gauges"]["cpu_usage"] == 75.5

    def test_metric_validation(self, collector):
        """测试指标验证"""
        # 测试无效的指标名称
        with pytest.raises(ValueError):
            collector.create_counter("", "Empty name")

        # 测试无效的值
        collector.create_counter("valid_counter", "Valid")
        with pytest.raises(ValueError):
            collector.increment_counter("valid_counter", -1)

        # 测试不存在的指标
        with pytest.raises(KeyError):
            collector.get_counter_value("non_existent")

    def test_thread_safety(self, collector):
        """测试线程安全"""
        collector.create_counter("thread_test", "Thread test counter")

        def increment():
            for _ in range(1000):
                collector.increment_counter("thread_test")

        # 创建多个线程同时递增
        threads = []
        for _ in range(10):
            thread = threading.Thread(target=increment)
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证最终值
        assert collector.get_counter_value("thread_test") == 10000


@pytest.mark.unit
class TestPrometheusExporter:
    """Prometheus导出器测试"""

    @pytest.fixture
    def exporter(self):
        """创建导出器实例"""
        return PrometheusExporter(namespace="test_service", registry=None)

    @pytest.fixture
    def mock_metrics(self):
        """Mock指标数据"""
        return {
            "counters": {"requests_total": 1000, "errors_total": 50},
            "gauges": {"active_connections": 25, "memory_usage": 512.5},
            "histograms": {
                "request_duration": {
                    "count": 1000,
                    "sum": 5000.0,
                    "buckets": {0.1: 100, 0.5: 500, 1.0: 800, 5.0: 1000},
                }
            },
        }

    def test_export_counter(self, exporter, mock_metrics):
        """测试导出计数器"""
        prometheus_text = exporter.export_counter(
            name="requests_total",
            value=mock_metrics["counters"]["requests_total"],
            description="Total number of requests",
        )

        assert "requests_total" in prometheus_text
        assert "1000" in prometheus_text
        assert "# HELP" in prometheus_text
        assert "# TYPE" in prometheus_text

    def test_export_gauge(self, exporter, mock_metrics):
        """测试导出仪表"""
        prometheus_text = exporter.export_gauge(
            name="active_connections",
            value=mock_metrics["gauges"]["active_connections"],
            description="Active connections",
        )

        assert "active_connections" in prometheus_text
        assert "25" in prometheus_text
        assert "gauge" in prometheus_text

    def test_export_histogram(self, exporter, mock_metrics):
        """测试导出直方图"""
        histogram_data = mock_metrics["histograms"]["request_duration"]
        prometheus_text = exporter.export_histogram(
            name="request_duration_seconds",
            histogram_data=histogram_data,
            description="Request duration in seconds",
        )

        assert "request_duration_seconds" in prometheus_text
        assert "histogram" in prometheus_text
        assert "le=" in prometheus_text  # 桶标签

    def test_export_with_labels(self, exporter):
        """测试带标签导出"""
        labeled_metrics = {
            ("http_requests_total", {"method": "GET", "status": "200"}): 100,
            ("http_requests_total", {"method": "POST", "status": "201"}): 50,
        }

        prometheus_text = exporter.export_labeled_metrics(
            labeled_metrics, metric_type="counter", description="HTTP requests total"
        )

        assert 'method="GET"' in prometheus_text
        assert 'status="200"' in prometheus_text
        assert 'method="POST"' in prometheus_text
        assert 'status="201"' in prometheus_text

    def test_export_all_metrics(self, exporter, mock_metrics):
        """测试导出所有指标"""
        prometheus_text = exporter.export_all(mock_metrics)

        assert "requests_total" in prometheus_text
        assert "errors_total" in prometheus_text
        assert "active_connections" in prometheus_text
        assert "memory_usage" in prometheus_text
        assert "request_duration_seconds" in prometheus_text
        assert "# HELP" in prometheus_text
        assert "# TYPE" in prometheus_text

    def test_sanitization(self, exporter):
        """测试名称清理"""
        # 测试无效字符被替换为下划线
        sanitized = exporter.sanitize_metric_name("invalid.name-with-dashes")
        assert sanitized == "invalid_name_with_dashes"

        # 测试以数字开头的情况
        sanitized = exporter.sanitize_metric_name("123invalid")
        assert "_" in sanitized


@pytest.mark.unit
class TestStatsdExporter:
    """StatsD导出器测试"""

    @pytest.fixture
    def exporter(self):
        """创建导出器实例"""
        exporter = StatsdExporter(host="localhost", port=8125, prefix="test_service")
        exporter.client = MagicMock()
        return exporter

    def test_export_counter(self, exporter):
        """测试导出计数器到StatsD"""
        exporter.export_counter(
            name="requests", value=1, tags={"method": "GET", "status": "200"}
        )

        exporter.client.incr.assert_called_once()
        call_args = exporter.client.incr.call_args[0]
        assert "requests" in call_args[0]

    def test_export_gauge(self, exporter):
        """测试导出仪表到StatsD"""
        exporter.export_gauge(name="memory", value=512.5, tags={"host": "server1"})

        exporter.client.gauge.assert_called_once()
        call_args = exporter.client.gauge.call_args
        assert call_args[1] == 512.5

    def test_export_histogram(self, exporter):
        """测试导出直方图到StatsD"""
        exporter.export_histogram(
            name="response_time", value=0.5, tags={"endpoint": "/api/matches"}
        )

        exporter.client.histogram.assert_called_once()
        call_args = exporter.client.histogram.call_args
        assert call_args[1] == 0.5

    def test_export_timer(self, exporter):
        """测试导出计时器到StatsD"""
        exporter.export_timer(name="db_query", value=0.1, tags={"query": "SELECT"})

        exporter.client.timing.assert_called_once()
        call_args = exporter.client.timing.call_args
        assert call_args[1] == 100  # StatsD expects milliseconds

    def test_batch_export(self, exporter):
        """测试批量导出到StatsD"""
        metrics = {
            "counters": [("requests", 1), {"method": "GET"}],
            "gauges": [("memory", 512), {"host": "server1"}],
            "timers": [("response", 0.5), {"endpoint": "/api"}],
        }

        exporter.export_batch(metrics)

        assert exporter.client.incr.call_count == 1
        assert exporter.client.gauge.call_count == 1
        assert exporter.client.timing.call_count == 1


@pytest.mark.unit
class TestMetricsAggregator:
    """指标聚合器测试"""

    @pytest.fixture
    def aggregator(self):
        """创建聚合器实例"""
        return MetricsAggregator(window_size=60, aggregation_interval=10)

    @pytest.fixture
    def sample_metrics(self):
        """示例指标数据"""
        return [
            {"name": "cpu_usage", "value": 50.0, "timestamp": time.time() - 55},
            {"name": "cpu_usage", "value": 60.0, "timestamp": time.time() - 45},
            {"name": "cpu_usage", "value": 55.0, "timestamp": time.time() - 35},
            {"name": "cpu_usage", "value": 70.0, "timestamp": time.time() - 25},
            {"name": "cpu_usage", "value": 65.0, "timestamp": time.time() - 15},
            {"name": "memory_usage", "value": 512, "timestamp": time.time() - 50},
            {"name": "memory_usage", "value": 600, "timestamp": time.time() - 40},
            {"name": "memory_usage", "value": 550, "timestamp": time.time() - 30},
        ]

    def test_add_metrics(self, aggregator, sample_metrics):
        """测试添加指标"""
        for metric in sample_metrics:
            aggregator.add_metric(metric)

        assert len(aggregator.metrics["cpu_usage"]) == 5
        assert len(aggregator.metrics["memory_usage"]) == 3

    def test_calculate_average(self, aggregator, sample_metrics):
        """测试计算平均值"""
        for metric in sample_metrics:
            aggregator.add_metric(metric)

        avg_cpu = aggregator.calculate_average("cpu_usage")
        avg_memory = aggregator.calculate_average("memory_usage")

        assert avg_cpu == 60.0  # (50+60+55+70+65)/5
        assert avg_memory == 554.0  # (512+600+550)/3

    def test_calculate_percentiles(self, aggregator, sample_metrics):
        """测试计算百分位数"""
        for metric in sample_metrics:
            aggregator.add_metric(metric)

        percentiles = aggregator.calculate_percentiles("cpu_usage", [50, 90, 95])

        assert percentiles[50] == 55.0  # 中位数
        assert percentiles[90] == 68.0  # 90百分位
        assert percentiles[95] == 69.5  # 95百分位

    def test_calculate_rate(self, aggregator):
        """测试计算速率"""
        current_time = time.time()

        # 添加计数器指标
        aggregator.add_metric(
            {"name": "requests", "value": 100, "timestamp": current_time - 60}
        )
        aggregator.add_metric(
            {"name": "requests", "value": 200, "timestamp": current_time - 30}
        )
        aggregator.add_metric(
            {"name": "requests", "value": 250, "timestamp": current_time}
        )

        rate = aggregator.calculate_rate("requests")

        # 250-100 = 150 requests in 60 seconds = 2.5 req/s
        assert abs(rate - 2.5) < 0.1

    def test_aggregate_by_time_window(self, aggregator, sample_metrics):
        """测试按时间窗口聚合"""
        for metric in sample_metrics:
            aggregator.add_metric(metric)

        # 按秒聚合
        aggregated = aggregator.aggregate_by_time_window("cpu_usage", window_seconds=20)

        assert len(aggregated) <= 3  # 60秒窗口，20秒间隔，最多3个点

    def test_remove_old_metrics(self, aggregator, sample_metrics):
        """测试移除旧指标"""
        for metric in sample_metrics:
            aggregator.add_metric(metric)

        # 添加一个超时的指标
        old_metric = {
            "name": "cpu_usage",
            "value": 30.0,
            "timestamp": time.time() - 120,  # 2分钟前
        }
        aggregator.add_metric(old_metric)

        # 清理旧指标
        aggregator.cleanup_old_metrics()

        # 验证旧指标被移除
        assert len(aggregator.metrics["cpu_usage"]) == 5
        assert all(
            m["timestamp"] > time.time() - 60 for m in aggregator.metrics["cpu_usage"]
        )

    def test_get_aggregated_summary(self, aggregator, sample_metrics):
        """测试获取聚合摘要"""
        for metric in sample_metrics:
            aggregator.add_metric(metric)

        summary = aggregator.get_summary()

        assert "cpu_usage" in summary
        assert "memory_usage" in summary
        assert "count" in summary["cpu_usage"]
        assert "average" in summary["cpu_usage"]
        assert "min" in summary["cpu_usage"]
        assert "max" in summary["cpu_usage"]


@pytest.mark.unit
class TestAlertManager:
    """告警管理器测试"""

    @pytest.fixture
    def alert_manager(self):
        """创建告警管理器实例"""
        manager = AlertManager()
        manager.logger = MagicMock()
        manager.notifier = MagicMock()
        return manager

    @pytest.fixture
    def alert_rules(self):
        """告警规则"""
        return [
            {
                "name": "high_cpu_usage",
                "metric": "cpu_usage",
                "condition": "greater_than",
                "threshold": 80,
                "duration": 300,  # 5分钟
                "severity": "warning",
            },
            {
                "name": "high_error_rate",
                "metric": "error_rate",
                "condition": "greater_than",
                "threshold": 10,
                "duration": 60,  # 1分钟
                "severity": "critical",
            },
            {
                "name": "low_memory",
                "metric": "memory_available",
                "condition": "less_than",
                "threshold": 100,
                "duration": 600,  # 10分钟
                "severity": "warning",
            },
        ]

    def test_add_alert_rule(self, alert_manager, alert_rules):
        """测试添加告警规则"""
        for rule in alert_rules:
            alert_manager.add_rule(rule)

        assert len(alert_manager.rules) == 3
        assert "high_cpu_usage" in alert_manager.rules
        assert alert_manager.rules["high_error_rate"]["severity"] == "critical"

    def test_evaluate_metric_against_rules(self, alert_manager, alert_rules):
        """测试根据规则评估指标"""
        for rule in alert_rules:
            alert_manager.add_rule(rule)

        # 测试触发告警
        test_metrics = {"cpu_usage": 85.0, "error_rate": 15.0, "memory_available": 50.0}

        alerts = alert_manager.evaluate_metrics(test_metrics)

        assert len(alerts) == 3
        assert any(a["rule"] == "high_cpu_usage" for a in alerts)
        assert any(a["rule"] == "high_error_rate" for a in alerts)
        assert any(a["rule"] == "low_memory" for a in alerts)

    def test_no_alert_when_threshold_not_met(self, alert_manager, alert_rules):
        """测试阈值未满足时不告警"""
        for rule in alert_rules:
            alert_manager.add_rule(rule)

        test_metrics = {
            "cpu_usage": 60.0,  # 低于80阈值
            "error_rate": 5.0,  # 低于10阈值
            "memory_available": 200.0,  # 高于100阈值
        }

        alerts = alert_manager.evaluate_metrics(test_metrics)

        assert len(alerts) == 0

    def test_alert_duration_requirement(self, alert_manager):
        """测试告警持续时间要求"""
        rule = {
            "name": "sustained_high_cpu",
            "metric": "cpu_usage",
            "condition": "greater_than",
            "threshold": 80,
            "duration": 60,  # 需要持续1分钟
            "severity": "warning",
        }
        alert_manager.add_rule(rule)

        # 第一次超过阈值（刚刚开始）
        start_time = time.time()
        alert_manager.evaluate_metric("cpu_usage", 85.0, start_time)
        alerts = alert_manager.get_active_alerts()
        assert len(alerts) == 0  # 还没到持续时间

        # 持续超过阈值
        alert_manager.evaluate_metric("cpu_usage", 85.0, start_time + 30)
        alert_manager.evaluate_metric("cpu_usage", 85.0, start_time + 61)
        alerts = alert_manager.get_active_alerts()
        assert len(alerts) == 1  # 现在应该告警了

    def test_alert_recovery(self, alert_manager):
        """测试告警恢复"""
        rule = {
            "name": "test_alert",
            "metric": "test_metric",
            "condition": "greater_than",
            "threshold": 10,
            "duration": 0,  # 立即告警
            "severity": "warning",
        }
        alert_manager.add_rule(rule)

        # 触发告警
        alert_manager.evaluate_metric("test_metric", 15.0)
        assert len(alert_manager.active_alerts) == 1

        # 恢复正常
        alert_manager.evaluate_metric("test_metric", 5.0)
        assert len(alert_manager.active_alerts) == 0

    def test_alert_notification(self, alert_manager):
        """测试告警通知"""
        rule = {
            "name": "critical_alert",
            "metric": "critical_metric",
            "condition": "greater_than",
            "threshold": 100,
            "duration": 0,
            "severity": "critical",
        }
        alert_manager.add_rule(rule)

        # 设置通知器
        alert_manager.notifier.send = AsyncMock(return_value=True)

        # 触发告警
        alerts = alert_manager.evaluate_metric("critical_metric", 150.0)

        # 发送通知（异步）
        import asyncio

        asyncio.run(alert_manager.send_notifications(alerts))

        # 验证通知被发送
        alert_manager.notifier.send.assert_called()
        call_args = alert_manager.notifier.send.call_args[0][0]
        assert call_args["rule"] == "critical_alert"
        assert call_args["severity"] == "critical"

    def test_alert_rate_limiting(self, alert_manager):
        """测试告警速率限制"""
        rule = {
            "name": "frequent_alert",
            "metric": "frequent_metric",
            "condition": "greater_than",
            "threshold": 10,
            "duration": 0,
            "severity": "warning",
            "rate_limit": 300,  # 5分钟内最多一次
        }
        alert_manager.add_rule(rule)

        # 第一次告警
        alert1 = alert_manager.evaluate_metric("frequent_metric", 15.0)
        assert len(alert1) == 1

        # 立即第二次告警（应该被限制）
        alert2 = alert_manager.evaluate_metric("frequent_metric", 16.0)
        assert len(alert2) == 0

    def test_get_alert_statistics(self, alert_manager):
        """测试获取告警统计"""
        rules = [
            {
                "name": "rule1",
                "metric": "metric1",
                "condition": ">",
                "threshold": 10,
                "duration": 0,
                "severity": "warning",
            },
            {
                "name": "rule2",
                "metric": "metric2",
                "condition": ">",
                "threshold": 20,
                "duration": 0,
                "severity": "critical",
            },
            {
                "name": "rule3",
                "metric": "metric3",
                "condition": ">",
                "threshold": 30,
                "duration": 0,
                "severity": "info",
            },
        ]
        for rule in rules:
            alert_manager.add_rule(rule)

        # 触发一些告警
        alert_manager.evaluate_metric("metric1", 15.0)
        alert_manager.evaluate_metric("metric2", 25.0)

        stats = alert_manager.get_statistics()

        assert stats["total_rules"] == 3
        assert stats["active_alerts"] == 2
        assert stats["alerts_by_severity"]["warning"] == 1
        assert stats["alerts_by_severity"]["critical"] == 1
        assert stats["alerts_by_severity"]["info"] == 0

    def test_export_alerts_to_json(self, alert_manager):
        """测试导出告警为JSON"""
        rule = {
            "name": "export_test",
            "metric": "test_metric",
            "condition": "greater_than",
            "threshold": 10,
            "duration": 0,
            "severity": "warning",
        }
        alert_manager.add_rule(rule)

        # 触发告警
        alert_manager.evaluate_metric("test_metric", 15.0)

        # 导出JSON
        json_data = alert_manager.export_alerts(format="json")

        assert "export_test" in json_data
        assert "severity" in json_data
        assert "timestamp" in json_data

        # 验证可以解析
        parsed = json.loads(json_data)
        assert parsed["rule"] == "export_test"
