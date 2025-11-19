"""任务监控模块.

提供任务调度系统的监控功能,包括:
- 任务执行状态监控
- 性能指标收集
- Prometheus 指标导出
- 错误率统计
"""

import logging
from datetime import datetime
from typing import Any, cast, Optional

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Gauge, Histogram
from sqlalchemy import text

from src.database.connection import DatabaseManager
from src.database.sql_compatibility import (
    CompatibleQueryBuilder,
    get_db_type_from_engine,
)

logger = logging.getLogger(__name__)


class TaskMonitor:
    """类文档字符串."""

    pass  # 添加pass语句
    """
    任务监控器

    支持使用自定义的 CollectorRegistry,避免测试环境中的全局状态污染.
    在生产环境中使用默认的全局注册表,在测试环境中可以传入独立的注册表.
    """

    def __init__(self, registry: CollectorRegistry | None = None):
        """函数文档字符串."""
        pass
        # 添加pass语句
        """
        初始化任务监控器

        Args:
            registry: 可选的 Prometheus 注册表实例,主要用于测试隔离
        """
        self._db_type: str | None = None
        self._query_builder: CompatibleQueryBuilder | None = None

        # 使用传入的注册表或默认全局注册表
        self.registry = registry or REGISTRY

        # 在函数内部初始化 Prometheus 指标,使用指定的注册表
        # 避免模块全局初始化导致的测试冲突
        self.task_counter = self._create_counter(
            "football_tasks_total",
            "Total number of tasks executed",
            ["task_name", "status"],
        )

        self.task_duration = self._create_histogram(
            "football_task_duration_seconds",
            "Task execution duration in seconds",
            ["task_name"],
        )

        self.task_error_rate = self._create_gauge(
            "football_task_error_rate",
            "Task error rate in the last hour",
            ["task_name"],
        )

        self.active_tasks = self._create_gauge(
            "football_active_tasks", "Number of currently active tasks", ["task_name"]
        )

        self.queue_size = self._create_gauge(
            "football_queue_size", "Number of tasks in queue", ["queue_name"]
        )

        self.retry_counter = self._create_counter(
            "football_task_retries_total",
            "Total number of task retries",
            ["task_name", "retry_count"],
        )

    def _create_counter(self, name: str, description: str, labels: list) -> Counter:
        """创建 Counter 指标,避免重复注册.

        在测试环境中使用独立的注册表可以避免指标重复注册问题.
        """
        try:
            return Counter(name, description, labels, registry=self.registry)
        except ValueError:
            # 如果指标已存在,尝试从注册表获取
            for collector in self.registry._collector_to_names:
                if hasattr(collector, "_name") and collector._name == name:
                    return cast(Counter, collector)
            # 返回 mock 对象用于测试
            from unittest.mock import Mock

            mock_counter = Mock()
            mock_counter.inc = Mock()
            mock_counter.labels = Mock(return_value=mock_counter)
            return cast(Counter, mock_counter)

    def _create_histogram(self, name: str, description: str, labels: list) -> Histogram:
        """创建 Histogram 指标,避免重复注册."""
        try:
            return Histogram(name, description, labels, registry=self.registry)
        except ValueError:
            from unittest.mock import Mock

            mock_histogram = Mock()
            mock_histogram.observe = Mock()
            mock_histogram.labels = Mock(return_value=mock_histogram)
            return mock_histogram

    def _create_gauge(self, name: str, description: str, labels: list) -> Gauge:
        """创建 Gauge 指标,避免重复注册."""
        try:
            return Gauge(name, description, labels, registry=self.registry)
        except ValueError:
            from unittest.mock import Mock

            mock_gauge = Mock()
            mock_gauge.set = Mock()
            mock_gauge.inc = Mock()
            mock_gauge.dec = Mock()
            mock_gauge.labels = Mock(return_value=mock_gauge)
            return mock_gauge

    def record_task_start(self, task_name: str, task_id: str) -> None:
        """记录任务开始."""
        self.active_tasks.labels(task_name=task_name).inc()
        logger.info(f"任务开始: {task_name} (ID: {task_id})")

    def record_task_completion(
        self, task_name: str, task_id: str, duration: float, status: str = "success"
    ) -> None:
        """记录任务完成.

        Args:
            task_name: 任务名称
            task_id: 任务ID
            duration: 执行时长(秒)
            status: 任务状态 (success / failed)
        """
        # 更新指标
        self.task_counter.labels(task_name=task_name, status=status).inc()
        self.task_duration.labels(task_name=task_name).observe(duration)
        self.active_tasks.labels(task_name=task_name).dec()

        logger.info(
            f"任务完成: {task_name} (ID: {task_id}), 状态: {status}, 耗时: {duration:.2f}s"
        )

    def record_task_retry(self, task_name: str, retry_count: int) -> None:
        """记录任务重试."""
        self.retry_counter.labels(
            task_name=task_name, retry_count=str(retry_count)
        ).inc()
        logger.warning(f"任务重试: {task_name}, 第 {retry_count} 次重试")

    def update_queue_size(self, queue_name: str, size: int) -> None:
        """更新队列大小."""
        self.queue_size.labels(queue_name=queue_name).set(size)

    async def _get_db_type(self) -> str:
        """获取数据库类型."""
        if self._db_type is None:
            try:
                db_manager = DatabaseManager()
                engine = db_manager._async_engine or db_manager._sync_engine
                if engine:
                    self._db_type = get_db_type_from_engine(engine)
                else:
                    self._db_type = "postgresql"  # 默认值
            except (ValueError, KeyError, RuntimeError):
                self._db_type = "postgresql"  # 默认值
        return self._db_type

    async def _get_query_builder(self) -> CompatibleQueryBuilder:
        """获取兼容性查询构建器."""
        if self._query_builder is None:
            db_type = await self._get_db_type()
            self._query_builder = CompatibleQueryBuilder(db_type)
        return self._query_builder

    async def calculate_error_rates(self) -> dict[str, float]:
        """计算各任务的错误率.

        Returns:
            任务错误率字典
        """
        try:
            db_manager = DatabaseManager()
            error_rates = {}
            db_type = await self._get_db_type()

            async with db_manager.get_async_session() as session:
                # 查询最近1小时内的任务执行统计
                if db_type == "sqlite":
                    error_rate_query = text(
                        """
                        SELECT
                            task_name,
                            COUNT(*) as total_tasks,
                            SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as failed_tasks
                        FROM error_logs
                        WHERE created_at >= datetime('now', '-1 hour')
                        GROUP BY task_name
                    """
                    )
                else:
                    error_rate_query = text(
                        """
                        SELECT
                            task_name,
                            COUNT(*) as total_tasks,
                            SUM(CASE WHEN error_message IS NOT NULL THEN 1 ELSE 0 END) as failed_tasks
                        FROM error_logs
                        WHERE created_at >= NOW() - INTERVAL '1 hour'
                        GROUP BY task_name
                    """
                    )

                result = await session.execute(error_rate_query)

                for row in result:
                    task_name = row.task_name
                    total_tasks = row.total_tasks
                    failed_tasks = row.failed_tasks

                    error_rate = failed_tasks / total_tasks if total_tasks > 0 else 0.0
                    error_rates[task_name] = error_rate

                    # 更新Prometheus指标
                    self.task_error_rate.labels(task_name=task_name).set(error_rate)

                return error_rates

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"计算错误率失败: {str(e)}")
            return {}

    async def get_task_statistics(self, hours: int = 24) -> dict[str, Any]:
        """获取任务统计信息.

        Args:
            hours: 统计时间范围(小时)

        Returns:
            任务统计数据
        """
        try:
            db_manager = DatabaseManager()
            db_type = await self._get_db_type()

            async with db_manager.get_async_session() as session:
                # 统计查询
                if db_type == "sqlite":
                    stats_query = text(
                        """
                        SELECT
                            task_name,
                            COUNT(*) as total_executions,
                            COUNT(CASE WHEN error_message IS NULL THEN 1 END) as successful_executions,
                            COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed_executions,
                            AVG(CASE WHEN error_message IS NULL THEN 1.0 ELSE 0.0 END) as success_rate,
                            SUM(retry_count) as total_retries
                        FROM error_logs
                        WHERE created_at >= datetime('now', :hours_param || ' hours')
                        GROUP BY task_name
                        ORDER BY total_executions DESC
                    """
                    )
                    result = await session.execute(
                        stats_query, {"hours_param": f"-{hours}"}
                    )
                else:
                    stats_query = text(
                        """
                        SELECT
                            task_name,
                            COUNT(*) as total_executions,
                            COUNT(CASE WHEN error_message IS NULL THEN 1 END) as successful_executions,
                            COUNT(CASE WHEN error_message IS NOT NULL THEN 1 END) as failed_executions,
                            AVG(CASE WHEN error_message IS NULL THEN 1.0 ELSE 0.0 END) as success_rate,
                            SUM(retry_count) as total_retries
                        FROM error_logs
                        WHERE created_at >= NOW() - INTERVAL :hours || ' hours'
                        GROUP BY task_name
                        ORDER BY total_executions DESC
                    """
                    )
                    result = await session.execute(stats_query, {"hours": hours})

                statistics = []
                for row in result:
                    statistics.append(
                        {
                            "task_name": row.task_name,
                            "total_executions": row.total_executions,
                            "successful_executions": row.successful_executions,
                            "failed_executions": row.failed_executions,
                            "success_rate": float(row.success_rate),
                            "total_retries": row.total_retries,
                        }
                    )

                return {
                    "time_range_hours": hours,
                    "statistics": statistics,
                    "generated_at": datetime.now().isoformat(),
                }

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"获取任务统计失败: {str(e)}")
            return {"error": str(e), "statistics": []}

    async def check_task_health(self) -> dict[str, Any]:
        """检查任务系统健康状态.

        Returns:
            健康状态信息
        """
        health_status: dict[str, Any] = {
            "overall_status": "healthy",
            "issues": [],
            "metrics": {},
        }

        try:
            # 1. 检查错误率
            error_rates = await self.calculate_error_rates()
            high_error_tasks = [
                task
                for task, rate in error_rates.items()
                if rate > 0.1  # 10% 错误率阈值
            ]

            if high_error_tasks:
                health_status["overall_status"] = "warning"
                health_status["issues"].append(
                    {
                        "type": "high_error_rate",
                        "tasks": high_error_tasks,
                        "message": f"任务错误率过高: {high_error_tasks}",
                    }
                )

            health_status["metrics"]["error_rates"] = error_rates

            # 2. 检查队列积压
            queue_sizes = await self._get_queue_sizes()
            large_queues = [
                queue
                for queue, size in queue_sizes.items()
                if size > 100  # 100个任务积压阈值
            ]

            if large_queues:
                health_status["overall_status"] = "warning"
                health_status["issues"].append(
                    {
                        "type": "queue_backlog",
                        "queues": large_queues,
                        "message": f"队列积压严重: {large_queues}",
                    }
                )

            health_status["metrics"]["queue_sizes"] = queue_sizes

            # 3. 检查任务延迟
            task_delays = await self._check_task_delays()
            delayed_tasks = [
                task
                for task, delay in task_delays.items()
                if delay > 600  # 10分钟延迟阈值
            ]

            if delayed_tasks:
                health_status["overall_status"] = "unhealthy"
                health_status["issues"].append(
                    {
                        "type": "task_delays",
                        "tasks": delayed_tasks,
                        "message": f"任务执行延迟过高: {delayed_tasks}",
                    }
                )

            health_status["metrics"]["task_delays"] = task_delays

            return health_status

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.error(f"检查任务健康状态失败: {str(e)}")
            return {
                "overall_status": "unknown",
                "error": str(e),
                "issues": [{"type": "monitoring_error", "message": str(e)}],
            }

    async def _get_queue_sizes(self) -> dict[str, int]:
        """获取队列大小."""
        try:
            import os

            import redis

            redis_client = redis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379 / 0")
            )

            queue_names = ["fixtures", "odds", "scores", "maintenance", "default"]
            queue_sizes = {}

            for queue_name in queue_names:
                # Celery 队列在 Redis 中的键名格式
                queue_key = f"celery.{queue_name}"
                size = redis_client.llen(queue_key)
                queue_sizes[queue_name] = size

                # 更新Prometheus指标
                self.queue_size.labels(queue_name=queue_name).set(size)

            return queue_sizes

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.warning(f"获取队列大小失败: {str(e)}")
            return {}

    async def _check_task_delays(self) -> dict[str, float]:
        """检查任务延迟."""
        try:
            db_manager = DatabaseManager()
            task_delays = {}
            query_builder = await self._get_query_builder()

            async with db_manager.get_async_session() as session:
                # 查询运行时间过长的任务
                delay_query = text(query_builder.build_task_delay_query())
                result = await session.execute(delay_query)

                for row in result:
                    task_delays[row.task_name] = float(row.avg_delay_seconds)

                return task_delays

        except (RuntimeError, ValueError, ConnectionError) as e:
            logger.warning(f"检查任务延迟失败: {str(e)}")
            return {}

    def generate_monitoring_report(self) -> dict[str, Any]:
        """生成监控报告.

        Returns:
            监控报告数据
        """
        return {
            "report_generated_at": datetime.now().isoformat(),
            "monitoring_status": "active",
            "metrics_available": [
                "task_counter",
                "task_duration",
                "task_error_rate",
                "active_tasks",
                "queue_size",
                "retry_counter",
            ],
            "prometheus_endpoint": "/metrics",
            "health_check_endpoint": "/health / tasks",
        }
