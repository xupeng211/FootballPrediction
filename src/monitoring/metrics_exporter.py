"""
监控指标导出器

导出足球预测平台的各项监控指标，供 Prometheus 采集。
包括数据采集成功/失败次数、数据清洗成功/失败次数、调度任务延迟时间、数据表行数统计等。
"""

import logging
import time
from datetime import datetime
from typing import Optional, Tuple

from prometheus_client import (CONTENT_TYPE_LATEST, REGISTRY,
                               CollectorRegistry, Counter, Gauge, Histogram,
                               Info, generate_latest)
from sqlalchemy import text

from ..database.connection import get_async_session

logger = logging.getLogger(__name__)


class MetricsExporter:
    """
    监控指标导出器

    提供 Prometheus 格式的监控指标，包括：
    - 数据采集成功/失败次数
    - 数据清洗成功/失败次数
    - 调度任务延迟时间
    - 数据表行数统计
    - 系统健康状态
    """

    def __init__(self, registry: Optional[CollectorRegistry] = None):
        """
        初始化指标导出器

        Args:
            registry: Prometheus 注册表，默认使用全局注册表
        """
        self.registry = registry or REGISTRY

        # 数据采集指标
        self.data_collection_total = Counter(
            "football_data_collection_total",
            "数据采集总次数",
            ["data_source", "collection_type"],
            registry=self.registry,
        )

        self.data_collection_errors = Counter(
            "football_data_collection_errors_total",
            "数据采集错误总数",
            ["data_source", "collection_type", "error_type"],
            registry=self.registry,
        )

        self.data_collection_duration = Histogram(
            "football_data_collection_duration_seconds",
            "数据采集耗时（秒）",
            ["data_source", "collection_type"],
            buckets=(0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0),
            registry=self.registry,
        )

        # 数据清洗指标
        self.data_cleaning_total = Counter(
            "football_data_cleaning_total",
            "数据清洗总次数",
            ["data_type"],
            registry=self.registry,
        )

        self.data_cleaning_errors = Counter(
            "football_data_cleaning_errors_total",
            "数据清洗错误总数",
            ["data_type", "error_type"],
            registry=self.registry,
        )

        self.data_cleaning_duration = Histogram(
            "football_data_cleaning_duration_seconds",
            "数据清洗耗时（秒）",
            ["data_type"],
            registry=self.registry,
        )

        # 调度器指标
        self.scheduler_task_delay = Gauge(
            "football_scheduler_task_delay_seconds",
            "调度任务延迟时间（秒）",
            ["task_name"],
            registry=self.registry,
        )

        self.scheduler_task_failures = Counter(
            "football_scheduler_task_failures_total",
            "调度任务失败总数",
            ["task_name", "failure_reason"],
            registry=self.registry,
        )

        self.scheduler_task_duration = Histogram(
            "football_scheduler_task_duration_seconds",
            "调度任务执行时间（秒）",
            ["task_name"],
            registry=self.registry,
        )

        # 数据库表行数指标
        self.table_row_count = Gauge(
            "football_table_row_count",
            "数据表行数统计",
            ["table_name"],
            registry=self.registry,
        )

        # 数据库性能指标
        self.database_connections = Gauge(
            "football_database_connections",
            "数据库连接数",
            ["connection_state"],
            registry=self.registry,
        )

        self.database_query_duration = Histogram(
            "football_database_query_duration_seconds",
            "数据库查询耗时（秒）",
            ["query_type"],
            registry=self.registry,
        )

        # 系统健康指标
        self.system_info = Info("football_system_info", "系统信息", registry=self.registry)

        self.last_update_timestamp = Gauge(
            "football_metrics_last_update_timestamp",
            "指标最后更新时间戳",
            registry=self.registry,
        )

        # 设置系统信息
        self.system_info.info(
            {
                "version": "1.0.0",
                "component": "football_prediction_platform",
                "environment": "production",
            }
        )

    def record_data_collection(
        self,
        data_source: str,
        collection_type: str,
        success: bool,
        duration: float,
        error_type: Optional[str] = None,
        records_count: int = 0,
    ) -> None:
        """
        记录数据采集指标

        Args:
            data_source: 数据源名称
            collection_type: 采集类型（fixtures/odds/scores）
            success: 是否成功
            duration: 采集耗时（秒）
            error_type: 错误类型（如果失败）
            records_count: 采集记录数
        """
        # 增加采集总数
        self.data_collection_total.labels(
            data_source=data_source, collection_type=collection_type
        ).inc(records_count if records_count > 0 else 1)

        # 记录采集耗时
        self.data_collection_duration.labels(
            data_source=data_source, collection_type=collection_type
        ).observe(duration)

        # 记录错误（如果失败）
        if not success and error_type:
            self.data_collection_errors.labels(
                data_source=data_source,
                collection_type=collection_type,
                error_type=error_type,
            ).inc()

    def record_data_cleaning(
        self,
        data_type: str,
        success: bool,
        duration: float,
        error_type: Optional[str] = None,
        records_processed: int = 1,
    ) -> None:
        """
        记录数据清洗指标

        Args:
            data_type: 数据类型（match/odds/scores）
            success: 是否成功
            duration: 清洗耗时（秒）
            error_type: 错误类型（如果失败）
            records_processed: 处理记录数
        """
        # 增加清洗总数
        self.data_cleaning_total.labels(data_type=data_type).inc(records_processed)

        # 记录清洗耗时
        self.data_cleaning_duration.labels(data_type=data_type).observe(duration)

        # 记录错误（如果失败）
        if not success and error_type:
            self.data_cleaning_errors.labels(
                data_type=data_type, error_type=error_type
            ).inc()

    def record_scheduler_task(
        self,
        task_name: str,
        scheduled_time: datetime,
        actual_start_time: datetime,
        duration: float,
        success: bool,
        failure_reason: Optional[str] = None,
    ) -> None:
        """
        记录调度任务指标

        Args:
            task_name: 任务名称
            scheduled_time: 计划执行时间
            actual_start_time: 实际开始时间
            duration: 执行耗时（秒）
            success: 是否成功
            failure_reason: 失败原因（如果失败）
        """
        # 计算延迟时间
        delay_seconds = (actual_start_time - scheduled_time).total_seconds()
        self.scheduler_task_delay.labels(task_name=task_name).set(delay_seconds)

        # 记录执行耗时
        self.scheduler_task_duration.labels(task_name=task_name).observe(duration)

        # 记录失败（如果失败）
        if not success and failure_reason:
            self.scheduler_task_failures.labels(
                task_name=task_name, failure_reason=failure_reason
            ).inc()

    async def update_table_row_counts(self) -> None:
        """
        更新数据表行数统计
        """
        try:
            async for session in get_async_session():
                # 获取各表行数
                tables_to_monitor = [
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

                for table_name in tables_to_monitor:
                    try:
                        result = await session.execute(
                            text(f"SELECT COUNT(*) FROM {table_name}")
                        )
                        row_count = result.scalar()
                        self.table_row_count.labels(table_name=table_name).set(
                            row_count
                        )

                    except Exception as e:
                        logger.error(f"获取表 {table_name} 行数失败: {e}")
                        continue

                break  # 只使用第一个会话

        except Exception as e:
            logger.error(f"更新表行数统计失败: {e}")

    async def update_database_metrics(self) -> None:
        """
        更新数据库性能指标
        """
        try:
            async for session in get_async_session():
                # 获取数据库连接数
                result = await session.execute(
                    text(
                        """
                        SELECT state, COUNT(*)
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                        GROUP BY state
                    """
                    )
                )

                for state, count in result.fetchall():
                    if state:
                        self.database_connections.labels(connection_state=state).set(
                            count
                        )

                break  # 只使用第一个会话

        except Exception as e:
            logger.error(f"更新数据库指标失败: {e}")

    async def collect_all_metrics(self) -> None:
        """
        收集所有监控指标
        """
        start_time = time.time()

        try:
            # 更新表行数统计
            await self.update_table_row_counts()

            # 更新数据库指标
            await self.update_database_metrics()

            # 更新最后更新时间戳
            self.last_update_timestamp.set(time.time())

            logger.info("监控指标收集完成")

        except Exception as e:
            logger.error(f"收集监控指标失败: {e}")

        duration = time.time() - start_time
        logger.debug(f"指标收集耗时: {duration:.2f}秒")

    def get_metrics(self) -> Tuple[str, str]:
        """
        获取 Prometheus 格式的指标数据

        Returns:
            Tuple[str, str]: (content_type, metrics_data)
        """
        metrics_data = generate_latest(self.registry)
        return CONTENT_TYPE_LATEST, metrics_data


# 全局指标导出器实例
metrics_exporter = MetricsExporter()


def get_metrics_exporter() -> MetricsExporter:
    """
    获取全局指标导出器实例

    Returns:
        MetricsExporter: 指标导出器实例
    """
    return metrics_exporter
