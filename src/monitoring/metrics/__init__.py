"""
监控指标模块
Monitoring Metrics Module

提供各种指标收集器、聚合器和导出器。
"""

from .types import MetricType, MetricUnit
from .aggregator import MetricsAggregator
from .exporters import StatsdExporter
from .base import BaseMetricsCollector
from .collectors import (
    MetricsCollector,
    SystemMetricsCollector,
    DatabaseMetricsCollector,
    ApplicationMetricsCollector,
)
from .global_collector import (
    get_metrics_collector,
    start_metrics_collection,
    stop_metrics_collection,
    get_async_session,
)

__all__ = [
    # Types
    "MetricType",
    "MetricUnit",
    # Aggregator
    "MetricsAggregator",
    # Exporters
    "StatsdExporter",
    # Base
    "BaseMetricsCollector",
    # Collectors
    "MetricsCollector",
    "SystemMetricsCollector",
    "DatabaseMetricsCollector",
    "ApplicationMetricsCollector",
    # Global functions
    "get_metrics_collector",
    "start_metrics_collection",
    "stop_metrics_collection",
    "get_async_session",
]

# =============================================================================
# 向后兼容性导入 - 暂时注释掉以避免循环导入
# =============================================================================

# 注释掉向后兼容性导入以避免循环导入
# 将在metrics_collector中重新导入

# 别名
# PrometheusExporter 从 metrics_exporter 导入，见下面