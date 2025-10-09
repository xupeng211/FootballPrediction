"""
数据库监控收集器

收集数据库连接和查询性能指标。
"""

import logging
import time
from typing import Dict, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from src.database.connection import get_async_session
from ..metrics.system_metrics import SystemMetrics

logger = logging.getLogger(__name__)


class DatabaseCollector:
    """数据库监控收集器"""

    def __init__(self, metrics: SystemMetrics):
        """
        初始化数据库收集器

        Args:
            metrics: 系统指标实例
        """
        self.metrics = metrics
        self.query_times: Dict[str, list] = {}

    async def collect(self) -> Dict[str, any]:
        """
        收集数据库指标

        Returns:
            收集到的指标值
        """
        try:
            metrics_data = {}

            # 获取数据库连接信息
            connection_info = await self._get_connection_info()
            metrics_data.update(connection_info)

            # 更新连接指标
            if connection_info:
                self.metrics.db_connections_active.set(
                    connection_info.get("active_connections", 0)
                )
                self.metrics.db_connections_total.set(
                    connection_info.get("total_connections", 0)
                )

            logger.debug(f"数据库指标收集完成: {metrics_data}")
            return metrics_data

        except Exception as e:
            logger.error(f"收集数据库指标失败: {e}")
            return {}

    async def _get_connection_info(self) -> Dict[str, int]:
        """
        获取数据库连接信息

        Returns:
            连接信息字典
        """
        try:
            async with get_async_session() as session:
                # PostgreSQL查询
                result = await session.execute(text("""
                    SELECT
                        count(*) as total_connections,
                        count(*) FILTER (WHERE state = 'active') as active_connections
                    FROM pg_stat_activity
                """))

                row = result.fetchone()
                if row:
                    return {
                        "total_connections": row.total_connections,
                        "active_connections": row.active_connections,
                    }

        except SQLAlchemyError as e:
            logger.debug(f"无法获取PostgreSQL连接信息: {e}")

            # 尝试SQLite查询
            try:
                async with get_async_session() as session:
                    result = await session.execute(text("PRAGMA compile_options"))
                    # SQLite是单连接数据库
                    return {
                        "total_connections": 1,
                        "active_connections": 1,
                    }
            except Exception as e2:
                logger.debug(f"无法获取SQLite连接信息: {e2}")

        return {}

    def record_query(self, operation: str, table: str, duration: float, is_slow: bool = False):
        """
        记录数据库查询指标

        Args:
            operation: 操作类型
            table: 表名
            duration: 查询持续时间
            is_slow: 是否是慢查询
        """
        # 记录查询持续时间
        self.metrics.db_query_duration_seconds.labels(
            operation=operation, table=table
        ).observe(duration)

        # 记录慢查询
        if is_slow:
            self.metrics.db_slow_queries_total.labels(
                operation=operation, table=table
            ).inc()

        # 保存查询时间用于统计
        key = f"{operation}.{table}"
        if key not in self.query_times:
            self.query_times[key] = []
        self.query_times[key].append(duration)

        # 只保留最近100次的查询时间
        if len(self.query_times[key]) > 100:
            self.query_times[key] = self.query_times[key][-100:]

    def get_query_stats(self) -> Dict[str, Dict[str, float]]:
        """
        获取查询统计信息

        Returns:
            查询统计字典
        """
        stats = {}
        for key, times in self.query_times.items():
            if times:
                stats[key] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "last_time": times[-1],
                }
        return stats

    async def test_connection(self) -> bool:
        """
        测试数据库连接

        Returns:
            连接是否正常
        """
        try:
            start_time = time.time()
            async with get_async_session() as session:
                await session.execute(text("SELECT 1"))
            duration = time.time() - start_time

            # 记录连接测试查询
            self.record_query("test", "connection", duration)
            return True

        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False