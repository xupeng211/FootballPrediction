"""
指标类型定义
Metric Types Definition

定义指标的类型和单位枚举。
"""

from enum import Enum


class MetricType(Enum):
    """指标类型"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"


class MetricUnit(Enum):
    """指标单位"""

    COUNT = "count"
    PERCENT = "percent"
    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    BYTES = "bytes"
    REQUESTS_PER_SECOND = "requests_per_second"