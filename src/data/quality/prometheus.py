from typing import Any, Dict, List, Optional, Union
"""
Prometheus 导出器模块
Prometheus Exporter Module
"""

import logging


class PrometheusCollector:
    """Prometheus 指标收集器"""

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self.metrics = {}

    def register_metric(self, name: str, metric_type: str, help_text: str):
        """注册指标"""
        self.metrics[name] = {"type": metric_type, "help": help_text, "value": 0}

    def set_metric(self, name: str, value: float):
        """设置指标值"""
        if name in self.metrics:
            self.metrics[name]["value"] = value

    def get_metrics(self) -> Dict[str, Any]:
        """获取所有指标"""
        return self.metrics  # type: ignore


class PrometheusExporter:
    """Prometheus 导出器"""

    def __init__(self, collector: PrometheusCollector):
        self.collector = collector
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def export(self) -> str:
        """导出指标格式"""
        output: List[Any] = []
        for name, metric in self.collector.get_metrics().items():
            output.append(f"# HELP {name} {metric['help']}")
            output.append(f"# TYPE {name} {metric['type']}")
            output.append(f"{name} {metric['value']}")
        return "\n".join(output)


# 创建默认实例
collector = PrometheusCollector()
exporter = PrometheusExporter(collector)
metrics = {}  # type: ignore
utils = {}  # type: ignore

__all__ = ["collector", "exporter", "metrics", "utils"]
