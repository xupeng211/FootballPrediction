"""
告警指标模块

导出Prometheus指标管理器。
"""


from .prometheus_metrics import PrometheusMetrics

__all__ = ["PrometheusMetrics"]
