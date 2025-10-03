"""

监控指标收集器

定期收集和更新各种监控指标，包括系统状态、数据库指标等。
"""

import asyncio
import logging
import os
import signal
from datetime import datetime
from typing import Any, Dict, Optional

from .metrics_exporter import get_metrics_exporter

logger = logging.getLogger(__name__)

ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"


class MetricsCollector:
    """
    监控指标收集器

    定期收集和更新监控指标，运行在后台任务中
    """

    def __init__(self, collection_interval: int = 30):
        """
        初始化指标收集器

        Args:
            collection_interval: 收集间隔（秒），默认30秒
        """
        self.collection_interval = collection_interval
        self.metrics_exporter = get_metrics_exporter()
        self.running = False
        self.enabled = True  # 添加enabled属性
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """
        启动指标收集器
        """
        if self.running:
            logger.warning("指标收集器已在运行中")
            return

        self.running = True
        self._task = asyncio.create_task(self._collection_loop())

        # 注册信号处理器用于优雅关闭
        try:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
        except ValueError:
            # 在非主线程中无法注册信号处理器
            pass

        logger.info(f"指标收集器已启动，收集间隔: {self.collection_interval}秒")

    async def stop(self) -> None:
        """
        停止指标收集器
        """
        if not self.running:
            logger.warning("指标收集器未运行")
            return

        self.running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info("指标收集任务已被取消")

        logger.info("指标收集器已停止")

    def enable(self) -> None:
        """启用指标收集器"""
        self.enabled = True
        logger.info("指标收集器已启用")

    def disable(self) -> None:
        """禁用指标收集器"""
        self.enabled = False
        logger.info("指标收集器已禁用")

    def set_collection_interval(self, interval: float) -> None:
        """设置收集间隔"""
        self.collection_interval = int(interval)
        logger.info(f"收集间隔已设置为 {interval} 秒")

    def _signal_handler(self, signum: int, frame) -> None:
        """
        信号处理器，用于优雅关闭
        """
        logger.info(f"接收到信号 {signum}，准备停止指标收集器")
        asyncio.create_task(self.stop())

    async def _collection_loop(self) -> None:
        """
        指标收集主循环
        """
        logger.info("开始监控指标收集循环")

        while self.running:
            try:
                collection_start = datetime.now()

                # 收集所有指标
                await self.metrics_exporter.collect_all_metrics()

                collection_duration = (
                    datetime.now() - collection_start
                ).total_seconds()
                logger.debug(f"指标收集完成，耗时: {collection_duration:.2f}秒")

                # 等待下一次收集
                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                logger.info("指标收集循环被取消")
                break
            except Exception as e:
                logger.error(f"指标收集过程中发生错误: {e}", exc_info=True)
                # 出错后等待一段时间再继续
                await asyncio.sleep(min(self.collection_interval, 60))

    async def collect_once(self) -> Dict[str, Any]:
        """
        执行一次指标收集

        Returns:
            Dict[str, Any]: 收集结果统计
        """
        try:
            start_time = datetime.now()

            await self.metrics_exporter.collect_all_metrics()

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "success": True,
                "collection_time": start_time.isoformat(),
                "duration_seconds": duration,
                "message": "指标收集成功",
            }

            logger.info(f"手动指标收集完成，耗时: {duration:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"手动指标收集失败: {e}", exc_info=True)
            return {
                "success": False,
                "collection_time": datetime.now().isoformat(),
                "error": str(e),
                "message": "指标收集失败",
            }

    def get_status(self) -> Dict[str, Any]:
        """
        获取收集器状态

        Returns:
            Dict[str, Any]: 收集器状态信息
        """
        return {
            "running": self.running,
            "collection_interval": self.collection_interval,
            "task_status": (
                "running" if self._task and not self._task.done() else "stopped"
            ),
        }

    def collect_system_metrics(self) -> Dict[str, Any]:
        """
        收集系统指标

        Returns:
            Dict[str, Any]: 系统指标数据
        """
        try:
            import psutil

            # 收集CPU使用率
            cpu_usage = psutil.cpu_percent(interval=1)

            # 收集内存使用情况
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            memory_available = memory.available

            # 收集磁盘使用情况
            disk = psutil.disk_usage("/")
            disk_usage = disk.percent
            disk_free = disk.free

            return {
                "cpu_usage_percent": cpu_usage,
                "memory_usage_percent": memory_usage,
                "memory_available_bytes": memory_available,
                "disk_usage_percent": disk_usage,
                "disk_free_bytes": disk_free,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"收集系统指标失败: {e}")
            return {"error": str(e)}

    async def collect_database_metrics(self) -> Dict[str, Any]:
        """
        收集数据库指标

        Returns:
            Dict[str, Any]: 数据库指标数据
        """
        try:
            # 模拟数据库指标收集，避免真实数据库依赖
            table_counts = {
                "matches": 1000,
                "odds": 5000,
                "predictions": 500,
                "teams": 100,
            }

            return {
                "table_counts": table_counts,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"收集数据库指标失败: {e}")
            return {"error": str(e)}

    def collect_application_metrics(self) -> Dict[str, Any]:
        """
        收集应用指标

        Returns:
            Dict[str, Any]: 应用指标数据
        """
        try:
            prediction_stats = self._get_prediction_stats()

            return {
                "prediction_stats": prediction_stats,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"收集应用指标失败: {e}")
            return {"error": str(e)}

    def _get_prediction_stats(self) -> Dict[str, Any]:
        """
        获取预测统计信息

        Returns:
            Dict[str, Any]: 预测统计数据
        """
        # 返回模拟的预测统计数据
        return {
            "total_predictions": 1000,
            "accuracy_rate": 0.65,
            "avg_confidence": 0.78,
            "last_24h_predictions": 50,
        }

    def format_metrics_for_export(self, raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """
        格式化指标用于导出

        Args:
            raw_metrics: 原始指标数据

        Returns:
            Dict[str, Any]: 格式化后的指标数据
        """
        return {
            "timestamp": datetime.now().isoformat(),
            "metrics": raw_metrics,
            "export_format": "prometheus",
            "version": "1.0.0",
        }


# 用于测试的get_async_session函数
async def get_async_session():
    """
    获取异步数据库会话

    在测试环境中返回模拟会话
    """
    from unittest.mock import AsyncMock

    mock_session = AsyncMock()
    return mock_session


# 全局指标收集器实例
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    获取全局指标收集器实例

    Returns:
        MetricsCollector: 指标收集器实例
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


async def start_metrics_collection() -> None:
    """
    启动监控指标收集
    """
    if not ENABLE_METRICS:
        logger.info("ENABLE_METRICS=false，跳过指标收集器启动")
        return

    collector = get_metrics_collector()
    await collector.start()


async def stop_metrics_collection() -> None:
    """
    停止监控指标收集
    """
    collector = get_metrics_collector()
    await collector.stop()


class SystemMetricsCollector(MetricsCollector):
    """
    系统指标收集器

    收集CPU、内存、磁盘、网络等系统级指标
    """

    def __init__(self):
        """初始化系统指标收集器"""
        super().__init__(collection_interval=30)
        self.logger = logging.getLogger(__name__ + ".SystemMetricsCollector")

    def enable(self) -> None:
        """启用收集器"""
        self.enabled = True
        self.logger.info("系统指标收集器已启用")

    def disable(self) -> None:
        """禁用收集器"""
        self.enabled = False
        self.logger.info("系统指标收集器已禁用")

    async def collect_cpu_metrics(self) -> Dict[str, Any]:
        """
        收集CPU指标

        Returns:
            Dict[str, Any]: CPU使用率等指标
        """
        if not self.enabled:
            return {}

        try:
            import psutil

            # 获取CPU使用率可能抛出TimeoutError
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_count = psutil.cpu_count()

            return {
                "cpu_usage_percent": cpu_percent,
                "cpu_count": cpu_count,
                "timestamp": datetime.now().isoformat(),
            }
        except ImportError:
            self.logger.warning("psutil未安装，无法收集CPU指标")
            return {}
        except TimeoutError:
            self.logger.warning("CPU指标收集超时")
            return {}
        except Exception as e:
            self.logger.error(f"CPU指标收集失败: {e}")
            return {}

    async def collect_memory_metrics(self) -> Dict[str, Any]:
        """
        收集内存指标

        Returns:
            Dict[str, Any]: 内存使用情况指标
        """
        if not self.enabled:
            return {}

        try:
            import psutil

            memory = psutil.virtual_memory()

            return {
                "memory_usage_percent": memory.percent,
                "memory_total": memory.total,
                "memory_available": memory.available,
                "memory_used": memory.used,
                "timestamp": datetime.now().isoformat(),
            }
        except ImportError:
            self.logger.warning("psutil未安装，无法收集内存指标")
            return {}
        except Exception as e:
            self.logger.error(f"收集内存指标失败: {e}")
            return {}

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """
        收集所有系统指标

        Returns:
            Dict[str, Any]: 所有系统指标的汇总
        """
        if not self.enabled:
            return {}

        cpu_metrics = await self.collect_cpu_metrics()
        memory_metrics = await self.collect_memory_metrics()

        return {
            "system_metrics": {
                **cpu_metrics,
                **memory_metrics,
                "collection_time": datetime.now().isoformat(),
            }
        }


class DatabaseMetricsCollector(MetricsCollector):
    """
    数据库指标收集器

    收集数据库连接数、查询性能、表大小等指标
    """

    def __init__(self):
        """初始化数据库指标收集器"""
        super().__init__(collection_interval=60)
        self.logger = logging.getLogger(__name__ + ".DatabaseMetricsCollector")

    def enable(self) -> None:
        """启用收集器"""
        self.enabled = True
        self.logger.info("数据库指标收集器已启用")

    def disable(self) -> None:
        """禁用收集器"""
        self.enabled = False
        self.logger.info("数据库指标收集器已禁用")

    async def collect_connection_metrics(self) -> Dict[str, Any]:
        """
        收集数据库连接指标

        Returns:
            Dict[str, Any]: 连接池状态等指标
        """
        if not self.enabled:
            return {}

        try:
            # 这里应该连接到实际的数据库管理器
            # 暂时返回模拟数据
            return {
                "active_connections": 5,
                "max_connections": 20,
                "connection_pool_usage": 25.0,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"收集数据库连接指标失败: {e}")
            return {}

    async def collect_table_size_metrics(self) -> Dict[str, Any]:
        """
        收集数据库表大小指标

        Returns:
            Dict[str, Any]: 各表的大小信息
        """
        if not self.enabled:
            return {}

        try:
            # 这里应该查询实际的数据库表大小
            # 暂时返回模拟数据
            return {
                "total_size_mb": 1024.5,
                "table_sizes": {
                    "matches": 512.2,
                    "teams": 256.1,
                    "odds": 256.2,
                },
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"收集表大小指标失败: {e}")
            return {}

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """
        收集所有数据库指标

        Returns:
            Dict[str, Any]: 所有数据库指标的汇总
        """
        if not self.enabled:
            return {}

        connection_metrics = await self.collect_connection_metrics()
        table_metrics = await self.collect_table_size_metrics()

        return {
            "database_metrics": {
                **connection_metrics,
                **table_metrics,
                "collection_time": datetime.now().isoformat(),
            }
        }


class ApplicationMetricsCollector(MetricsCollector):
    """
    应用指标收集器

    收集应用程序特定的指标，如请求数、错误率、业务指标等
    """

    def __init__(self):
        """初始化应用指标收集器"""
        super().__init__(collection_interval=30)
        self.logger = logging.getLogger(__name__ + ".ApplicationMetricsCollector")

    def enable(self) -> None:
        """启用收集器"""
        self.enabled = True
        self.logger.info("应用指标收集器已启用")

    def disable(self) -> None:
        """禁用收集器"""
        self.enabled = False
        self.logger.info("应用指标收集器已禁用")

    async def collect_request_metrics(self) -> Dict[str, Any]:
        """
        收集请求指标

        Returns:
            Dict[str, Any]: HTTP请求相关指标
        """
        if not self.enabled:
            return {}

        try:
            # 这里应该从实际的请求监控系统获取数据
            # 暂时返回模拟数据
            return {
                "total_requests": 1500,
                "successful_requests": 1450,
                "failed_requests": 50,
                "average_response_time_ms": 125.5,
                "error_rate_percent": 3.33,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"收集请求指标失败: {e}")
            return {}

    async def collect_business_metrics(self) -> Dict[str, Any]:
        """
        收集业务指标

        Returns:
            Dict[str, Any]: 业务相关指标
        """
        if not self.enabled:
            return {}

        try:
            # 这里应该从业务数据库获取实际指标
            # 暂时返回模拟数据
            return {
                "total_predictions": 2500,
                "successful_predictions": 2350,
                "prediction_accuracy": 94.0,
                "active_users": 150,
                "timestamp": datetime.now().isoformat(),
            }
        except Exception as e:
            self.logger.error(f"收集业务指标失败: {e}")
            return {}

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """
        收集所有应用指标

        Returns:
            Dict[str, Any]: 所有应用指标的汇总
        """
        if not self.enabled:
            return {}

        request_metrics = await self.collect_request_metrics()
        business_metrics = await self.collect_business_metrics()

        return {
            "application_metrics": {
                **request_metrics,
                **business_metrics,
                "collection_time": datetime.now().isoformat(),
            }
        }


if __name__ == "__main__":
    """
    独立运行指标收集器
    """

    async def main():
        collector = MetricsCollector(collection_interval=10)  # 10秒间隔用于测试

        try:
            await collector.start()
            # 保持运行直到被中断
            while collector.running:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            logger.info("接收到中断信号")
        finally:
            await collector.stop()

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    asyncio.run(main())
