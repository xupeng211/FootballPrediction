"""
监控指标导出器 - 向后兼容性层

导出足球预测平台的各项监控指标，供 Prometheus 采集。
包括数据采集成功/失败次数、数据清洗成功/失败次数、调度任务延迟时间、数据表行数统计等。

注意：此文件已重构为模块化架构，保留此文件仅为了向后兼容性。
新代码应该直接使用 src.monitoring.metrics_exporter_mod 模块。
"""

# 从新模块导入所有公共接口
    MetricsExporter,
    get_metrics_exporter,
    reset_metrics_exporter,
)

# 重新导出以保持向后兼容性
__all__ = [
    "MetricsExporter",
    "get_metrics_exporter",
    "reset_metrics_exporter",
]

# 添加文档说明
_DEPRECATED_MSG = """
警告：此模块已弃用，请使用 src.monitoring.metrics_exporter_mod 模块。

旧用法：
    from src.monitoring.metrics_exporter import MetricsExporter

新用法：

或者继续使用当前导入，它将自动重定向到新模块。
"""