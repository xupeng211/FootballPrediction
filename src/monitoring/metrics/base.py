"""
基础指标收集器
Base Metrics Collector

定义指标收集器的基类和通用功能。
"""




logger = logging.getLogger(__name__)

_settings = get_settings()

# 默认监控的表
DEFAULT_TABLES: List[str] = (
    list(_settings.metrics_tables)
    if getattr(_settings, "metrics_tables", None)
    else [
        "matches",
        "teams",
        "leagues",
        "odds",
        "features",
        "raw_match_data",
        "raw_odds_data",
        "raw_scores_data",
        "data_collection_logs",
    ]
)


class BaseMetricsCollector(ABC):
    """
    基础指标收集器抽象类

    定义所有指标收集器的通用接口和行为。
    """

    def __init__(
        self,
        collection_interval: Optional[int] = None,
        tables_to_monitor: Optional[List[str]] = None,
    ):
        """
        初始化基础指标收集器

        Args:
            collection_interval: 收集间隔（秒）
            tables_to_monitor: 要监控的表列表
        """
        default_interval = getattr(_settings, "metrics_collection_interval", 30) or 30
        self.collection_interval = collection_interval or default_interval
        self.metrics_exporter = get_metrics_exporter()
        self.running = False
        self.enabled = True
        self._task: Optional[asyncio.Task] = None
        self.tables_to_monitor = list(tables_to_monitor or DEFAULT_TABLES)

        # 设置导出器的监控表
        if hasattr(self.metrics_exporter, "set_tables_to_monitor"):
            self.metrics_exporter.set_tables_to_monitor(self.tables_to_monitor)

    async def start(self) -> None:
        """启动指标收集器"""
        if self.running:
            logger.warning(f"{self.__class__.__name__}已在运行中")
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

        logger.info(f"{self.__class__.__name__}已启动，收集间隔: {self.collection_interval}秒")

    async def stop(self) -> None:
        """停止指标收集器"""
        if not self.running:
            logger.warning(f"{self.__class__.__name__}未运行")
            return

        self.running = False

        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                logger.info(f"{self.__class__.__name__}收集任务已被取消")

        logger.info(f"{self.__class__.__name__}已停止")

    def enable(self) -> None:
        """启用指标收集器"""
        self.enabled = True
        logger.info(f"{self.__class__.__name__}已启用")

    def disable(self) -> None:
        """禁用指标收集器"""
        self.enabled = False
        logger.info(f"{self.__class__.__name__}已禁用")

    def set_collection_interval(self, interval: float) -> None:
        """设置收集间隔"""
        self.collection_interval = int(interval)
        logger.info(f"收集间隔已设置为 {interval} 秒")

    def _signal_handler(self, signum: int, frame) -> None:
        """
        信号处理器，用于优雅关闭
        """
        logger.info(f"接收到信号 {signum}，准备停止{self.__class__.__name__}")
        asyncio.create_task(self.stop())

    async def _collection_loop(self) -> None:
        """指标收集主循环"""
        logger.info(f"开始{self.__class__.__name__}指标收集循环")

        while self.running:
            try:
                collection_start = datetime.now()

                # 执行具体的指标收集
                await self.collect_all_metrics()

                collection_duration = (datetime.now() - collection_start).total_seconds()
                logger.debug(f"{self.__class__.__name__}指标收集完成，耗时: {collection_duration:.2f}秒")

                # 等待下一次收集
                await asyncio.sleep(self.collection_interval)

            except asyncio.CancelledError:
                logger.info(f"{self.__class__.__name__}指标收集循环被取消")
                break
            except Exception as e:
                logger.error(f"{self.__class__.__name__}指标收集过程中发生错误: {e}", exc_info=True)
                # 出错后等待一段时间再继续
                await asyncio.sleep(min(self.collection_interval, 60))

    @abstractmethod
    async def collect_all_metrics(self) -> Dict[str, Any]:
        """
        收集所有指标（抽象方法）

        Returns:
            Dict[str, Any]: 收集到的指标数据
        """
        pass

    async def collect_once(self) -> Dict[str, Any]:
        """
        执行一次指标收集

        Returns:
            Dict[str, Any]: 收集结果统计
        """
        try:
            start_time = datetime.now()

            metrics = await self.collect_all_metrics()

            duration = (datetime.now() - start_time).total_seconds()

            result = {
                "success": True,
                "collection_time": start_time.isoformat(),
                "duration_seconds": duration,
                "metrics": metrics,
                "message": "指标收集成功",
            }

            logger.info(f"{self.__class__.__name__}手动指标收集完成，耗时: {duration:.2f}秒")
            return result

        except Exception as e:
            logger.error(f"{self.__class__.__name__}手动指标收集失败: {e}", exc_info=True)
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
            "enabled": self.enabled,
            "collection_interval": self.collection_interval,
            "task_status": "running" if self._task and not self._task.done() else "stopped",
            "collector_type": self.__class__.__name__,
            "tables_to_monitor": self.tables_to_monitor,
        }
from datetime import datetime
from typing import Optional
import asyncio

import signal

from ...monitoring.metrics_exporter import get_metrics_exporter

