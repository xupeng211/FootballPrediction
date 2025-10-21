"""
增强指标收集器模块化简化测试
"""

import pytest
from datetime import datetime


def test_metric_types():
    """测试指标数据类型"""
    from src.monitoring.metrics_collector_enhanced.metric_types import (
        MetricPoint,
        MetricSummary,
        AlertInfo,
    )

    # 测试MetricPoint
    point = MetricPoint(
        name="test_metric", value=100.5, labels={"env": "test"}, unit="ms"
    )
    assert point.name == "test_metric"
    assert point.value == 100.5
    assert point.labels["env"] == "test"
    assert point.unit == "ms"
    assert isinstance(point.timestamp, datetime)

    # 测试MetricSummary
    summary = MetricSummary(
        count=10, sum=1000.0, avg=100.0, min=50.0, max=150.0, last=95.0
    )
    assert summary.count == 10
    assert summary.avg == 100.0
    assert summary.min == 50.0
    assert summary.max == 150.0

    # 测试AlertInfo
    alert = AlertInfo(
        name="test_alert",
        message="Test alert message",
        severity="high",
        component="test_component",
    )
    assert alert.name == "test_alert"
    assert alert.message == "Test alert message"
    assert alert.severity == "high"
    assert alert.component == "test_component"


def test_metrics_aggregator():
    """测试指标聚合器"""
    from src.monitoring.metrics_collector_enhanced.aggregator import (
        MetricsAggregator,
    )
    from src.monitoring.metrics_collector_enhanced.metric_types import MetricPoint

    aggregator = MetricsAggregator(window_size=60)

    # 添加指标点
    point1 = MetricPoint(name="test_metric", value=100.0, labels={"env": "test"})
    aggregator.add_metric(point1)

    point2 = MetricPoint(name="test_metric", value=200.0, labels={"env": "test"})
    aggregator.add_metric(point2)

    # 获取指标聚合
    summary = aggregator.get_metric("test_metric", {"env": "test"})
    assert summary is not None
    assert summary.count == 2
    assert summary.avg == 150.0
    assert summary.min == 100.0
    assert summary.max == 200.0

    # 获取所有指标
    all_metrics = aggregator.get_all_metrics()
    assert "test_metric" in all_metrics

    # 测试清理过期指标
    counts = aggregator.get_metrics_count()
    assert counts["total_metrics"] > 0
    assert counts["active_aggregates"] > 0


def test_alert_manager():
    """测试告警管理器"""
    from src.monitoring.metrics_collector_enhanced.alerting import AlertManager

    alert_manager = AlertManager()

    # 添加告警规则
    def high_error_rate(metrics):
        return metrics.get("error_count", 0) > 10

    alert_manager.add_alert_rule(
        name="high_error_rate",
        condition=high_error_rate,
        severity="high",
        description="Error rate is too high",
    )

    # 检查告警（不应触发）
    alert_manager.check_alerts({"error_count": 5})
    assert len(alert_manager.get_active_alerts()) == 0

    # 触发告警
    alert_manager.check_alerts({"error_count": 15})
    assert len(alert_manager.get_active_alerts()) == 1
    active_alert = alert_manager.get_active_alerts()[0]
    assert active_alert.name == "high_error_rate"
    assert active_alert.severity == "high"

    # 解决告警
    alert_manager.resolve_alert("high_error_rate")
    assert len(alert_manager.get_active_alerts()) == 0

    # 测试告警摘要
    summary = alert_manager.get_alert_summary()
    assert "active_alerts" in summary
    assert "total_rules" in summary
    assert summary["total_rules"] == 1


def test_system_metrics_collector():
    """测试系统指标收集器"""
    from src.monitoring.metrics_collector_enhanced.system_metrics import (
        SystemMetricsCollector,
    )
    from unittest.mock import Mock

    prometheus_manager = Mock()
    aggregator = Mock()
    aggregator.add_metric = Mock()

    collector = SystemMetricsCollector(prometheus_manager, aggregator)

    # 记录错误
    collector.record_error("timeout", "database", "high")
    error_key = "database:timeout"
    assert error_key in collector.error_counts
    assert collector.error_counts[error_key] == 1

    # 记录缓存操作
    collector.record_cache_operation(
        cache_type="redis", operation="get", hit=True, size=1000
    )
    assert "redis" in collector.cache_stats
    assert collector.cache_stats["redis"]["hits"] == 1
    assert collector.cache_stats["redis"]["last_size"] == 1000

    # 更新连接指标
    collector.update_connection_metrics({"database": 10, "redis": 5})
    # 验证prometheus.set_gauge被调用
    assert prometheus_manager.set_gauge.called

    # 获取系统摘要
    summary = collector.get_system_summary()
    assert "errors" in summary
    assert "cache" in summary
    assert summary["errors"]["total"] == 1


