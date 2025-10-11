"""
增强指标收集器模块化测试
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock


def test_module_imports():
    """测试模块导入"""
    # 测试导入新模块
    from src.metrics.collector.enhanced import (
        MetricPoint,
        MetricSummary,
        AlertInfo,
        MetricsAggregator,
        PrometheusMetricsManager,
        BusinessMetricsCollector,
        SystemMetricsCollector,
        AlertManager,
        EnhancedMetricsCollector,
        get_metrics_collector,
        track_prediction_performance,
        track_cache_performance,
        track_database_performance,
        DefaultAlertHandlers,
    )

    assert MetricPoint is not None
    assert MetricSummary is not None
    assert AlertInfo is not None
    assert MetricsAggregator is not None
    assert PrometheusMetricsManager is not None
    assert BusinessMetricsCollector is not None
    assert SystemMetricsCollector is not None
    assert AlertManager is not None
    assert EnhancedMetricsCollector is not None
    assert get_metrics_collector is not None
    assert track_prediction_performance is not None
    assert track_cache_performance is not None
    assert track_database_performance is not None
    assert DefaultAlertHandlers is not None


def test_metric_types():
    """测试指标数据类型"""
    from src.metrics.collector.enhanced import (
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
    from src.metrics.collector.enhanced import (
        MetricsAggregator,
        MetricPoint,
    )

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
    assert "{'env': 'test'}" in str(all_metrics["test_metric"])


def test_business_metrics_collector():
    """测试业务指标收集器"""
    from src.metrics.collector.enhanced import BusinessMetricsCollector
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

    # 获取业务摘要
    summary = collector.get_business_summary()
    assert "predictions" in summary
    assert "models" in summary
    assert summary["predictions"]["total"] == 1


def test_system_metrics_collector():
    """测试系统指标收集器"""
    from src.metrics.collector.enhanced import SystemMetricsCollector
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


def test_alert_manager():
    """测试告警管理器"""
    from src.metrics.collector.enhanced import AlertManager

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


def test_enhanced_metrics_collector():
    """测试增强指标收集器"""
    from src.metrics.collector.enhanced import EnhancedMetricsCollector

    # 创建收集器（不启动任务）
    collector = EnhancedMetricsCollector()

    # 记录预测指标
    collector.record_prediction(
        model_version="v1.0",
        predicted_result="home",
        confidence=0.85,
        duration=0.5,
        success=True,
    )

    # 记录错误
    collector.record_error("timeout", "database", "high")

    # 记录缓存操作
    collector.record_cache_operation(cache_type="redis", operation="get", hit=True)

    # 获取指标摘要
    summary = collector.get_metrics_summary()
    assert "business" in summary
    assert "system" in summary
    assert "alerts" in summary
    assert "aggregates" in summary

    # 验证业务指标
    assert summary["business"]["predictions"]["total"] == 1

    # 验证系统指标
    assert summary["system"]["errors"]["total"] == 1

    # 获取Prometheus指标
    prometheus_metrics = collector.get_prometheus_metrics()
    assert isinstance(prometheus_metrics, str)
    assert len(prometheus_metrics) > 0


@pytest.mark.asyncio
async def test_aggregation_task():
    """测试聚合任务"""
    from src.metrics.collector.enhanced import EnhancedMetricsCollector

    collector = EnhancedMetricsCollector()

    # 启动聚合任务
    await collector.start_aggregation_task(interval=1)

    # 记录一些指标
    collector.record_prediction(
        model_version="v1.0", predicted_result="home", confidence=0.85, duration=0.5
    )

    # 等待任务执行
    await asyncio.sleep(1.5)

    # 停止任务
    await collector.stop_aggregation_task()


def test_global_collector():
    """测试全局收集器"""
    from src.metrics.collector.enhanced import (
        get_metrics_collector,
        set_metrics_collector,
    )

    # 获取全局收集器
    collector1 = get_metrics_collector()
    assert collector1 is not None

    # 再次获取应该是同一个实例
    collector2 = get_metrics_collector()
    assert collector1 is collector2

    # 设置新的收集器（用于测试）
    mock_collector = Mock()
    set_metrics_collector(mock_collector)
    collector3 = get_metrics_collector()
    assert collector3 is mock_collector

    # 恢复默认收集器
    set_metrics_collector(None)


def test_backward_compatibility():
    """测试向后兼容性"""
    # 测试原始导入方式仍然有效
    from src.metrics.collector.enhanced import (
        EnhancedMetricsCollector,
        MetricsAggregator,
        MetricPoint,
        get_metrics_collector,
        track_prediction_performance,
    )

    # 验证类和函数可以导入
    assert EnhancedMetricsCollector is not None
    assert MetricsAggregator is not None
    assert MetricPoint is not None
    assert get_metrics_collector is not None
    assert track_prediction_performance is not None

    # 验证可以实例化
    collector = EnhancedMetricsCollector()
    assert collector is not None
    assert hasattr(collector, "record_prediction")


def test_decorators():
    """测试装饰器"""
    from src.metrics.collector.enhanced import (
        track_cache_performance,
        track_performance,
    )

    # 测试缓存性能装饰器
    @track_cache_performance(cache_type="redis")
    def cache_get(key):
        if key == "exists":
            return "value"
        return None

    result = cache_get("exists")
    assert result == "value"

    result = cache_get("not_exists")
    assert result is None

    # 测试通用性能装饰器
    @track_performance("test_operation")
    def test_function():
        return "test"

    result = test_function()
    assert result == "test"


@pytest.mark.asyncio
async def test_async_decorators():
    """测试异步装饰器"""
    from src.metrics.collector.enhanced import (
        track_prediction_performance,
    )

    @track_prediction_performance()
    async def predict_match(match_id: int, model_version: str = "v1.0"):
        # 模拟预测
        await asyncio.sleep(0.01)

        class Result:
            predicted_result = "home"
            confidence_score = 0.85

        return Result()

    result = await predict_match(123)
    assert result.predicted_result == "home"
    assert result.confidence_score == 0.85
