"""
ge_prometheus_exporter.py
ge_prometheus_exporter

此文件已被拆分为多个模块以提供更好的组织结构。
This file has been split into multiple modules for better organization.

为了向后兼容，此文件重新导出所有模块中的类。
For backward compatibility, this file re-exports all classes from the modules.
"""

import warnings

from .prometheus import collector, exporter, metrics, utils

warnings.warn(
    "直接从 ge_prometheus_exporter 导入已弃用。"
    "请从 src/data/quality/prometheus 导入相关类。",
    DeprecationWarning,
    stacklevel=2,
)

# 从新模块导入所有内容

# 为了向后兼容，创建别名
from .prometheus import PrometheusExporter as GEPrometheusExporter

# 导出所有类
__all__ = ["GEPrometheusExporter", "metrics", "collector", "exporter", "utils"]