def test_business_metrics_collector():
    """测试业务指标收集器"""
    from src.monitoring.metrics_collector_enhanced.business_metrics import (
        BusinessMetricsCollector,
    )
    from unittest.mock import Mock

    prometheus_manager = Mock()
    aggregator = Mock()
    aggregator.add_metric = Mock()

    collector = BusinessMetricsCollector(prometheus_manager, aggregator)

    # 记录预测指标
    collector.record_prediction(
        model_version="v1.0",
        predicted_result="home",
        confidence=0.85,
        duration=0.5,
        success=True,
    )

    # 验证统计更新
    assert collector.predictions_total == 1
    assert "v1.0" in collector.model_stats
    assert collector.model_stats["v1.0"]["predictions"] == 1

    # 记录预测验证
    collector.record_prediction_verification("v1.0", is_correct=True)
    assert collector.predictions_verified == 1
    assert collector.predictions_correct == 1

    # 记录模型加载
    collector.record_model_load("test_model", "v1.0", True, 0.1)
    assert collector.model_loads == 1

    # 记录数据收集
    collector.record_data_collection("api", "matches", 100, True, 5.0)

    # 记录价值投注
    collector.record_value_bet("bet365", "high", 1.2)

    # 获取业务摘要
    summary = collector.get_business_summary()
    assert "predictions" in summary
    assert "models" in summary
    assert summary["predictions"]["total"] == 1
    assert summary["models"]["total_loads"] == 1


def test_backward_compatibility():
    """测试向后兼容性"""
    # 测试原始导入方式仍然有效
    from src.metrics.collector.enhanced import (
        EnhancedMetricsCollector,
        MetricsAggregator,
        MetricPoint,
        get_metrics_collector,
    )

    # 测试基本功能
    collector = get_metrics_collector()
    assert collector is not None

    # 测试MetricPoint
    point = MetricPoint("test", 1.0)
    assert point.name == "test"
    assert point.value == 1.0


def test_decorators():
    """测试装饰器"""
    from src.monitoring.metrics_collector_enhanced.decorators import (
        track_cache_performance,
        track_performance,
    )

    # 测试缓存性能装饰器
    @track_cache_performance(cache_type_param="cache_type")
    def cache_get(key, cache_type="redis"):
        if key == "exists":
            return "value"
        return None

    _result = cache_get("exists")
    assert _result == "value"

    _result = cache_get("not_exists", cache_type="redis")
    assert _result is None

    # 测试通用性能装饰器
    @track_performance(metric_name="test_operation")
    def test_function():
        return "test"

    _result = test_function()
    assert _result == "test"


def test_alert_handlers():
    """测试告警处理器"""
    from src.monitoring.metrics_collector_enhanced.alerting import (
        DefaultAlertHandlers,
        AlertInfo,
    )
    from datetime import datetime
    from unittest.mock import patch

    # 创建测试告警
    alert = AlertInfo(
        name="test_alert",
        message="Test message",
        severity="high",
    )

    # 测试日志处理器
    with patch(
        "src.monitoring.metrics_collector_enhanced.alerting.logger"
    ) as mock_logger:
        DefaultAlertHandlers.log_handler(alert)
        assert mock_logger.error.called

    # 测试控制台处理器
    with patch("builtins.print") as mock_print:
        DefaultAlertHandlers.console_handler(alert)
        assert mock_print.called

    # 测试Webhook处理器工厂
    webhook_handler = DefaultAlertHandlers.webhook_handler("http://test.com/webhook")
    assert callable(webhook_handler)


def test_metric_summary():
    """测试指标摘要"""
    from src.monitoring.metrics_collector_enhanced.metric_types import MetricSummary

    summary = MetricSummary(
        count=100,
        sum=10000.0,
        avg=100.0,
        min=10.0,
        max=200.0,
        last=95.0,
        p50=98.0,
        p95=150.0,
        p99=190.0,
    )

    # 转换为字典
    summary_dict = summary.to_dict()
    assert summary_dict["count"] == 100
    assert summary_dict["avg"] == 100.0
    assert summary_dict["p95"] == 150.0
    assert summary_dict["p99"] == 190.0


def test_alert_info():
    """测试告警信息"""
    from src.monitoring.metrics_collector_enhanced.metric_types import AlertInfo
    from datetime import datetime

    alert = AlertInfo(
        name="test_alert",
        message="Test alert message",
        severity="critical",
        component="test_module",
        labels={"env": "production"},
    )

    # 转换为字典
    alert_dict = alert.to_dict()
    assert alert_dict["name"] == "test_alert"
    assert alert_dict["severity"] == "critical"
    assert alert_dict["component"] == "test_module"
    assert alert_dict["labels"]["env"] == "production"
    assert isinstance(alert_dict["timestamp"], str)
