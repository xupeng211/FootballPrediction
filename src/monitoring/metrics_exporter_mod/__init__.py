"""
监控指标导出器模块 / Metrics Exporter Module

提供足球预测平台的各项监控指标导出功能，包括：
- 数据采集成功/失败次数
- 数据清洗成功/失败次数
- 调度任务延迟时间
- 数据表行数统计
- 系统健康状态

模块化结构：
- metric_definitions: Prometheus 指标定义
- data_collection_metrics: 数据采集指标记录
- data_cleaning_metrics: 数据清洗指标记录
- scheduler_metrics: 调度器指标记录
- database_metrics: 数据库指标记录
- metrics_exporter: 主导出器类
- utils: 工具函数
"""

from .metrics_exporter import (
    MetricsExporter,
    get_metrics_exporter,
    reset_metrics_exporter,
)

__all__ = [
    "MetricsExporter",
    "get_metrics_exporter",
    "reset_metrics_exporter",
]

__version__ = "1.0.0"
__author__ = "Football Prediction Team"
