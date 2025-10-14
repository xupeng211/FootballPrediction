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
"""

import logging
from typing import Any,  Dict[str, Any],  Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EnhancedMetricsCollector:
    """简化的增强指标收集器"""

    def __init__(self):
        self.metrics = {}

    def collect(self) -> Dict[str, Any]:
        """收集指标"""
        return {"timestamp": datetime.utcnow(), "metrics": self.metrics}

    def add_metric(self, name: str, value: Any):
        """添加指标"""
        self.metrics[name] = value
        logger.debug(f"Added metric: {name} = {value}")


class MetricsAggregator:
    """指标聚合器 - 简化版本"""

    def __init__(self):
        self.aggregated_metrics = {}

    def aggregate(self, metrics: Dict[str, Any]):
        """聚合指标"""
        for key, value in metrics.items():
            if key in self.aggregated_metrics:
                # 简单的聚合逻辑：取平均值
                self.aggregated_metrics[key] = (
                    self.aggregated_metrics[key] + value
                ) / 2
            else:
                self.aggregated_metrics[key] = value
        logger.debug(f"Aggregated {len(metrics)} metrics")

    def get_aggregated(self) -> Dict[str, Any]:
        """获取聚合后的指标"""
        return self.aggregated_metrics


class MetricPoint:
    """指标点 - 简化版本"""

    def __init__(self, name: str, value: float, timestamp: Optional[datetime] = None):
        self.name = name
        self.value = value
        self.timestamp = timestamp or datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {"name": self.name, "value": self.value, "timestamp": self.timestamp}


# 全局实例
_collector = None


def get_metrics_collector() -> EnhancedMetricsCollector:
    """获取全局指标收集器实例"""
    global _collector
    if _collector is None:
        _collector = EnhancedMetricsCollector()
    return _collector


def track_prediction_performance(prediction_id: str, accuracy: float):
    """跟踪预测性能"""
    collector = get_metrics_collector()
    collector.add_metric(f"prediction_{prediction_id}_accuracy", accuracy)
    logger.info(f"Tracked prediction performance: {prediction_id} - {accuracy}")


def track_cache_performance(cache_name: str, hit_rate: float):
    """跟踪缓存性能"""
    collector = get_metrics_collector()
    collector.add_metric(f"cache_{cache_name}_hit_rate", hit_rate)
    logger.info(f"Tracked cache performance: {cache_name} - {hit_rate}")


# 重新导出类型

# 保持原有的导出
__all__ = [
    "EnhancedMetricsCollector",
    "MetricsAggregator",
    "MetricPoint",
    "get_metrics_collector",
    "track_prediction_performance",
    "track_cache_performance",
]
