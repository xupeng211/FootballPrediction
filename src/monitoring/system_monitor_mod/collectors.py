"""
监控数据收集器
"""

import asyncio
import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

import psutil

from .metrics import get_prometheus_metrics
from ...cache.redis_manager import get_redis_manager
from ...database.connection import DatabaseManager, get_async_session
from sqlalchemy import text

logger = logging.getLogger(__name__)


class BaseMetricsCollector:
    """
    基础指标收集器
    """

    def __init__(self):
        self.metrics = get_prometheus_metrics()
        self.logger = logging.getLogger(self.__class__.__name__)

    async def collect(self) -> Dict[str, Any]:
        """
        收集指标数据

        Returns:
            Dict[str, Any]: 收集的指标数据
        """
        raise NotImplementedError


class SystemMetricsCollector(BaseMetricsCollector):
    """
    系统资源指标收集器
    """

    def __init__(self, start_time: float):
        super().__init__()
        self.start_time = start_time

    async def collect(self) -> Dict[str, Any]:
        """收集系统资源指标"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.metrics.system_cpu_percent.set(cpu_percent)

            # 内存使用率
            memory = psutil.virtual_memory()
            self.metrics.system_memory_percent.set(memory.percent)

            # 磁盘使用率
            disk = psutil.disk_usage("/")
            self.metrics.system_disk_percent.set(disk.percent)

            # 进程资源使用
            process = psutil.Process()
            self.metrics.process_memory_bytes.set(process.memory_info().rss)
            self.metrics.process_cpu_percent.set(process.cpu_percent())

            # 应用运行时间
            uptime = time.time() - self.start_time
            self.metrics.app_uptime_seconds.set(uptime)

            return {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": disk.percent,
                "process_memory_bytes": process.memory_info().rss,
                "process_cpu_percent": process.cpu_percent(),
                "uptime_seconds": uptime,
            }

        except Exception as e:
            self.logger.error(f"收集系统指标失败: {e}")
            return {"error": str(e)}


class DatabaseMetricsCollector(BaseMetricsCollector):
    """
    数据库指标收集器
    """

    async def collect(self) -> Dict[str, Any]:
        """收集数据库指标"""
        try:
            db_manager = DatabaseManager()

            # 获取连接池状态
            pool_status = {}
            if db_manager._sync_engine and db_manager._sync_engine.pool:
                pool = db_manager._sync_engine.pool
                pool_status = {
                    "size": pool.size(),
                    "checked_in": pool.checkedin(),
                    "checked_out": pool.checkedout(),
                    "overflow": pool.overflow(),
                    "invalidated": pool.invalidated(),
                }

                # 设置连接池指标
                self.metrics.db_connections_active.set(pool.checkedout())
                self.metrics.db_connections_total.set(pool.size())

            # 查询数据库统计信息
            connection_status = 0
            async with get_async_session() as session:
                try:
                    # 检查数据库连接状态
                    result = await session.execute(text("SELECT 1"))
                    connection_status = 1 if result.scalar() == 1 else 0

                except Exception as e:
                    self.logger.error(f"数据库健康检查失败: {e}")

            return {
                "connection_status": connection_status,
                "pool_status": pool_status,
            }

        except Exception as e:
            self.logger.error(f"收集数据库指标失败: {e}")
            return {"error": str(e)}


class CacheMetricsCollector(BaseMetricsCollector):
    """
    缓存指标收集器
    """

    async def collect(self) -> Dict[str, Any]:
        """收集缓存指标"""
        try:
            redis_manager = get_redis_manager()
            cache_info = {}

            # 尝试获取Redis信息
            try:
                info = redis_manager.get_info()
                if info:
                    cache_info.update(info)

                    # Redis内存使用
                    if "used_memory" in info:
                        self.metrics.cache_size_bytes.labels(cache_type="redis").set(
                            info["used_memory"]
                        )

                    # 连接数（如果可用）
                    if "connected_clients" in info:
                        cache_info["connected_clients"] = info["connected_clients"]

            except Exception as e:
                self.logger.warning(f"Redis信息获取失败: {e}")

            return cache_info

        except Exception as e:
            self.logger.error(f"收集缓存指标失败: {e}")
            return {"error": str(e)}


class ApplicationMetricsCollector(BaseMetricsCollector):
    """
    应用指标收集器
    """

    async def collect(self) -> Dict[str, Any]:
        """收集应用指标"""
        try:
            # 这里可以添加应用特定的指标收集逻辑
            # 比如活跃用户数、当前处理的请求数等

            # 示例：收集最近的错误率
            app_metrics = {
                "timestamp": datetime.now().isoformat(),
            }

            return app_metrics

        except Exception as e:
            self.logger.error(f"收集应用指标失败: {e}")
            return {"error": str(e)}


class MetricsCollectorManager:
    """
    指标收集器管理器

    管理所有的指标收集器，协调数据收集。
    """

    def __init__(self, start_time: float):
        """
        初始化收集器管理器

        Args:
            start_time: 应用启动时间
        """
        self.start_time = start_time
        self.collectors = {
            "system": SystemMetricsCollector(start_time),
            "database": DatabaseMetricsCollector(),
            "cache": CacheMetricsCollector(),
            "application": ApplicationMetricsCollector(),
        }
        self.logger = logging.getLogger(__name__)

    async def collect_all(self) -> Dict[str, Dict[str, Any]]:
        """
        收集所有指标

        Returns:
            Dict[str, Dict[str, Any]]: 所有收集器的指标数据
        """
        results = {}

        # 并行收集所有指标
        tasks = []
        for name, collector in self.collectors.items():
            task = asyncio.create_task(self._collect_with_error_handling(name, collector))
            tasks.append((name, task))

        # 等待所有收集完成
        for name, task in tasks:
            try:
                result = await task
                results[name] = result
            except Exception as e:
                self.logger.error(f"收集器 {name} 执行失败: {e}")
                results[name] = {"error": str(e)}

        return results

    async def _collect_with_error_handling(
        self, name: str, collector: BaseMetricsCollector
    ) -> Dict[str, Any]:
        """
        带错误处理的指标收集

        Args:
            name: 收集器名称
            collector: 收集器实例

        Returns:
            Dict[str, Any]: 收集结果
        """
        try:
            return await collector.collect()
        except Exception as e:
            self.logger.error(f"收集器 {name} 失败: {e}")
            return {"error": str(e)}

    def add_collector(self, name: str, collector: BaseMetricsCollector):
        """
        添加自定义收集器

        Args:
            name: 收集器名称
            collector: 收集器实例
        """
        self.collectors[name] = collector
        self.logger.info(f"添加自定义收集器: {name}")

    def remove_collector(self, name: str):
        """
        移除收集器

        Args:
            name: 收集器名称
        """
        if name in self.collectors:
            del self.collectors[name]
            self.logger.info(f"移除收集器: {name}")

    def get_collectors(self) -> Dict[str, BaseMetricsCollector]:
        """
        获取所有收集器

        Returns:
            Dict[str, BaseMetricsCollector]: 收集器字典
        """
        return self.collectors.copy()