"""
监控指标收集器
Metrics Collector

统一指标收集入口,向后兼容原有接口.
"""

import logging
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)


# 为了向后兼容，添加 MetricsCollector 类
class MetricsCollector:
    """向后兼容的 MetricsCollector 类"""

    def __init__(self):
        """初始化指标收集器"""
        self.metrics = {}

    def initialize(self):
        """初始化指标收集器"""
        logger.info("✅ MetricsCollector initialized successfully")

    def collect(self) -> dict[str, Any]:
        """收集指标"""
        return {"timestamp": datetime.utcnow(), "metrics": self.metrics}

    def add_metric(self, name: str, value: Any):
        """添加指标"""
        self.metrics[name] = value


# 便捷函数 - 直接实现以保持向后兼容
def start_metrics_collection():
    """开始指标收集"""
    collector = get_metrics_collector()
    collector.initialize()
    logger.info("📊 Metrics collection started")
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
    # "MetricsCollector",  # 注释以避免F822错误
    # "EnhancedMetricsCollector",  # 模块不存在,暂时注释
    "MetricsAggregator",
    "MetricPoint",
    "get_metrics_collector",
    "track_prediction_performance",
    "track_cache_performance",
    "start_metrics_collection",
    "stop_metrics_collection",
]
