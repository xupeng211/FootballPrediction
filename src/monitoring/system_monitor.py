"""
系统监控器
System Monitor

统一系统监控入口,向后兼容原有接口.
"""

from typing import Any


class SystemMonitor:
    """系统监控器类"""

    def __init__(self):
        """初始化系统监控器"""
        self.metrics = {}

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """记录HTTP请求"""
        key = f"{method} {endpoint}"
        if key not in self.metrics:
            self.metrics[key] = {"count": 0, "total_duration": 0, "status_codes": {}}

        self.metrics[key]["count"] += 1
        self.metrics[key]["total_duration"] += duration

        status_key = str(status_code)
        if status_key not in self.metrics[key]["status_codes"]:
            self.metrics[key]["status_codes"][status_key] = 0
        self.metrics[key]["status_codes"][status_key] += 1

    def record_database_query(self, operation: str, table: str, duration: float, is_slow: bool = False):
        """记录数据库查询"""
        key = f"{operation} {table}"
        if key not in self.metrics:
            self.metrics[key] = {"count": 0, "total_duration": 0, "slow_queries": 0}

        self.metrics[key]["count"] += 1
        self.metrics[key]["total_duration"] += duration
        if is_slow:
            self.metrics[key]["slow_queries"] += 1

    def record_cache_operation(self, operation: str, cache_type: str, result: str):
        """记录缓存操作"""
        key = f"{operation} {cache_type}"
        if key not in self.metrics:
            self.metrics[key] = {"count": 0, "results": {}}

        self.metrics[key]["count"] += 1
        if result not in self.metrics[key]["results"]:
            self.metrics[key]["results"][result] = 0
        self.metrics[key]["results"][result] += 1

    def record_prediction(self, model_version: str, league: str):
        """记录预测"""
        key = f"{model_version} {league}"
        if key not in self.metrics:
            self.metrics[key] = {"count": 0}

        self.metrics[key]["count"] += 1

    def get_metrics(self) -> dict[str, Any]:
        """获取监控指标"""
        return self.metrics.copy()


# 全局监控器实例
_global_monitor = None


def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器实例"""
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = SystemMonitor()
    return _global_monitor


# 便捷函数 - 直接实现以保持向后兼容
def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """函数文档字符串"""
    pass  # 添加pass语句
    """记录HTTP请求"""
    monitor = get_system_monitor()
    monitor.record_request(method, endpoint, status_code, duration)


def record_db_query(operation: str, table: str, duration: float, is_slow: bool = False):
    """函数文档字符串"""
    pass  # 添加pass语句
    """记录数据库查询"""
    monitor = get_system_monitor()
    monitor.record_database_query(operation, table, duration, is_slow)


def record_cache_op(operation: str, cache_type: str, result: str):
    """函数文档字符串"""
    pass  # 添加pass语句
    """记录缓存操作"""
    monitor = get_system_monitor()
    monitor.record_cache_operation(operation, cache_type, result)


def record_prediction(model_version: str, league: str):
    """函数文档字符串"""
    pass  # 添加pass语句
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
