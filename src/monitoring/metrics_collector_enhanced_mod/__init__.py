"""
指标收集器模块（兼容版本）
Metrics Collector Module (Compatibility Version)

为向后兼容而保留的简化实现
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
import time
import uuid


@dataclass
class MetricPoint:
    """指标数据点"""

    name: str
    value: float
    timestamp: Optional[datetime] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


class MetricsAggregator:
    """指标聚合器"""

    def __init__(self):
        self.metrics: Dict[str, List[MetricPoint]] = {}

    def add_metric(self, name: str, value: float):
        """添加指标"""
        if name not in self.metrics:
            self.metrics[name] = []
        self.metrics[name].append(MetricPoint(name, value))

    def get_average(self, name: str) -> float:
        """获取平均值"""
        points = self.metrics.get(name, [])
        return sum(p.value for p in points) / len(points) if points else 0.0

    def get_count(self, name: str) -> int:
        """获取计数"""
        return len(self.metrics.get(name, []))

    def get_sum(self, name: str) -> float:
        """获取总和"""
        return sum(p.value for p in self.metrics.get(name, []))


class EnhancedMetricsCollector:
    """增强的指标收集器"""

    def __init__(self):
        self.aggregator = MetricsAggregator()
        self.start_time = time.time()

    def track_metric(self, name: str, value: float):
        """跟踪指标"""
        self.aggregator.add_metric(name, value)

    def track_request_duration(self, duration: float):
        """跟踪请求持续时间"""
        self.track_metric("request_duration", duration)

    def track_prediction_count(self):
        """跟踪预测次数"""
        self.track_metric("prediction_count", 1)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """获取指标摘要"""
        return {
            "uptime": time.time() - self.start_time,
            "metrics": {
                name: {
                    "count": self.aggregator.get_count(name),
                    "sum": self.aggregator.get_sum(name),
                    "avg": self.aggregator.get_average(name),
                }
                for name in self.aggregator.metrics.keys()
            },
        }


# 全局实例
_collector = None


def get_metrics_collector() -> EnhancedMetricsCollector:
    """获取全局指标收集器实例"""
    global _collector
    if _collector is None:
        _collector = EnhancedMetricsCollector()
    return _collector


def track_prediction_performance(prediction_id: str, duration: float, success: bool):
    """跟踪预测性能"""
    collector = get_metrics_collector()
    collector.track_metric("prediction_duration", duration)
    if success:
        collector.track_metric("prediction_success", 1)
    else:
        collector.track_metric("prediction_failure", 1)


def track_cache_performance(cache_key: str, hit: bool):
    """跟踪缓存性能"""
    collector = get_metrics_collector()
    if hit:
        collector.track_metric("cache_hit", 1)
    else:
        collector.track_metric("cache_miss", 1)
