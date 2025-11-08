from .metrics_collector_enhanced import EnhancedMetricsCollector as MetricsCollector
from .metrics_collector_enhanced import (
    MetricPoint,
    MetricsAggregator,
    get_metrics_collector,
    track_cache_performance,
    track_prediction_performance,
)

"""
监控指标收集器
Metrics Collector

统一指标收集入口,向后兼容原有接口.
"""

try:
    # from .metrics_collector_enhanced_mod.collector import EnhancedMetricsCollector
    # from .metrics_collector_enhanced_mod.aggregator import MetricsAggregator
    # from .metrics_collector_enhanced_mod.metric_types import MetricPoint
    pass
except ImportError:
    # 如果模块化实现有问题,使用基础实现
    pass


def start_metrics_collection():
    """函数文档字符串"""
    pass  # 添加pass语句
    """启动指标收集"""
    collector = get_metrics_collector()
    if hasattr(collector, "start"):
        collector.start()
    return True


def stop_metrics_collection():
    """函数文档字符串"""
    pass  # 添加pass语句
    """停止指标收集"""
    collector = get_metrics_collector()
    if hasattr(collector, "stop"):
        collector.stop()
    return True


__all__ = [
    "MetricsCollector",
    # "EnhancedMetricsCollector",  # 模块不存在,暂时注释
    "MetricsAggregator",
    "MetricPoint",
    "get_metrics_collector",
    "track_prediction_performance",
    "track_cache_performance",
    "start_metrics_collection",
    "stop_metrics_collection",
]
