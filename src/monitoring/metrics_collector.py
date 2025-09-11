"""
监控指标收集器

定期收集和更新各种监控指标，包括系统状态、数据库指标等。
"""

import asyncio
import logging
import signal
from datetime import datetime
from typing import Any, Dict, Optional

from .metrics_exporter import get_metrics_exporter

logger = logging.getLogger(__name__)


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
    collector = get_metrics_collector()
    await collector.start()


async def stop_metrics_collection() -> None:
    """
    停止监控指标收集
    """
    collector = get_metrics_collector()
    await collector.stop()


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
