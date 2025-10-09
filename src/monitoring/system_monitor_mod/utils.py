"""
系统监控便捷函数和全局管理
"""

import logging
from typing import Optional

# 全局监控器实例
_system_monitor: Optional["SystemMonitor"] = None

logger = logging.getLogger(__name__)


def get_system_monitor() -> "SystemMonitor":
    """
    获取全局系统监控器实例

    Returns:
        SystemMonitor: 监控器实例
    """
    global _system_monitor
    if _system_monitor is None:
        from .monitor import SystemMonitor

        _system_monitor = SystemMonitor()
        logger.info("创建全局系统监控器实例")
    return _system_monitor


# 便捷函数
def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """
    记录HTTP请求的便捷函数

    Args:
        method: HTTP方法
        endpoint: 端点路径
        status_code: 状态码
        duration: 请求耗时（秒）
    """
    monitor = get_system_monitor()
    monitor.record_request(method, endpoint, status_code, duration)


def record_db_query(operation: str, table: str, duration: float, is_slow: bool = False):
    """
    记录数据库查询的便捷函数

    Args:
        operation: 操作类型（SELECT, INSERT, UPDATE, DELETE）
        table: 表名
        duration: 查询耗时（秒）
        is_slow: 是否为慢查询
    """
    monitor = get_system_monitor()
    monitor.record_database_query(operation, table, duration, is_slow)


def record_cache_op(operation: str, cache_type: str, result: str):
    """
    记录缓存操作的便捷函数

    Args:
        operation: 操作类型（get, set, delete）
        cache_type: 缓存类型（redis, memory）
        result: 操作结果（hit, miss, success, error）
    """
    monitor = get_system_monitor()
    monitor.record_cache_operation(operation, cache_type, result)


def record_prediction(model_version: str, league: str):
    """
    记录预测操作的便捷函数

    Args:
        model_version: 模型版本
        league: 联赛
    """
    monitor = get_system_monitor()
    monitor.record_prediction(model_version, league)


def record_model_inference(model_name: str, model_version: str, duration: float):
    """
    记录模型推理的便捷函数

    Args:
        model_name: 模型名称
        model_version: 模型版本
        duration: 推理耗时（秒）
    """
    monitor = get_system_monitor()
    monitor.record_model_inference(model_name, model_version, duration)


async def start_system_monitoring(interval: int = 30):
    """
    启动系统监控的便捷函数

    Args:
        interval: 监控数据收集间隔（秒）
    """
    monitor = get_system_monitor()
    await monitor.start_monitoring(interval)


async def stop_system_monitoring():
    """
    停止系统监控的便捷函数
    """
    monitor = get_system_monitor()
    await monitor.stop_monitoring()


async def get_system_health() -> dict:
    """
    获取系统健康状态的便捷函数

    Returns:
        dict: 健康状态报告
    """
    monitor = get_system_monitor()
    return await monitor.get_health_status()


async def collect_all_metrics() -> dict:
    """
    收集所有指标的便捷函数

    Returns:
        dict: 指标数据
    """
    monitor = get_system_monitor()
    return await monitor.collect_metrics()


def get_monitoring_status() -> dict:
    """
    获取监控状态的便捷函数

    Returns:
        dict: 监控状态信息
    """
    monitor = get_system_monitor()
    return monitor.get_monitoring_status()