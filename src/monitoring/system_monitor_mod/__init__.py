"""
系统监控器模块
System Monitor Module

提供全面的系统性能和健康状态监控。
"""

from .monitor import SystemMonitor
from .collectors import MetricsCollectorManager
from .health_checks import HealthChecker  # type: ignore


# 便捷函数
def get_system_monitor():
    """获取全局系统监控器实例"""
    if not hasattr(get_system_monitor, "_instance"):
        get_system_monitor._instance = SystemMonitor()
    return get_system_monitor._instance


__all__ = [
    "SystemMonitor",
    "MetricsCollectorManager",
    "HealthChecker",
    "get_system_monitor",
]
