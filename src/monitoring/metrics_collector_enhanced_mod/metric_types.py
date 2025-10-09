"""
指标数据类型定义 / Metric Data Types

定义指标收集相关的数据类型和基础结构。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any


@dataclass
class MetricPoint:
    """指标数据点

    表示单个时间点的指标值，包含名称、值、标签和时间戳。
    """

    name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    unit: str = ""

    def __post_init__(self):
        """初始化后处理"""
        if isinstance(self.timestamp, str):
            # 支持字符串时间戳
            self.timestamp = datetime.fromisoformat(self.timestamp)


@dataclass
class MetricSummary:
    """指标摘要

    表示一段时间内的指标聚合统计。
    """

    count: int
    sum: float
    avg: float
    min: float
    max: float
    last: float
    p50: float = 0.0
    p95: float = 0.0
    p99: float = 0.0

    def to_dict(self) -> Dict[str, float]:
        """转换为字典"""
        return {
            "count": self.count,
            "sum": self.sum,
            "avg": self.avg,
            "min": self.min,
            "max": self.max,
            "last": self.last,
            "p50": self.p50,
            "p95": self.p95,
            "p99": self.p99,
        }


@dataclass
class AlertInfo:
    """告警信息

    表示一个告警的详细信息。
    """

    name: str
    message: str
    severity: str
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = ""
    labels: Dict[str, str] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "message": self.message,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat(),
            "component": self.component,
            "labels": self.labels,
        }
