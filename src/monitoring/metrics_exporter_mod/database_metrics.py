"""
数据库指标记录器 / Database Metrics Recorder

负责记录数据库相关的各项指标。
"""

import logging
import time
from typing import Optional, List, Dict

from sqlalchemy import text
from src.database import get_async_db_session as get_async_session  # type: ignore

logger = logging.getLogger(__name__)


class DatabaseMetrics:
    """数据库指标记录器

    负责记录数据库连接数、查询性能、表行数等指标。
    """

    def __init__(self, metrics_defs, tables_to_monitor: Optional[List[str]] = None):
        """
        初始化数据库指标记录器

        Args:
            metrics_defs: 指标定义实例
            tables_to_monitor: 需要监控的表列表
        """
        self.metrics = metrics_defs
        self.tables_to_monitor = tables_to_monitor or []

    async def update_table_row_counts(
        self, table_counts: Optional[Dict[str, int]] = None
    ) -> None:
        """
        更新数据表行数统计

        Args:
            table_counts: 表行数字典，格式为 {table_name: row_count}
                          如果为 None，则从数据库查询
        """
        if table_counts:
            # 测试模式：直接使用提供的数据
            for table_name, count in table_counts.items():
                try:
                    self.metrics.table_row_count.labels(table_name=table_name).set(
                        float(count)
                    )
                except (
                    SQLAlchemyError,
                    DatabaseError,
                    ConnectionError,
                    TimeoutError,
                ) as e:
                    logger.error(f"更新表 {table_name} 行数失败: {e}")
        else:
            # 生产模式：从数据库查询
            await self._query_table_row_counts()

    async def _query_table_row_counts(self) -> None:
        """从数据库查询表行数"""
        try:
            async with get_async_session() as session:
                if not self.tables_to_monitor:
                    logger.debug("未配置数据库表监控列表，跳过行数统计")
                    return

                for table_name in self.tables_to_monitor:
                    try:
                        # 验证表名的安全性
                        if not self._is_safe_table_name(table_name):
                            logger.warning(f"跳过可能不安全的表名: {table_name}")
                            continue

                        # 使用 quoted_name 确保表名安全
                        from sqlalchemy import quoted_name

                        safe_table_name = quoted_name(table_name, quote=True)

                        # 执行查询
                        result = await session.execute(
                            text(f"SELECT COUNT(*) FROM {safe_table_name}")  # nosec B608
                        )
                        row_count = result.scalar()

                        # 更新指标
                        self.metrics.table_row_count.labels(table_name=table_name).set(
                            float(row_count) if row_count is not None else 0.0
                        )

                    except (
                        SQLAlchemyError,
                        DatabaseError,
                        ConnectionError,
                        TimeoutError,
                    ) as e:
                        logger.error(f"获取表 {table_name} 行数失败: {e}")
                        continue

        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.error(f"查询表行数统计失败: {e}")

    def _is_safe_table_name(self, table_name: str) -> bool:
        """
        检查表名是否安全

        Args:
            table_name: 表名

        Returns:
            bool: 是否安全
        """
        # 只允许字母、数字和下划线
        return table_name.replace("_", "").isalnum()

    async def update_connection_metrics(self) -> None:
        """更新数据库连接数指标"""
        try:
            async with get_async_session() as session:
                # 查询数据库连接数
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
                        self.metrics.database_connections.labels(
                            connection_state=state
                        ).set(count)

        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.error(f"更新数据库连接指标失败: {e}")

    async def update_all_metrics(self) -> None:
        """更新所有数据库相关指标"""
        start_time = time.time()

        try:
            # 更新表行数
            await self.update_table_row_counts()

            # 更新连接数
            await self.update_connection_metrics()

            # 更新最后更新时间戳
            self.metrics.last_update_timestamp.set(time.time())

        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.error(f"更新数据库指标失败: {e}")

        duration = time.time() - start_time
        logger.debug(f"数据库指标更新耗时: {duration:.2f}秒")

    def record_query_duration(
        self,
        query_type: str,
        duration: float,
    ) -> None:
        """
        记录数据库查询耗时

        Args:
            query_type: 查询类型（SELECT/INSERT/UPDATE/DELETE）
            duration: 查询耗时（秒）
        """
        try:
            self.metrics.database_query_duration.labels(query_type=query_type).observe(
                duration
            )
        except (SQLAlchemyError, DatabaseError, ConnectionError, TimeoutError) as e:
            logger.error(f"记录查询耗时失败: {e}")

    def set_tables_to_monitor(self, tables: List[str]) -> None:
        """
        设置需要监控的表列表

        Args:
            tables: 表名列表
        """
        # 验证表名安全性
        safe_tables = []
        for table in tables:
            if self._is_safe_table_name(table):
                safe_tables.append(table)
            else:
                logger.warning(f"忽略不安全的表名: {table}")

        self.tables_to_monitor = safe_tables

    def get_monitored_tables(self) -> List[str]:
        """
        获取当前监控的表列表

        Returns:
            List[str]: 表名列表
        """
        return self.tables_to_monitor.copy()
