"""
增强的指标收集器
Enhanced Metrics Collector

提供全面的业务和系统指标收集：
- 业务指标（预测数量、准确率等）
- 系统指标（延迟、吞吐量、错误率）
- 自定义指标和告警
- Prometheus集成

Provides comprehensive business and system metrics collection:
- Business metrics (prediction count, accuracy, etc.)
- System metrics (latency, throughput, error rate)
- Custom metrics and alerts
- Prometheus integration

该文件已重构为模块化架构，原始功能现在通过以下模块提供：
- metric_types: 指标数据类型定义
- aggregator: 指标聚合器
- prometheus_metrics: Prometheus指标管理
- business_metrics: 业务指标收集
- system_metrics: 系统指标收集
- alerting: 告警管理
- collector: 主收集器
- decorators: 性能跟踪装饰器

基于 MONITORING_DESIGN.md 第3.2节设计。
"""

from .metrics_collector_enhanced_mod import (
    # 为了向后兼容，从新的模块化实现重新导出
    EnhancedMetricsCollector,
    MetricsAggregator,
    MetricPoint,
    get_metrics_collector,
    track_prediction_performance,
    track_cache_performance,
)

# 重新导出类型

# 保持原有的导出
__all__ = [
    "EnhancedMetricsCollector",
    "MetricsAggregator",
    "MetricPoint",
    "MetricSummary",
    "AlertInfo",
    "get_metrics_collector",
    "track_prediction_performance",
    "track_cache_performance",
]
