"""
系统监控核心
System Monitor Core

系统监控的主要业务逻辑。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from prometheus_client import CollectorRegistry

from .system_metrics import SystemMetricsCollector
from .health_checker import HealthChecker, HealthStatus

logger = logging.getLogger(__name__)


class SystemMonitor:
    """系统监控器"""

    def __init__(self, registry: Optional[CollectorRegistry] = None) -> None:
        """初始化系统监控器"""
        self.registry = registry or CollectorRegistry()
        self.metrics_collector = SystemMetricsCollector(self.registry)
        self.health_checker = HealthChecker()
        self.monitoring = False
        self.monitor_task: Optional[asyncio.Task] = None

        # 监控回调
        self.metrics_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self.health_callbacks: List[Callable[[Dict[str, Any]], None]] = []

        # 存储最新的指标和健康状态
        self.last_metrics: Dict[str, Any] = {}
        self.last_health: Dict[str, Any] = {}

    def _initialize_metrics(self) -> None:
        """初始化自定义指标"""
        # 应用程序指标
        self.request_count = self.metrics_collector._create_counter(
            "http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )

        self.request_duration = self.metrics_collector._create_histogram(
            "http_request_duration_seconds",
            "HTTP request duration",
            ["method", "endpoint"],
        )

        self.database_queries = self.metrics_collector._create_counter(
            "database_queries_total", "Total database queries", ["operation", "table"]
        )

        self.cache_operations = self.metrics_collector._create_counter(
            "cache_operations_total",
            "Total cache operations",
            ["operation", "cache_type", "result"],
        )

        self.predictions_made = self.metrics_collector._create_counter(
            "predictions_made_total",
            "Total predictions made",
            ["model_version", "league"],
        )

        self.model_inference_duration = self.metrics_collector._create_histogram(
            "model_inference_duration_seconds", "Model inference duration", ["model"]
        )

    async def start_monitoring(self, interval: int = 30) -> None:
        """开始监控"""
        if self.monitoring:
            logger.warning("Monitoring already started")
            return

        self.monitoring = True
        self.monitor_task = asyncio.create_task(self._monitoring_loop(interval))
        logger.info(f"Started system monitoring with {interval}s interval")

    async def stop_monitoring(self) -> None:
        """停止监控"""
        if not self.monitoring:
            return

        self.monitoring = False
        if self.monitor_task:
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("Stopped system monitoring")

    async def _monitoring_loop(self, interval: int) -> None:
        """监控循环"""
        while self.monitoring:
            try:
                # 收集指标
                await self._collect_all_metrics()

                # 执行健康检查
                await self._run_health_checks()

                # 等待下次监控
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                logger.info("Monitoring loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {str(e)}")
                await asyncio.sleep(5)  # 出错后等待5秒再继续

    async def _collect_all_metrics(self) -> None:
        """收集所有指标"""
        metrics = {"timestamp": datetime.utcnow().isoformat()}

        # 收集系统指标
        system_metrics = await self.metrics_collector.collect_system_metrics()
        metrics["system"] = system_metrics

        # 收集数据库指标
        db_metrics = await self.metrics_collector.collect_database_metrics()
        metrics["database"] = db_metrics

        # 收集缓存指标
        cache_metrics = await self.metrics_collector.collect_cache_metrics()
        metrics["cache"] = cache_metrics

        # 收集应用程序指标
        app_metrics = await self.metrics_collector.collect_application_metrics()
        metrics["application"] = app_metrics

        # 更新最新指标
        self.last_metrics = metrics

        # 调用回调
        for callback in self.metrics_callbacks:
            try:
                callback(metrics)
            except Exception as e:
                logger.error(f"Error in metrics callback: {str(e)}")

    async def _run_health_checks(self) -> None:
        """运行健康检查"""
        health_status = {
            "overall": HealthStatus.HEALTHY,
            "timestamp": datetime.utcnow().isoformat(),
            "components": {},
        }

        # 检查各个组件
        checks = [
            ("database", self.health_checker.check_database),
            ("redis", self.health_checker.check_redis),
            ("system", self.health_checker.check_system_resources),
            ("application", self.health_checker.check_application_health),
        ]

        for component_name, check_func in checks:
            try:
                component_health = await check_func()
                health_status["components"][component_name] = component_health

                # 确定整体健康状态
                if component_health["status"] == HealthStatus.UNHEALTHY:
                    health_status["overall"] = HealthStatus.UNHEALTHY
                elif (
                    component_health["status"] == HealthStatus.DEGRADED
                    and health_status["overall"] == HealthStatus.HEALTHY
                ):
                    health_status["overall"] = HealthStatus.DEGRADED

            except Exception as e:
                logger.error(f"Health check failed for {component_name}: {str(e)}")
                health_status["components"][component_name] = {
                    "status": HealthStatus.UNHEALTHY,
                    "error": str(e),
                }
                health_status["overall"] = HealthStatus.UNHEALTHY

        # 更新最新健康状态
        self.last_health = health_status

        # 调用回调
        for callback in self.health_callbacks:
            try:
                callback(health_status)
            except Exception as e:
                logger.error(f"Error in health callback: {str(e)}")

    def add_metrics_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """添加指标收集回调"""
        self.metrics_callbacks.append(callback)

    def add_health_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """添加健康检查回调"""
        self.health_callbacks.append(callback)

    def record_request(
        self, method: str, endpoint: str, status_code: int, duration: float
    ) -> None:
        """记录HTTP请求"""
        if hasattr(self, "request_count"):
            self.request_count.labels(
                method=method, endpoint=endpoint, status=str(status_code)
            ).inc()

        if hasattr(self, "request_duration"):
            self.request_duration.labels(method=method, endpoint=endpoint).observe(
                duration
            )

    def record_database_query(
        self, operation: str, table: str, duration: float, is_slow: bool = False
    ) -> None:
        """记录数据库查询"""
        if hasattr(self, "database_queries"):
            self.database_queries.labels(operation=operation, table=table).inc()

    def record_cache_operation(
        self, operation: str, cache_type: str, result: str
    ) -> None:
        """记录缓存操作"""
        self.metrics_collector.record_cache_operation(operation, cache_type, result)

    def record_prediction(self, model_version: str, league: str) -> None:
        """记录预测"""
        if hasattr(self, "predictions_made"):
            self.predictions_made.labels(
                model_version=model_version, league=league
            ).inc()

    def record_model_inference(self, model_name: str, duration: float) -> None:
        """记录模型推理"""
        if hasattr(self, "model_inference_duration"):
            self.model_inference_duration.labels(model=model_name).observe(duration)

    def get_health_status(self) -> Dict[str, Any]:
        """获取健康状态"""
        return (
            self.last_health.copy()
            if self.last_health
            else {
                "overall": HealthStatus.HEALTHY,
                "timestamp": datetime.utcnow().isoformat(),
                "components": {},
            }
        )

    def get_metrics(self) -> Dict[str, Any]:
        """获取最新指标"""
        return self.last_metrics.copy() if self.last_metrics else {}

    def set_database_manager(self, db_manager) -> None:
        """设置数据库管理器"""
        self.metrics_collector.set_database_manager(db_manager)
        self.health_checker.set_database_manager(db_manager)

    def set_redis_manager(self, redis_manager) -> None:
        """设置Redis管理器"""
        self.metrics_collector.set_redis_manager(redis_manager)
        self.health_checker.set_redis_manager(redis_manager)


# 全局实例
_system_monitor: Optional[SystemMonitor] = None


def get_system_monitor() -> SystemMonitor:
    """获取全局系统监控器实例"""
    global _system_monitor
    if _system_monitor is None:
        _system_monitor = SystemMonitor()
    return _system_monitor


# 便捷函数
def record_http_request(
    method: str, endpoint: str, status_code: int, duration: float
) -> None:
    """记录HTTP请求"""
    monitor = get_system_monitor()
    monitor.record_request(method, endpoint, status_code, duration)


def record_db_query(
    operation: str, table: str, duration: float, is_slow: bool = False
) -> None:
    """记录数据库查询"""
    monitor = get_system_monitor()
    monitor.record_database_query(operation, table, duration, is_slow)


def record_cache_op(operation: str, cache_type: str, result: str) -> None:
    """记录缓存操作"""
    monitor = get_system_monitor()
    monitor.record_cache_operation(operation, cache_type, result)


def record_prediction(model_version: str, league: str) -> None:
    """记录预测"""
    monitor = get_system_monitor()
    monitor.record_prediction(model_version, league)
