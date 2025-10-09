"""
增强的指标收集器模块 / Enhanced Metrics Collector Module

提供全面的业务和系统指标收集功能：
- 指标数据类型定义
- 指标聚合和存储
- Prometheus集成
- 业务和系统指标收集
- 告警管理
- 性能跟踪装饰器

主要组件 / Main Components:
    - MetricPoint: 指标数据点
    - MetricsAggregator: 指标聚合器
    - PrometheusMetricsManager: Prometheus指标管理
    - BusinessMetricsCollector: 业务指标收集
    - SystemMetricsCollector: 系统指标收集
    - AlertManager: 告警管理
    - EnhancedMetricsCollector: 主收集器

使用示例 / Usage Example:
    ```python
    from src.monitoring.metrics_collector_enhanced_mod import get_metrics_collector

    # 获取全局收集器
    collector = get_metrics_collector()

    # 记录预测指标
    collector.record_prediction(
        model_version="v1.0",
        predicted_result="home",
        confidence=0.85,
        duration=0.5,
        success=True
    )

    # 获取指标摘要
    summary = collector.get_metrics_summary()
    print(f"Total predictions: {summary['business']['predictions']['total']}")

    # 使用装饰器
    from .decorators import track_prediction_performance

    @track_prediction_performance()
    async def predict_match(match_id: int):
        # 预测逻辑
        return prediction
    ```

性能特性 / Performance Features:
    - 滑动窗口聚合
    - 百分位数计算
    - 内存优化
    - 异步任务支持
    - 可配置的告警规则
"""

# 导入主要类和函数
from .metric_types import MetricPoint, MetricSummary, AlertInfo
from .aggregator import MetricsAggregator
from .prometheus_metrics import PrometheusMetricsManager
from .business_metrics import BusinessMetricsCollector
from .system_metrics import SystemMetricsCollector
from .alerting import AlertManager, DefaultAlertHandlers
from .collector import (
    EnhancedMetricsCollector,
    get_metrics_collector,
    set_metrics_collector,
)
from .decorators import (
    track_prediction_performance,
    track_cache_performance,
    track_database_performance,
    track_performance,
)

# 导出主要组件
__all__ = [
    # 数据类型
    "MetricPoint",
    "MetricSummary",
    "AlertInfo",
    # 核心组件
    "MetricsAggregator",
    "PrometheusMetricsManager",
    "BusinessMetricsCollector",
    "SystemMetricsCollector",
    "AlertManager",
    "EnhancedMetricsCollector",
    # 全局函数
    "get_metrics_collector",
    "set_metrics_collector",
    # 告警
    "DefaultAlertHandlers",
    # 装饰器
    "track_prediction_performance",
    "track_cache_performance",
    "track_database_performance",
    "track_performance",
]
