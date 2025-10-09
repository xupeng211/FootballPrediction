"""
数据一致性检查器 / Data Consistency Checker

负责检查数据的一致性，包括外键一致性、赔率数据一致性、比赛状态一致性等。
"""

import inspect
import logging
from typing import Any, Dict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.connection import DatabaseManager

logger = logging.getLogger(__name__)


class ConsistencyChecker:
    """数据一致性检查器"""

    def __init__(self):
        """初始化一致性检查器"""
        self.db_manager = DatabaseManager()

    async def check_data_consistency(self) -> Dict[str, Any]:
        """
        检查数据一致性

        Returns:
            Dict[str, Any]: 一致性检查结果
        """
        consistency_results: Dict[str, Any] = {}

        async with self.db_manager.get_async_session() as session:
            # 检查外键一致性
            consistency_results[
                "foreign_key_consistency"
            ] = await self._check_foreign_key_consistency(session)

            # 检查赔率数据一致性
            consistency_results[
                "odds_consistency"
            ] = await self._check_odds_consistency(session)

            # 检查比赛状态一致性
            consistency_results[
                "match_status_consistency"
            ] = await self._check_match_status_consistency(session)

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