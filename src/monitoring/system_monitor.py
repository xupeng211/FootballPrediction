"""
系统监控器
System Monitor

提供系统健康监控和指标收集功能。
"""

# 导入所有必要的类，保持向后兼容
from .system_metrics import SystemMetricsCollector
from .health_checker import HealthChecker, HealthStatus
from .system_monitor_core import SystemMonitor, get_system_monitor

# 导出所有公共接口
__all__ = [
    "SystemMonitor",
    "SystemMetricsCollector",
    "HealthChecker",
    "HealthStatus",
    "get_system_monitor",
]

# 便捷函数
from .system_monitor_core import (
    record_http_request,
    record_db_query,
    record_cache_op,
    record_prediction,
)
