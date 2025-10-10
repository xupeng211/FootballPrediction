"""
系统监控器
System Monitor

统一系统监控入口，向后兼容原有接口。
"""

# 为了向后兼容，从模块化实现重新导出
from .system_monitor_mod import (
    SystemMonitor,
    get_system_monitor,
)


# 便捷函数 - 直接实现以保持向后兼容
def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录HTTP请求"""
    monitor = get_system_monitor()
    monitor.record_request(method, endpoint, status_code, duration)


def record_db_query(operation: str, table: str, duration: float, is_slow: bool = False):
    """记录数据库查询"""
    monitor = get_system_monitor()
    monitor.record_database_query(operation, table, duration, is_slow)


def record_cache_op(operation: str, cache_type: str, result: str):
    """记录缓存操作"""
    monitor = get_system_monitor()
    monitor.record_cache_operation(operation, cache_type, result)


def record_prediction(model_version: str, league: str):
    """记录预测"""
    monitor = get_system_monitor()
    monitor.record_prediction(model_version, league)


__all__ = [
    "SystemMonitor",
    "get_system_monitor",
    "record_http_request",
    "record_db_query",
    "record_cache_op",
    "record_prediction",
]
