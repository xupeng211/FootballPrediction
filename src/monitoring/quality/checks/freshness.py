"""
数据新鲜度检查器 / Data Freshness Checker

负责检查数据表的新鲜度，基于最后更新时间计算。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import inspect
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.match import Match
from src.database.models.odds import Odds
from src.database.models.predictions import Predictions
from src.database.models.team import Team
from src.database.connection import DatabaseManager

from ..core.results import DataFreshnessResult

logger = logging.getLogger(__name__)


class FreshnessChecker:
    """数据新鲜度检查器"""

    def __init__(self, freshness_thresholds: Optional[Dict[str, float]] = None):
        """
        初始化新鲜度检查器

        Args:
            freshness_thresholds: 各表的新鲜度阈值（小时），默认24小时
        """
        self.freshness_thresholds = freshness_thresholds or {
            "matches": 24,
            "odds": 6,
            "predictions": 48,
            "teams": 168,  # 7天
        }
        self.db_manager = DatabaseManager()

    async def check_data_freshness(
        self, table_names: Optional[List[str]] = None
    ) -> Dict[str, DataFreshnessResult]:
        """
        检查数据新鲜度 / Check Data Freshness

        检查指定表或所有配置表的数据新鲜度，基于最后更新时间计算。
        Check data freshness for specified tables or all configured tables,
        calculated based on last update time.

        Args:
            table_names (Optional[List[str]]): 要检查的表名列表，为空时检查所有配置的表 /
                                              List of table names to check, checks all configured tables if empty
                Defaults to None

        Returns:
            Dict[str, DataFreshnessResult]: 各表的新鲜度检查结果 / Freshness check results for each table
                Keys are table names, values are DataFreshnessResult objects

        Raises:
            Exception: 当数据库查询发生错误时抛出 / Raised when database query fails

        Example:
            ```python
            checker = FreshnessChecker()

            # 检查所有表的新鲜度
            results = await checker.check_data_freshness()

            # 检查特定表的新鲜度
            results = await checker.check_data_freshness(["matches", "odds"])

            for table_name, result in results.items():
                if result.is_fresh:
                    print(f"表 {table_name} 数据新鲜 (更新于 {result.freshness_hours} 小时前)")
                else:
                    print(f"表 {table_name} 数据过期 (更新于 {result.freshness_hours} 小时前)")
            ```
        """
        if table_names is None:
            table_names = list(self.freshness_thresholds.keys())

        results: Dict[str, Any] = {}

        async with self.db_manager.get_async_session() as session:
            for table_name in table_names:
                try:
                    result = await self._check_table_freshness(session, table_name)
                    results[table_name] = result
                    logger.debug(f"表 {table_name} 新鲜度检查完成")
                except Exception as e:
                    logger.error(f"检查表 {table_name} 新鲜度失败: {e}")
                    # 创建失败结果
                    results[table_name] = DataFreshnessResult(
                        table_name=table_name,
                        last_update_time=None,
                        records_count=0,
                        freshness_hours=999999,
                        is_fresh=False,
                        threshold_hours=self.freshness_thresholds.get(
                            str(table_name), 24
                        ),
                    )

        logger.info(f"数据新鲜度检查完成，检查了 {len(results)} 张表")
        return results

    async def _check_table_freshness(
        self, session: AsyncSession, table_name: str
    ) -> DataFreshnessResult:
        """
        检查单个表的数据新鲜度

        Args:
            session: 数据库会话
            table_name: 表名

        Returns:
            DataFreshnessResult: 新鲜度检查结果
        """
        threshold_hours = self.freshness_thresholds.get(str(table_name), 24)

        # 根据表名选择相应的模型和时间字段
        if table_name == "matches":
            model = Match  # type: ignore[assignment]
            time_field = Match.updated_at  # type: ignore[assignment]
        elif table_name == "odds":
            model = Odds  # type: ignore[assignment]
            time_field = Odds.collected_at  # type: ignore[assignment]
        elif table_name == "predictions":
            model = Predictions  # type: ignore[assignment]
            time_field = Predictions.created_at  # type: ignore[assignment]
        elif table_name == "teams":
            model = Team  # type: ignore[assignment]
            time_field = Team.updated_at  # type: ignore[assignment]
        else:
            # 对于未知表，使用原生SQL查询
            return await self._check_table_freshness_sql(
                session, table_name, threshold_hours
            )

        # 查询最后更新时间和记录数
        result = await session.execute(
            select(
                func.max(time_field).label("last_update"),
                func.count().label("record_count"),
            ).select_from(model)
        )

        # 兼容不同测试场景：.first() 可能返回协程或直接返回行对象
        row = result.first()
        try:
            # 如果first()返回可等待对象，则等待其结果
            if inspect.isawaitable(row):
                row = await row
        except Exception:
            pass
        last_update_time = row.last_update if row else None
        records_count = row.record_count if row else 0

        # 计算新鲜度
        if last_update_time:
            time_diff = datetime.now() - last_update_time
            freshness_hours = time_diff.total_seconds() / 3600
            is_fresh = freshness_hours <= threshold_hours
        else:
            freshness_hours = 999999
            is_fresh = False

        return DataFreshnessResult(
            table_name=table_name,
            last_update_time=last_update_time,
            records_count=records_count,
            freshness_hours=freshness_hours,
            is_fresh=is_fresh,
            threshold_hours=threshold_hours,
        )

    async def _check_table_freshness_sql(
        self, session: AsyncSession, table_name: str, threshold_hours: float
    ) -> DataFreshnessResult:
        """
        使用原生SQL检查表的新鲜度

        Args:
            session: 数据库会话
            table_name: 表名
            threshold_hours: 新鲜度阈值

        Returns:
            DataFreshnessResult: 新鲜度检查结果
        """
        # 尝试找到时间列
        possible_time_columns = [
            "updated_at",
            "created_at",
            "collected_at",
            "timestamp",
            "modified_at",
            "updated",
        ]

        for column in possible_time_columns:
            try:
                # 检查列是否存在
                result = await session.execute(
                    f"SELECT COUNT(*) FROM information_schema.columns "
                    f"WHERE table_name = '{table_name}' AND column_name = '{column}'"
                )
                count = result.scalar()

                if count > 0:
                    # 使用找到的时间列查询
                    query = f"""
                    SELECT
                        MAX({column}) as last_update,
                        COUNT(*) as record_count
                    FROM {table_name}
                    """

                    result = await session.execute(query)
                    row = result.first()

                    if row:
                        last_update_time = row.last_update
                        records_count = row.record_count

                        # 计算新鲜度
                        if last_update_time:
                            time_diff = datetime.now() - last_update_time
                            freshness_hours = time_diff.total_seconds() / 3600
                            is_fresh = freshness_hours <= threshold_hours
                        else:
                            freshness_hours = 999999
                            is_fresh = False

                        return DataFreshnessResult(
                            table_name=table_name,
                            last_update_time=last_update_time,
                            records_count=records_count,
                            freshness_hours=freshness_hours,
                            is_fresh=is_fresh,
                            threshold_hours=threshold_hours,
                        )

            except Exception:
                continue

        # 如果找不到时间列，返回默认结果
        return DataFreshnessResult(
            table_name=table_name,
            last_update_time=None,
            records_count=0,
            freshness_hours=999999,
            is_fresh=False,
            threshold_hours=threshold_hours,
        )