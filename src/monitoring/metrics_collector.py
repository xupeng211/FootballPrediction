"""
监控指标收集器
Metrics Collector

统一指标收集入口，向后兼容原有接口。
"""

# 为了向后兼容，从增强的模块化实现重新导出
from .metrics_collector_enhanced import (
    EnhancedMetricsCollector as MetricsCollector,
    MetricsAggregator,
    MetricPoint,
    get_metrics_collector,
    track_prediction_performance,
    track_cache_performance,
)

# 为了向后兼容，也导出一些原有的类名
try:
    # from .metrics_collector_enhanced_mod.collector import EnhancedMetricsCollector
    # from .metrics_collector_enhanced_mod.aggregator import MetricsAggregator
    # from .metrics_collector_enhanced_mod.metric_types import MetricPoint
    pass
except ImportError:
    # 如果模块化实现有问题，使用基础实现
    pass

# 便捷函数 - 直接实现以保持向后兼容
def start_metrics_collection():
    """启动指标收集"""
    collector = get_metrics_collector()
    if hasattr(collector, "start"):
        collector.start()
    return True

def stop_metrics_collection():
    """停止指标收集"""
    collector = get_metrics_collector()
    if hasattr(collector, "stop"):
        collector.stop()
    return True

__all__ = [
    "MetricsCollector",
    # "EnhancedMetricsCollector",  # 模块不存在，暂时注释
    "MetricsAggregator",
    "MetricPoint",
    "get_metrics_collector",
    "track_prediction_performance",
    "track_cache_performance",
    "start_metrics_collection",
    "stop_metrics_collection",
]
