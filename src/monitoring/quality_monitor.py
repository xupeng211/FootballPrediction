"""
数据质量监控器 / Data Quality Monitor

负责监控数据新鲜度、缺失率、完整性等数据质量指标。
支持实时监控、历史趋势分析、质量评分计算等功能。

Responsible for monitoring data quality metrics such as freshness, missing rates, and completeness.
Supports real-time monitoring, historical trend analysis, and quality score calculation.

主要类 / Main Classes:
    QualityMonitor: 数据质量监控主类 / Main data quality monitoring class
    DataFreshnessResult: 数据新鲜度检查结果 / Data freshness check result
    DataCompletenessResult: 数据完整性检查结果 / Data completeness check result

主要方法 / Main Methods:
    QualityMonitor.check_data_freshness(): 检查数据新鲜度 / Check data freshness
    QualityMonitor.check_data_completeness(): 检查数据完整性 / Check data completeness
    QualityMonitor.calculate_overall_quality_score(): 计算总体质量评分 / Calculate overall quality score

使用示例 / Usage Example:
    ```python
    from src.monitoring.quality_monitor import QualityMonitor

    # 创建监控器实例
    monitor = QualityMonitor()

    # 检查数据新鲜度
    freshness_results = await monitor.check_data_freshness()

    # 检查数据完整性
    completeness_results = await monitor.check_data_completeness()

    # 计算总体质量评分
    quality_score = await monitor.calculate_overall_quality_score()
    ```

依赖 / Dependencies:
    - sqlalchemy: 数据库查询 / Database queries
    - src.database.connection: 数据库连接管理 / Database connection management
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, quoted_name, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models.match import Match
from src.database.models.odds import Odds
from src.database.models.predictions import Predictions
from src.database.models.team import Team

logger = logging.getLogger(__name__)


class DataFreshnessResult:
    """数据新鲜度检查结果"""

    def __init__(
        self,
        table_name: str,
        last_update_time: Optional[datetime],
        records_count: int,
        freshness_hours: float,
        is_fresh: bool,
        threshold_hours: float,
    ):
        """
        初始化数据新鲜度结果

        Args:
            table_name: 表名
            last_update_time: 最后更新时间
            records_count: 记录数量
            freshness_hours: 数据新鲜度（小时）
            is_fresh: 是否新鲜
            threshold_hours: 新鲜度阈值（小时）
        """
        self.table_name = table_name
        self.last_update_time = last_update_time
        self.records_count = records_count
        self.freshness_hours = freshness_hours
        self.is_fresh = is_fresh
        self.threshold_hours = threshold_hours

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_name": self.table_name,
            "last_update_time": (
                self.last_update_time.isoformat() if self.last_update_time else None
            ),
            "records_count": self.records_count,
            "freshness_hours": round(self.freshness_hours, 2),
            "is_fresh": self.is_fresh,
            "threshold_hours": self.threshold_hours,
        }


class DataCompletenessResult:
    """数据完整性检查结果"""

    def __init__(
        self,
        table_name: str,
        total_records: int,
        missing_critical_fields: Dict[str, int],
        missing_rate: float,
        completeness_score: float,
    ):
        """
        初始化数据完整性结果

        Args:
            table_name: 表名
            total_records: 总记录数
            missing_critical_fields: 关键字段缺失统计
            missing_rate: 缺失率
            completeness_score: 完整性评分
        """
        self.table_name = table_name
        self.total_records = total_records
        self.missing_critical_fields = missing_critical_fields
        self.missing_rate = missing_rate
        self.completeness_score = completeness_score

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "table_name": self.table_name,
            "total_records": self.total_records,
            "missing_critical_fields": self.missing_critical_fields,
            "missing_rate": round(self.missing_rate, 4),
            "completeness_score": round(self.completeness_score, 2),
        }


class QualityMonitor:
    """
    数据质量监控器主类 / Data Quality Monitor Main Class

    提供以下监控功能：
    - 数据新鲜度监控
    - 数据完整性检查
    - 数据一致性验证
    - 质量评分计算
    - 历史趋势分析

    Provides the following monitoring functions:
    - Data freshness monitoring
    - Data completeness checking
    - Data consistency verification
    - Quality score calculation
    - Historical trend analysis

    Example:
        ```python
        from src.monitoring.quality_monitor import QualityMonitor

        # 创建监控器实例
        monitor = QualityMonitor()

        # 检查特定表的新鲜度
        freshness_results = await monitor.check_data_freshness(["matches", "odds"])

        # 检查所有表的完整性
        completeness_results = await monitor.check_data_completeness()

        # 计算总体质量评分
        overall_score = await monitor.calculate_overall_quality_score()
        ```

    Note:
        基于DATA_DESIGN.md数据质量监控设计。
        Based on DATA_DESIGN.md data quality monitoring design.
    """

    def __init__(self):
        """初始化数据质量监控器"""

        # 数据新鲜度阈值配置（小时）
        self.freshness_thresholds = {
            "matches": 24,  # 比赛数据24小时内
            "odds": 1,  # 赔率数据1小时内
            "predictions": 2,  # 预测数据2小时内
            "teams": 168,  # 球队数据1周内
            "leagues": 720,  # 联赛数据1个月内
        }

        # 关键字段定义
        self.critical_fields = {
            "matches": ["home_team_id", "away_team_id", "league_id", "match_time"],
            "odds": ["match_id", "bookmaker", "home_odds", "draw_odds", "away_odds"],
            "predictions": ["match_id", "model_name", "home_win_probability"],
            "teams": ["team_name", "league_id"],
        }

        # 初始化数据库管理器
        from src.database.connection import DatabaseManager

        self.db_manager = DatabaseManager()

        logger.info("数据质量监控器初始化完成")

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
            from src.monitoring.quality_monitor import QualityMonitor

            monitor = QualityMonitor()

            # 检查所有表的新鲜度
            results = await monitor.check_data_freshness()

            # 检查特定表的新鲜度
            results = await monitor.check_data_freshness(["matches", "odds"])

            for table_name, result in results.items():
                if result.is_fresh:
                    print(f"表 {table_name} 数据新鲜 (更新于 {result.freshness_hours} 小时前)")
                else:
                    print(f"表 {table_name} 数据过期 (更新于 {result.freshness_hours} 小时前)")
            ```

        Note:
            新鲜度阈值在__init__方法中配置。
            Freshness thresholds are configured in the __init__ method.
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
                        threshold_hours=self.freshness_thresholds.get(table_name, 24),
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
        threshold_hours = self.freshness_thresholds.get(table_name, 24)

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
            import inspect

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
        使用原生SQL检查表的数据新鲜度

        Args:
            session: 数据库会话
            table_name: 表名
            threshold_hours: 阈值小时数

        Returns:
            DataFreshnessResult: 新鲜度检查结果
        """
        try:
            # 尝试不同的时间字段
            time_fields = ["updated_at", "created_at", "collected_at", "match_time"]

            last_update_time = None
            records_count = 0

            # Validate table name to prevent SQL injection
            if table_name not in ["matches", "odds", "predictions", "teams", "leagues"]:
                raise ValueError(f"Invalid table name: {table_name}")

            # 使用quoted_name确保表名安全，并使用字符串拼接构建查询
            # 表名已通过quoted_name处理，防止SQL注入
            # Note: Using string concatenation here is safe as table_name is validated
            safe_table_name = quoted_name(table_name, quote=True)
            result = await session.execute(
                text("SELECT COUNT(*) as count FROM " + str(safe_table_name))
            )  # nosec B608
            count_row = count_result.first()
            try:
                import inspect

                if inspect.isawaitable(count_row):
                    count_row = await count_row
            except Exception:
                pass
            records_count = int(count_row[0]) if count_row else 0

            # 尝试获取最后更新时间
            for time_field in time_fields:
                # Validate time field to prevent SQL injection
                if time_field not in [
                    "updated_at",
                    "created_at",
                    "collected_at",
                    "match_time",
                ]:
                    continue
                try:
                    # 表名和字段名都来自预定义的白名单，防止SQL注入
                    # Note: Using string concatenation here is safe as both table_name and time_field are validated
                    time_result = await session.execute(
                        text(
                            "SELECT MAX("
                            + time_field
                            + ") as last_update FROM "
                            + table_name
                        )
                    )  # nosec B608
                    time_row = time_result.first()
                    try:
                        import inspect

                        if inspect.isawaitable(time_row):
                            time_row = await time_row
                    except Exception:
                        pass
                    if time_row and time_row.last_update:
                        last_update_time = time_row.last_update
                        break
                except Exception as e:
                    logger.warning(
                        f"Failed to get last update time for {table_name} using field {time_field}: {e}"
                    )
                    continue

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

        except Exception as e:
            logger.error(f"SQL方式检查表 {table_name} 新鲜度失败: {e}")
            return DataFreshnessResult(
                table_name=table_name,
                last_update_time=None,
                records_count=0,
                freshness_hours=999999,
                is_fresh=False,
                threshold_hours=threshold_hours,
            )

    async def check_data_completeness(
        self, table_names: Optional[List[str]] = None
    ) -> Dict[str, DataCompletenessResult]:
        """
        检查数据完整性

        Args:
            table_names: 要检查的表名列表

        Returns:
            Dict[str, DataCompletenessResult]: 各表的完整性检查结果
        """
        if table_names is None:
            table_names = list(self.critical_fields.keys())

        results: Dict[str, Any] = {}

        async with self.db_manager.get_async_session() as session:
            for table_name in table_names:
                try:
                    result = await self._check_table_completeness(session, table_name)
                    results[table_name] = result
                    logger.debug(f"表 {table_name} 完整性检查完成")
                except Exception as e:
                    logger.error(f"检查表 {table_name} 完整性失败: {e}")

        logger.info(f"数据完整性检查完成，检查了 {len(results)} 张表")
        return results

    async def _check_table_completeness(
        self, session: AsyncSession, table_name: str
    ) -> DataCompletenessResult:
        """
        检查单个表的数据完整性

        Args:
            session: 数据库会话
            table_name: 表名

        Returns:
            DataCompletenessResult: 完整性检查结果
        """
        critical_fields = self.critical_fields.get(table_name, [])

        if not critical_fields:
            logger.warning(f"表 {table_name} 未定义关键字段")
            return DataCompletenessResult(
                table_name=table_name,
                total_records=0,
                missing_critical_fields={},
                missing_rate=0.0,
                completeness_score=100.0,
            )

        # Validate table name to prevent SQL injection
        if table_name not in ["matches", "odds", "predictions", "teams", "leagues"]:
            raise ValueError(f"Invalid table name: {table_name}")

        # 获取总记录数
        # Safe: table_name is validated against whitelist
        # 使用quoted_name确保表名安全，并使用字符串拼接构建查询
        # 表名已通过quoted_name处理，防止SQL注入
        # Note: Using string concatenation here is safe as table_name is validated
        safe_table_name = quoted_name(table_name, quote=True)
        result = await session.execute(
            text("SELECT COUNT(*) as total FROM " + str(safe_table_name))
        )  # nosec B608
        total_row = total_result.first()
        try:
            import inspect

            if inspect.isawaitable(total_row):
                total_row = await total_row
        except Exception:
            pass
        total_records = total_row.total if total_row else 0

        if total_records == 0:
            return DataCompletenessResult(
                table_name=table_name,
                total_records=0,
                missing_critical_fields={},
                missing_rate=0.0,
                completeness_score=100.0,
            )

        # 检查各关键字段的缺失情况
        missing_fields = {}
        total_missing = 0

        for field in critical_fields:
            try:
                # 表名和字段名都来自预定义的白名单，防止SQL注入
                # Note: Using string concatenation here is safe as both table_name and field are validated
                missing_result = await session.execute(
                    text(
                        "SELECT COUNT(*) as missing FROM "
                        + table_name
                        + " WHERE "
                        + field
                        + " IS NULL"
                    )
                )  # nosec B608
                missing_row = missing_result.first()
                try:
                    import inspect

                    if inspect.isawaitable(missing_row):
                        missing_row = await missing_row
                except Exception:
                    pass
                missing_count = missing_row.missing if missing_row else 0
                missing_fields[field] = missing_count
                total_missing += missing_count
            except Exception as e:
                logger.warning(f"检查字段 {field} 缺失情况失败: {e}")
                missing_fields[field] = 0

        # 计算缺失率和完整性评分
        total_checks = total_records * len(critical_fields)
        missing_rate = total_missing / total_checks if total_checks > 0 else 0
        completeness_score = (1 - missing_rate) * 100

        return DataCompletenessResult(
            table_name=table_name,
            total_records=total_records,
            missing_critical_fields=missing_fields,
            missing_rate=missing_rate,
            completeness_score=completeness_score,
        )

    async def check_data_consistency(self) -> Dict[str, Any]:
        """
        检查数据一致性

        Returns:
            Dict[str, Any]: 一致性检查结果
        """
        consistency_results: Dict[str, Any] = {}

        async with self.db_manager.get_async_session() as session:
            # 检查外键一致性
            consistency_results["foreign_key_consistency"] = (
                await self._check_foreign_key_consistency(session)
            )

            # 检查赔率数据一致性
            consistency_results["odds_consistency"] = (
                await self._check_odds_consistency(session)
            )

            # 检查比赛状态一致性
            consistency_results["match_status_consistency"] = (
                await self._check_match_status_consistency(session)
            )

        logger.info("数据一致性检查完成")
        return consistency_results

    async def _check_foreign_key_consistency(
        self, session: AsyncSession
    ) -> Dict[str, Any]:
        """检查外键一致性"""
        results: Dict[str, Any] = {}

        try:
            # 检查 matches 表中的 team 引用
            orphaned_home_teams = await session.execute(
                text(
                    """
                    SELECT COUNT(*) as count
                    FROM matches m
                    LEFT JOIN teams t ON m.home_team_id = t.id
                    WHERE t.id IS NULL AND m.home_team_id IS NOT NULL
                """
                )
            )
            home_teams_row = orphaned_home_teams.first()
            try:
                import inspect

                if inspect.isawaitable(home_teams_row):
                    home_teams_row = await home_teams_row
            except Exception:
                pass
            results["orphaned_home_teams"] = (
                int(home_teams_row[0]) if home_teams_row else 0
            )

            orphaned_away_teams = await session.execute(
                text(
                    """
                    SELECT COUNT(*) as count
                    FROM matches m
                    LEFT JOIN teams t ON m.away_team_id = t.id
                    WHERE t.id IS NULL AND m.away_team_id IS NOT NULL
                """
                )
            )
            away_teams_row = orphaned_away_teams.first()
            try:
                import inspect

                if inspect.isawaitable(away_teams_row):
                    away_teams_row = await away_teams_row
            except Exception:
                pass
            results["orphaned_away_teams"] = (
                int(away_teams_row[0])
                if away_teams_row and away_teams_row[0] is not None
                else 0
            )

            # 检查 odds 表中的 match 引用
            orphaned_odds = await session.execute(
                text(
                    """
                    SELECT COUNT(*) as count
                    FROM odds o
                    LEFT JOIN matches m ON o.match_id = m.id
                    WHERE m.id IS NULL AND o.match_id IS NOT NULL
                """
                )
            )
            orphaned_row = orphaned_odds.first()
            try:
                import inspect

                if inspect.isawaitable(orphaned_row):
                    orphaned_row = await orphaned_row
            except Exception:
                pass
            results["orphaned_odds"] = int(orphaned_row[0]) if orphaned_row else 0

        except Exception as e:
            logger.error(f"检查外键一致性失败: {e}")
            results["error"] = str(e)

        return results

    async def _check_odds_consistency(self, session: AsyncSession) -> Dict[str, Any]:
        """检查赔率数据一致性"""
        results: Dict[str, Any] = {}

        try:
            # 检查赔率的合理性（应该 > 1.0）
            invalid_odds = await session.execute(
                text(
                    """
                    SELECT COUNT(*) as count
                    FROM odds
                    WHERE home_odds <= 1.0 OR draw_odds <= 1.0 OR away_odds <= 1.0
                """
                )
            )
            invalid_odds_row = invalid_odds.first()
            try:
                import inspect

                if inspect.isawaitable(invalid_odds_row):
                    invalid_odds_row = await invalid_odds_row
            except Exception:
                pass
            results["invalid_odds_range"] = (
                int(invalid_odds_row[0])
                if invalid_odds_row and invalid_odds_row[0] is not None
                else 0
            )

            # 检查隐含概率和是否合理（应该在 0.95-1.20 之间）
            invalid_probability = await session.execute(
                text(
                    """
                    SELECT COUNT(*) as count
                    FROM odds
                    WHERE (1.0/home_odds + 1.0/draw_odds + 1.0/away_odds) < 0.95
                       OR (1.0/home_odds + 1.0/draw_odds + 1.0/away_odds) > 1.20
                """
                )
            )
            invalid_row = invalid_probability.first()
            try:
                import inspect

                if inspect.isawaitable(invalid_row):
                    invalid_row = await invalid_row
            except Exception:
                pass
            results["invalid_probability_sum"] = (
                int(invalid_row[0]) if invalid_row else 0
            )

        except Exception as e:
            logger.error(f"检查赔率一致性失败: {e}")
            results["error"] = str(e)

        return results

    async def _check_match_status_consistency(
        self, session: AsyncSession
    ) -> Dict[str, Any]:
        """检查比赛状态一致性"""
        results: Dict[str, Any] = {}

        try:
            # 检查已完成比赛是否有比分
            finished_without_score = await session.execute(
                text(
                    """
                    SELECT COUNT(*) as count
                    FROM matches
                    WHERE match_status = 'finished'
                      AND (home_score IS NULL OR away_score IS NULL)
                """
                )
            )
            finished_result = finished_without_score.first()
            try:
                import inspect

                if inspect.isawaitable(finished_result):
                    finished_result = await finished_result
            except Exception:
                pass
            results["finished_matches_without_score"] = (
                int(finished_result[0])
                if finished_result and finished_result[0] is not None
                else 0
            )

            # 检查未开始比赛是否有比分
            scheduled_with_score = await session.execute(
                text(
                    """
                    SELECT COUNT(*) as count
                    FROM matches
                    WHERE match_status = 'scheduled'
                      AND (home_score IS NOT NULL OR away_score IS NOT NULL)
                """
                )
            )
            scheduled_row = scheduled_with_score.first()
            try:
                import inspect

                if inspect.isawaitable(scheduled_row):
                    scheduled_row = await scheduled_row
            except Exception:
                pass
            results["scheduled_matches_with_score"] = (
                int(scheduled_row[0]) if scheduled_row else 0
            )

        except Exception as e:
            logger.error(f"检查比赛状态一致性失败: {e}")
            results["error"] = str(e)

        return results

    async def calculate_overall_quality_score(self) -> Dict[str, Any]:
        """
        计算总体数据质量评分

        Returns:
            Dict[str, Any]: 质量评分结果
        """
        try:
            # 获取各项检查结果
            freshness_results = await self.check_data_freshness()
            completeness_results = await self.check_data_completeness()
            consistency_results = await self.check_data_consistency()

            # 计算新鲜度得分
            fresh_tables = sum(1 for r in freshness_results.values() if r.is_fresh)
            freshness_score = (
                (fresh_tables / len(freshness_results)) * 100
                if freshness_results
                else 0
            )

            # 计算完整性得分
            completeness_scores = [
                r.completeness_score for r in completeness_results.values()
            ]
            avg_completeness_score = (
                sum(completeness_scores) / len(completeness_scores)
                if completeness_scores
                else 0
            )

            # 计算一致性得分（基于错误数量）
            consistency_errors = 0
            fk_consistency = consistency_results.get("foreign_key_consistency", {})
            odds_consistency = consistency_results.get("odds_consistency", {})
            match_consistency = consistency_results.get("match_status_consistency", {})

            consistency_errors += sum(
                v for v in fk_consistency.values() if isinstance(v, int)
            )
            consistency_errors += sum(
                v for v in odds_consistency.values() if isinstance(v, int)
            )
            consistency_errors += sum(
                v for v in match_consistency.values() if isinstance(v, int)
            )

            # 一致性得分：错误数量越少分数越高
            consistency_score = max(0, 100 - consistency_errors * 0.1)

            # 计算总体评分（加权平均）
            overall_score = (
                freshness_score * 0.3
                + avg_completeness_score * 0.4
                + consistency_score * 0.3
            )

            return {
                "overall_score": round(overall_score, 2),
                "freshness_score": round(freshness_score, 2),
                "completeness_score": round(avg_completeness_score, 2),
                "consistency_score": round(consistency_score, 2),
                "detailed_results": {
                    "freshness": {
                        table: result.to_dict()
                        for table, result in freshness_results.items()
                    },
                    "completeness": {
                        table: result.to_dict()
                        for table, result in completeness_results.items()
                    },
                    "consistency": consistency_results,
                },
                "quality_level": self._get_quality_level(overall_score),
                "check_time": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"计算总体质量评分失败: {e}")
            return {
                "overall_score": 0,
                "error": str(e),
                "check_time": datetime.now().isoformat(),
            }

    def _get_quality_level(self, score: float) -> str:
        """
        获取质量等级

        Args:
            score: 质量评分

        Returns:
            str: 质量等级
        """
        if score >= 95:
            return "优秀"
        elif score >= 85:
            return "良好"
        elif score >= 70:
            return "一般"
        elif score >= 50:
            return "较差"
        else:
            return "很差"

    async def get_quality_trends(self, days: int = 7) -> Dict[str, Any]:
        """
        获取质量趋势（需要历史数据支持）

        Args:
            days: 查看天数

        Returns:
            Dict[str, Any]: 质量趋势数据
        """
        # 这里可以扩展实现历史质量数据的存储和分析
        # 当前版本返回当前快照
        current_quality = await self.calculate_overall_quality_score()

        return {
            "current_quality": current_quality,
            "trend_period_days": days,
            "trend_data": [],  # 待实现历史数据收集
            "recommendations": self._generate_quality_recommendations(current_quality),
        }

    def _generate_quality_recommendations(
        self, quality_data: Dict[str, Any]
    ) -> List[str]:
        """
        生成质量改进建议

        Args:
            quality_data: 质量数据

        Returns:
            List[str]: 改进建议列表
        """
        recommendations = []

        # 基于各项评分给出建议
        if quality_data.get("freshness_score", 0) < 80:
            recommendations.append(
                "数据新鲜度较低，建议检查数据采集任务的执行频率和稳定性"
            )

        if quality_data.get("completeness_score", 0) < 85:
            recommendations.append("数据完整性有待提升，建议检查关键字段的数据录入流程")

        if quality_data.get("consistency_score", 0) < 90:
            recommendations.append("数据一致性存在问题，建议检查外键约束和数据验证规则")

        if quality_data.get("overall_score", 0) < 70:
            recommendations.append("整体数据质量需要重点关注，建议制定数据治理改进计划")

        return recommendations
