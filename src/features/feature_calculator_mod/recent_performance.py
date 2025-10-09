"""
近期战绩特征计算模块

负责计算球队的近期表现特征，包括胜负平统计、进球数等。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models.match import Match, MatchStatus
from ..feature_definitions import RecentPerformanceFeatures


class RecentPerformanceCalculator:
    """近期战绩特征计算器"""

    def __init__(self, db_manager: Any):
        """
        初始化计算器

        Args:
            db_manager: 数据库管理器
        """
        self.db_manager = db_manager

    async def calculate(
        self,
        team_id: int,
        calculation_date: datetime,
        session: Optional[AsyncSession] = None,
    ) -> RecentPerformanceFeatures:
        """
        计算球队近期战绩特征

        Args:
            team_id: 球队ID
            calculation_date: 计算日期
            session: 数据库会话（可选）

        Returns:
            RecentPerformanceFeatures: 近期战绩特征
        """
        if session is None:
            async with self.db_manager.get_async_session() as session:
                return await self._calculate_recent_performance(
                    session, team_id, calculation_date
                )
        else:
            return await self._calculate_recent_performance(
                session, team_id, calculation_date
            )

    async def _calculate_recent_performance(
        self, session: AsyncSession, team_id: int, calculation_date: datetime
    ) -> RecentPerformanceFeatures:
        """内部近期战绩计算逻辑"""

        # 查询最近5场比赛
        recent_matches_query = (
            select(Match)
            .where(
                and_(
                    or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                    Match.match_time < calculation_date,
                    Match.match_status == MatchStatus.FINISHED,
                )
            )
            .order_by(desc(Match.match_time))
            .limit(5)
        )

        result = await session.execute(recent_matches_query)
        recent_matches = result.scalars().all()

        # 初始化特征
        features = RecentPerformanceFeatures(
            team_id=team_id, calculation_date=calculation_date
        )

        wins = draws = losses = 0
        goals_for = goals_against = points = 0
        home_wins = away_wins = 0
        home_goals_for = away_goals_for = 0

        for match in recent_matches:
            is_home_team = match.home_team_id == team_id

            if is_home_team:
                team_score = match.home_score or 0
                opponent_score = match.away_score or 0
            else:
                team_score = match.away_score or 0
                opponent_score = match.home_score or 0

            goals_for += team_score
            goals_against += opponent_score

            # 计算胜负平
            if team_score > opponent_score:
                wins += 1
                points += 3
                if is_home_team:
                    home_wins += 1
                    home_goals_for += team_score
                else:
                    away_wins += 1
                    away_goals_for += team_score
            elif team_score == opponent_score:
                draws += 1
                points += 1
                if is_home_team:
                    home_goals_for += team_score
                else:
                    away_goals_for += team_score
            else:
                losses += 1
                if is_home_team:
                    home_goals_for += team_score
                else:
                    away_goals_for += team_score

        # 更新特征
        features.recent_5_wins = wins
        features.recent_5_draws = draws
        features.recent_5_losses = losses
        features.recent_5_goals_for = goals_for
        features.recent_5_goals_against = goals_against
        features.recent_5_points = points
        features.recent_5_home_wins = home_wins
        features.recent_5_away_wins = away_wins
        features.recent_5_home_goals_for = home_goals_for
        features.recent_5_away_goals_for = away_goals_for

        return features

    @staticmethod
    def calculate_form(matches: List[Dict[str, Any]]) -> float:
        """
        根据比赛结果计算球队状态评分，范围 0-1。

        Args:
            matches: 比赛结果列表

        Returns:
            float: 状态评分
        """
        if not matches:
            return 0.0

        points = 0
        for match in matches:
            result = (match or {}).get("result")
            if result == "win":
                points += 3
            elif result == "draw":
                points += 1

        max_points = len(matches) * 3
        return round(points / max_points, 4) if max_points else 0.0

    async def calculate_extended_recent_performance(
        self,
        team_id: int,
        calculation_date: datetime,
        match_count: int = 10,
        session: Optional[AsyncSession] = None,
    ) -> Dict[str, Any]:
        """
        计算扩展的近期战绩特征（可自定义比赛数量）

        Args:
            team_id: 球队ID
            calculation_date: 计算日期
            match_count: 比赛数量（默认10场）
            session: 数据库会话（可选）

        Returns:
            Dict[str, Any]: 扩展的近期战绩特征
        """
        if session is None:
            async with self.db_manager.get_async_session() as session:
                return await self._calculate_extended_performance(
                    session, team_id, calculation_date, match_count
                )
        else:
            return await self._calculate_extended_performance(
                session, team_id, calculation_date, match_count
            )

    async def _calculate_extended_performance(
        self,
        session: AsyncSession,
        team_id: int,
        calculation_date: datetime,
        match_count: int,
    ) -> Dict[str, Any]:
        """内部扩展战绩计算逻辑"""

        recent_matches_query = (
            select(Match)
            .where(
                and_(
                    or_(Match.home_team_id == team_id, Match.away_team_id == team_id),
                    Match.match_time < calculation_date,
                    Match.match_status == MatchStatus.FINISHED,
                )
            )
            .order_by(desc(Match.match_time))
            .limit(match_count)
        )

        result = await session.execute(recent_matches_query)
        recent_matches = result.scalars().all()

        # 计算更详细的统计
        stats = {
            "team_id": team_id,
            "calculation_date": calculation_date,
            "match_count": len(recent_matches),
            "wins": 0,
            "draws": 0,
            "losses": 0,
            "goals_for": 0,
            "goals_against": 0,
            "clean_sheets": 0,
            "failed_to_score": 0,
            "home_performance": {"wins": 0, "goals": 0},
            "away_performance": {"wins": 0, "goals": 0},
        }

        for match in recent_matches:
            is_home = match.home_team_id == team_id
            team_score = match.home_score if is_home else match.away_score
            opponent_score = match.away_score if is_home else match.home_score

            team_score = team_score or 0
            opponent_score = opponent_score or 0

            # 基础统计
            stats["goals_for"] += team_score
            stats["goals_against"] += opponent_score

            if team_score > opponent_score:
                stats["wins"] += 1
                if is_home:
                    stats["home_performance"]["wins"] += 1
                else:
                    stats["away_performance"]["wins"] += 1
            elif team_score == opponent_score:
                stats["draws"] += 1
            else:
                stats["losses"] += 1

            # 零封和未进球统计
            if opponent_score == 0:
                stats["clean_sheets"] += 1
            if team_score == 0:
                stats["failed_to_score"] += 1

            # 主客场进球
            if is_home:
                stats["home_performance"]["goals"] += team_score
            else:
                stats["away_performance"]["goals"] += team_score

        # 计算衍生指标
        total_matches = len(recent_matches)
        if total_matches > 0:
            stats["win_rate"] = stats["wins"] / total_matches
            stats["draw_rate"] = stats["draws"] / total_matches
            stats["loss_rate"] = stats["losses"] / total_matches
            stats["avg_goals_for"] = stats["goals_for"] / total_matches
            stats["avg_goals_against"] = stats["goals_against"] / total_matches
            stats["goal_difference"] = stats["goals_for"] - stats["goals_against"]
        else:
            stats.update({
                "win_rate": 0.0,
                "draw_rate": 0.0,
                "loss_rate": 0.0,
                "avg_goals_for": 0.0,
                "avg_goals_against": 0.0,
                "goal_difference": 0,
            })

        return stats