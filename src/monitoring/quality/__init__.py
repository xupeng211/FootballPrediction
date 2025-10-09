"""
数据质量监控模块 / Data Quality Monitoring Module

负责监控数据新鲜度、缺失率、完整性等数据质量指标。
支持实时监控、历史趋势分析、质量评分计算等功能。

Responsible for monitoring data quality metrics such as freshness, missing rates, and completeness.
Supports real-time monitoring, historical trend analysis, and quality score calculation.
"""

from .core.monitor import QualityMonitor
from .core.results import DataFreshnessResult, DataCompletenessResult

__all__ = [
    "QualityMonitor",
    "DataFreshnessResult",
    "DataCompletenessResult",
]