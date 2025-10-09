"""
系统监控器主模块
"""



logger = logging.getLogger(__name__)


class SystemMonitor:
    """
    系统监控器

    提供全面的系统性能和健康状态监控
    """

    def __init__(self, registry=None):
        """
        初始化系统监控器

        Args:
            registry: Prometheus注册表实例（已弃用，使用get_prometheus_metrics）
        """
        self.start_time = time.time()

        # 初始化组件
        self.metrics = get_prometheus_metrics()
        self.collector_manager = MetricsCollectorManager(self.start_time)
        self.health_checker = HealthChecker()

        # 监控状态
        self.is_monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

        self.logger = logging.getLogger(__name__)

    async def start_monitoring(self, interval: int = 30):
        """
        启动系统监控

        Args:
            interval: 监控数据收集间隔（秒）
        """
        if self.is_monitoring:
            self.logger.warning("系统监控已经在运行中")
            return

        self.is_monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop(interval))
        self.logger.info(f"系统监控已启动，监控间隔: {interval}秒")

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
        self.logger.info("系统监控已停止")

    async def _monitoring_loop(self, interval: int):
        """监控循环"""
        while self.is_monitoring:
            try:
                # 收集所有指标
                await self.collector_manager.collect_all()

                # 等待下一次收集
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"监控数据收集失败: {e}")
                await asyncio.sleep(interval)

    async def collect_metrics(self) -> Dict[str, Any]:
        """
        手动收集所有指标

        Returns:
            Dict[str, Any]: 收集的指标数据
        """
        return await self.collector_manager.collect_all()

    async def get_health_status(self) -> Dict[str, Any]:
        """
        获取系统健康状态

        Returns:
            Dict[str, Any]: 健康状态报告
        """
        health_status = await self.health_checker.check_all()
        health_status["uptime_seconds"] = time.time() - self.start_time
        health_status["version"] = "1.0.0"
        return health_status

    # 便捷方法 - 委托给指标管理器
    def record_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ):
        """
        记录HTTP请求

        Args:
            method: HTTP方法
            endpoint: 端点路径
            status_code: 状态码
            duration: 请求耗时
        """
        self.metrics.app_requests_total.labels(
            method=method, endpoint=endpoint, status_code=status_code
        ).inc()
        self.metrics.app_request_duration_seconds.labels(
            method=method, endpoint=endpoint
        ).observe(duration)

    def record_database_query(
        self, operation: str, table: str, duration: float, is_slow: bool = False
    ):
        """
        记录数据库查询

        Args:
            operation: 操作类型
            table: 表名
            duration: 查询耗时
            is_slow: 是否为慢查询
        """
        self.metrics.db_query_duration_seconds.labels(operation=operation, table=table).observe(
            duration
        )

        if is_slow:
            self.metrics.db_slow_queries_total.labels(operation=operation, table=table).inc()

    def record_cache_operation(self, operation: str, cache_type: str, result: str):
        """
        记录缓存操作

        Args:
            operation: 操作类型
            cache_type: 缓存类型
            result: 操作结果
        """
        self.metrics.cache_operations_total.labels(
            operation=operation, cache_type=cache_type, result=result
        ).inc()

    def record_prediction(self, model_version: str, league: str):
        """
        记录预测操作

        Args:
            model_version: 模型版本
            league: 联赛
        """
        self.metrics.business_predictions_total.labels(
            model_version=model_version, league=league
        ).inc()

    def record_model_inference(
        self, model_name: str, model_version: str, duration: float
    ):
        """
        记录模型推理

        Args:
            model_name: 模型名称
            model_version: 模型版本
            duration: 推理耗时
        """
        self.metrics.ml_model_inference_duration_seconds.labels(
            model_name=model_name, model_version=model_version
        ).observe(duration)

    def add_metrics_collector(self, name: str, collector):
        """
        添加自定义指标收集器

        Args:
            name: 收集器名称
            collector: 收集器实例
        """
        self.collector_manager.add_collector(name, collector)

    def add_health_checker(self, name: str, checker):
        """
        添加自定义健康检查器

        Args:
            name: 检查器名称
            checker: 检查器实例
        """
        self.health_checker.add_checker(name, checker)

    def get_monitoring_status(self) -> Dict[str, Any]:
        """
        获取监控状态

        Returns:
            Dict[str, Any]: 监控状态信息
        """
        return {
            "is_monitoring": self.is_monitoring,
            "uptime_seconds": time.time() - self.start_time,
            "start_time": self.start_time,
            "collectors": list(self.collector_manager.collectors.keys()),
            "health_checkers": self.health_checker.get_checkers(),
        }
from typing import Optional
import asyncio
import logging
import time

from .collectors import MetricsCollectorManager
from .health_checks import HealthChecker
from .metrics import get_prometheus_metrics

