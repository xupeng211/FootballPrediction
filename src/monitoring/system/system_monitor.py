"""
系统监控器主类

整合所有监控组件，提供统一的系统监控接口。
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from prometheus_client import CollectorRegistry

from .collectors import ApplicationCollector, CacheCollector, DatabaseCollector, SystemCollector
from .health import HealthChecker
from .metrics import SystemMetrics

logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    系统监控器主类

    提供全面的系统性能和健康状态监控
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        初始化系统监控器

        Args:
            registry: Prometheus注册表实例
        """
        self.registry = registry
        self.start_time = time.time()

        # 初始化指标
        self.metrics = SystemMetrics(registry)

        # 初始化收集器
        self.system_collector = SystemCollector(self.metrics, self.start_time)
        self.database_collector = DatabaseCollector(self.metrics)
        self.cache_collector = CacheCollector(self.metrics)
        self.application_collector = ApplicationCollector(self.metrics)

        # 初始化健康检查器
        self.health_checker = HealthChecker(
            self.database_collector,
            self.cache_collector,
        )

        # 监控状态
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

        # 监控间隔
        self.default_interval = 30  # 秒

    async def start_monitoring(self, interval: int = None):
        """
        启动系统监控

        Args:
            interval: 监控数据收集间隔（秒）
        """
        if self.is_monitoring:
            logger.warning("系统监控已经在运行中")
            return

        self.is_monitoring = True
        interval = interval or self.default_interval
        self.monitor_task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info(f"系统监控已启动，监控间隔: {interval}秒")

    async def stop_monitoring(self):
        """停止系统监控"""
        if not self.is_monitoring:
            return

        self.is_monitoring = False
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("系统监控已停止")

    async def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 收集各类指标
                await self.system_collector.collect()
                await self.database_collector.collect()
                await self.cache_collector.collect()
                await self.application_collector.collect()

                logger.debug("监控数据收集完成")
                # 等待下一次收集
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控数据收集失败: {e}")
                await asyncio.sleep(interval)

    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """
        记录HTTP请求

        Args:
            method: HTTP方法
            endpoint: 端点
            status_code: 状态码
            duration: 请求持续时间
        """
        self.application_collector.record_request(method, endpoint, status_code, duration)

    def record_database_query(
        self,
        operation: str,
        table: str,
        duration: float,
        is_slow: bool = False,
    ):
        """
        记录数据库查询

        Args:
            operation: 操作类型
            table: 表名
            duration: 查询持续时间
            is_slow: 是否是慢查询
        """
        self.database_collector.record_query(operation, table, duration, is_slow)

    def record_cache_operation(self, operation: str, cache_type: str, result: str):
        """
        记录缓存操作

        Args:
            operation: 操作类型
            cache_type: 缓存类型
            result: 操作结果
        """
        self.cache_collector.record_operation(operation, cache_type, result)

    def record_prediction(self, model_version: str, league: str):
        """
        记录预测事件

        Args:
            model_version: 模型版本
            league: 联赛
        """
        self.application_collector.record_prediction(model_version, league)

    def record_model_inference(self, model_name: str, model_version: str, duration: float):
        """
        记录模型推理

        Args:
            model_name: 模型名称
            model_version: 模型版本
            duration: 推理持续时间
        """
        self.application_collector.record_model_inference(model_name, model_version, duration)

    async def get_health_status(self) -> Dict[str, Any]:
        """
        获取系统健康状态

        Returns:
            健康状态报告
        """
        return await self.health_checker.check_all()

    async def get_monitoring_summary(self) -> Dict[str, Any]:
        """
        获取监控摘要

        Returns:
            监控摘要
        """
        try:
            # 获取系统信息
            system_info = self.system_collector.get_system_info()

            # 获取数据库统计
            db_stats = self.database_collector.get_query_stats()

            # 获取缓存统计
            cache_stats = self.cache_collector.get_cache_stats()

            # 获取应用统计
            app_stats = self.application_collector._get_request_summary()
            prediction_stats = self.application_collector._get_prediction_summary()
            collection_stats = self.application_collector._get_data_collection_summary()

            # 获取健康状态摘要
            health_summary = self.health_checker.get_health_summary()

            return {
                "timestamp": datetime.utcnow().isoformat(),
                "monitoring": {
                    "is_active": self.is_monitoring,
                    "uptime_seconds": time.time() - self.start_time,
                    "uptime_human": str(
                        time.gmtime(time.time() - self.start_time)
                    ).split(" GMT")[0],
                },
                "system": system_info,
                "database": {
                    "query_stats": db_stats,
                },
                "cache": cache_stats,
                "application": {
                    "requests": app_stats,
                    "predictions": prediction_stats,
                    "data_collection": collection_stats,
                },
                "health": health_summary,
            }

        except Exception as e:
            logger.error(f"获取监控摘要失败: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }


# 全局实例
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器实例"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


# 便捷函数
def record_http_request(method: str, endpoint: str, status_code: int, duration: float):
    """记录HTTP请求（便捷函数）"""
    monitor = get_system_monitor()
    monitor.record_request(method, endpoint, status_code, duration)


def record_db_query(operation: str, table: str, duration: float, is_slow: bool = False):
    """记录数据库查询（便捷函数）"""
    monitor = get_system_monitor()
    monitor.record_database_query(operation, table, duration, is_slow)


def record_cache_op(operation: str, cache_type: str, result: str):
    """记录缓存操作（便捷函数）"""
    monitor = get_system_monitor()
    monitor.record_cache_operation(operation, cache_type, result)


def record_prediction(model_version: str, league: str):
    """记录预测事件（便捷函数）"""
    monitor = get_system_monitor()
    monitor.record_prediction(model_version, league)


async def start_system_monitoring(interval: int = 30):
    """启动系统监控（便捷函数）"""
    monitor = get_system_monitor()
    await monitor.start_monitoring(interval)


async def stop_system_monitoring():
    """停止系统监控（便捷函数）"""
    monitor = get_system_monitor()
    await monitor.stop_monitoring()