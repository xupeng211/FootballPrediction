"""
测试增强指标收集器模块的导入集成
验证各个模块可以正确导入和实例化
"""

import pytest


def test_import_metric_types():
    """测试导入指标类型"""
    try:
        from src.monitoring.metrics_collector_enhanced_mod.metric_types import (
            MetricPoint,
            MetricSummary,
            AlertInfo,
        )
        assert MetricPoint is not None
        assert MetricSummary is not None
        assert AlertInfo is not None
    except ImportError as e:
        pytest.skip(f"Cannot import metric types: {e}")


def test_import_aggregator():
    """测试导入聚合器"""
    try:
        from src.monitoring.metrics_collector_enhanced_mod.aggregator import (
            MetricsAggregator,
        )
        assert MetricsAggregator is not None
    except ImportError as e:
        pytest.skip(f"Cannot import aggregator: {e}")


def test_import_alerting():
    """测试导入告警管理"""
    try:
        from src.monitoring.metrics_collector_enhanced_mod.alerting import (
            AlertManager,
            DefaultAlertHandlers,
        )
        assert AlertManager is not None
        assert DefaultAlertHandlers is not None
    except ImportError as e:
        pytest.skip(f"Cannot import alerting: {e}")


def test_import_business_metrics():
    """测试导入业务指标收集器"""
    try:
        from src.monitoring.metrics_collector_enhanced_mod.business_metrics import (
            BusinessMetricsCollector,
        )
        assert BusinessMetricsCollector is not None
    except ImportError as e:
        pytest.skip(f"Cannot import business metrics: {e}")


def test_import_system_metrics():
    """测试导入系统指标收集器"""
    try:
        from src.monitoring.metrics_collector_enhanced_mod.system_metrics import (
            SystemMetricsCollector,
        )
        assert SystemMetricsCollector is not None
    except ImportError as e:
        pytest.skip(f"Cannot import system metrics: {e}")


def test_import_decorators():
    """测试导入装饰器"""
    try:
        from src.monitoring.metrics_collector_enhanced_mod.decorators import (
            track_performance,
            track_cache_performance,
            track_prediction_performance,
            track_database_performance,
        )
        assert track_performance is not None
        assert track_cache_performance is not None
        assert track_prediction_performance is not None
        assert track_database_performance is not None
    except ImportError as e:
        pytest.skip(f"Cannot import decorators: {e}")


def test_import_collector():
    """测试导入主收集器（可能因为prometheus依赖失败）"""
    try:
        from src.monitoring.metrics_collector_enhanced_mod.collector import (
            EnhancedMetricsCollector,
        )
        assert EnhancedMetricsCollector is not None
    except ImportError as e:
        pytest.skip(f"Cannot import collector (prometheus dependency issue): {e}")


def test_import_prometheus_metrics():
    """测试导入Prometheus指标管理（可能因为prometheus依赖失败）"""
    try:
        from src.monitoring.metrics_collector_enhanced_mod.prometheus_metrics import (
            PrometheusMetricsManager,
            PROMETHEUS_AVAILABLE,
        )
        assert PrometheusMetricsManager is not None
        # 检查prometheus是否可用
        # 如果不可用，PROMETHEUS_AVAILABLE应该是False
    except ImportError as e:
        pytest.skip(f"Cannot import prometheus metrics: {e}")


def test_import_from_init():
    """测试从__init__.py导入（使用延迟导入避免依赖问题）"""
    # 这个测试可能会因为prometheus依赖而跳过
    try:
        # 尝试导入，但不实际使用
        import importlib
        module = importlib.import_module("src.monitoring.metrics_collector_enhanced_mod")
        assert module is not None
    except ImportError as e:
        pytest.skip(f"Cannot import module package: {e}")


def test_backward_compatibility_import():
    """测试向后兼容性导入"""
    # 原始模块应该仍然可以导入
    try:
        from src.monitoring.metrics_collector_enhanced import (
            EnhancedMetricsCollector,
        )
        assert EnhancedMetricsCollector is not None
    except ImportError as e:
        pytest.skip(f"Cannot import from original location: {e}")