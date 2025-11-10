"""
特征计算器实现

足球预测系统的核心特征计算逻辑：
- 近期战绩特征计算
- 历史对战特征计算
- 赔率特征计算
- 组合特征计算
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...database.models import Match, Odds, Team
from ..entities import MatchEntity, TeamEntity
from ..feature_definitions import (
    AllMatchFeatures,
    AllTeamFeatures,
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)

logger = logging.getLogger(__name__)


class FeatureCalculator:
    """特征计算器

    负责计算足球预测所需的各种特征
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.logger = logger

    async def calculate_recent_performance_features(
        self, team_id: int, calculation_date: datetime, days_back: int = 30
    ) -> RecentPerformanceFeatures | None:
        """计算球队近期战绩特征

        Args:
            team_id: 球队ID
            calculation_date: 计算日期
            days_back: 回溯天数

        Returns:
            RecentPerformanceFeatures: 近期战绩特征
        """
        try:
            # 查询最近5场比赛
            start_date = calculation_date - timedelta(days=days_back)

            query = (
                select(Match)
                .where(
                    Match.match_date < calculation_date,
                    Match.match_date >= start_date,
                    (Match.home_team_id == team_id) | (Match.away_team_id == team_id),
                    Match.status == "FINISHED",
                )
                .order_by(Match.match_date.desc())
                .limit(5)
            )

            result = await self.db_session.execute(query)
            matches = result.scalars().all()

            if not matches:
                self.logger.warning(f"Team {team_id} has no recent matches")
                return None

            # 统计近期战绩
            recent_5 = {
                "wins": 0,
                "draws": 0,
                "losses": 0,
                "goals_for": 0,
                "goals_against": 0,
                "points": 0,
                "home_wins": 0,
                "away_wins": 0,
                "home_goals_for": 0,
                "away_goals_for": 0,
            }

            for match in matches:
                is_home = match.home_team_id == team_id
                team_score = match.home_score if is_home else match.away_score
                opponent_score = match.away_score if is_home else match.home_score

                # 基础统计
                recent_5["goals_for"] += team_score or 0
                recent_5["goals_against"] += opponent_score or 0

                # 胜负统计
                if team_score > opponent_score:
                    recent_5["wins"] += 1
                    recent_5["points"] += 3
                    if is_home:
                        recent_5["home_wins"] += 1
                    else:
                        recent_5["away_wins"] += 1
                elif team_score == opponent_score:
                    recent_5["draws"] += 1
                    recent_5["points"] += 1
                else:
                    recent_5["losses"] += 1

                # 主客场进球统计
                if is_home:
                    recent_5["home_goals_for"] += team_score or 0
                else:
                    recent_5["away_goals_for"] += team_score or 0

            return RecentPerformanceFeatures(
                team_id=team_id,
                calculation_date=calculation_date,
                recent_5_wins=recent_5["wins"],
                recent_5_draws=recent_5["draws"],
                recent_5_losses=recent_5["losses"],
                recent_5_goals_for=recent_5["goals_for"],
                recent_5_goals_against=recent_5["goals_against"],
                recent_5_points=recent_5["points"],
                recent_5_home_wins=recent_5["home_wins"],
                recent_5_away_wins=recent_5["away_wins"],
                recent_5_home_goals_for=recent_5["home_goals_for"],
                recent_5_away_goals_for=recent_5["away_goals_for"],
            )

        except Exception as e:
            self.logger.error(
                f"Error calculating recent performance for team {team_id}: {e}"
            )
            return None

    async def calculate_historical_matchup_features(
        self,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime,
        years_back: int = 5,
    ) -> HistoricalMatchupFeatures | None:
        """计算历史对战特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            calculation_date: 计算日期
            years_back: 回溯年数

        Returns:
            HistoricalMatchupFeatures: 历史对战特征
        """
        try:
            # 查询历史对战记录
            start_date = calculation_date - timedelta(days=years_back * 365)

            query = (
                select(Match)
                .where(
                    Match.match_date < calculation_date,
                    Match.match_date >= start_date,
                    (
                        (Match.home_team_id == home_team_id)
                        & (Match.away_team_id == away_team_id)
                    )
                    | (
                        (Match.home_team_id == away_team_id)
                        & (Match.away_team_id == home_team_id)
                    ),
                    Match.status == "FINISHED",
                )
                .order_by(Match.match_date.desc())
            )

            result = await self.db_session.execute(query)
            matches = result.scalars().all()

            if not matches:
                self.logger.warning(
                    f"No H2H matches found between {home_team_id} and {away_team_id}"
                )
                return None

            # 统计历史对战
            h2h_stats = {
                "total_matches": len(matches),
                "home_wins": 0,
                "away_wins": 0,
                "draws": 0,
                "home_goals_total": 0,
                "away_goals_total": 0,
                "recent_5_home_wins": 0,
                "recent_5_away_wins": 0,
                "recent_5_draws": 0,
            }

            # 近5次交手统计
            matches[:5]

            for i, match in enumerate(matches):
                is_home_at_home = match.home_team_id == home_team_id

                # 进球统计
                if is_home_at_home:
                    h2h_stats["home_goals_total"] += match.home_score or 0
                    h2h_stats["away_goals_total"] += match.away_score or 0

                    home_team_score = match.home_score or 0
                    away_team_score = match.away_score or 0
                else:
                    h2h_stats["home_goals_total"] += match.away_score or 0
                    h2h_stats["away_goals_total"] += match.home_score or 0

                    home_team_score = match.away_score or 0
                    away_team_score = match.home_score or 0

                # 胜负统计
                if home_team_score > away_team_score:
                    h2h_stats["home_wins"] += 1
                    if i < 5:  # 近5次交手
                        h2h_stats["recent_5_home_wins"] += 1
                elif home_team_score == away_team_score:
                    h2h_stats["draws"] += 1
                    if i < 5:
                        h2h_stats["recent_5_draws"] += 1
                else:
                    h2h_stats["away_wins"] += 1
                    if i < 5:
                        h2h_stats["recent_5_away_wins"] += 1

            return HistoricalMatchupFeatures(
                home_team_id=home_team_id,
                away_team_id=away_team_id,
                calculation_date=calculation_date,
                h2h_total_matches=h2h_stats["total_matches"],
                h2h_home_wins=h2h_stats["home_wins"],
                h2h_away_wins=h2h_stats["away_wins"],
                h2h_draws=h2h_stats["draws"],
                h2h_home_goals_total=h2h_stats["home_goals_total"],
                h2h_away_goals_total=h2h_stats["away_goals_total"],
                h2h_recent_5_home_wins=h2h_stats["recent_5_home_wins"],
                h2h_recent_5_away_wins=h2h_stats["recent_5_away_wins"],
                h2h_recent_5_draws=h2h_stats["recent_5_draws"],
            )

        except Exception as e:
            self.logger.error(
                f"Error calculating H2H features for {home_team_id} vs {away_team_id}: {e}"
            )
            return None

    async def calculate_odds_features(
        self, match_id: int, calculation_date: datetime
    ) -> OddsFeatures | None:
        """计算赔率特征

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期

        Returns:
            OddsFeatures: 赔率特征
        """
        try:
            # 查询赔率数据 - 获取主胜赔率
            home_odds_query = (
                select(Odds)
                .where(
                    Odds.match_id == match_id,
                    Odds.bet_type == "home_win",
                    Odds.is_active,
                )
                .order_by(Odds.created_at.desc())
                .limit(1)
            )

            draw_odds_query = (
                select(Odds)
                .where(
                    Odds.match_id == match_id,
                    Odds.bet_type == "draw",
                    Odds.is_active,
                )
                .order_by(Odds.created_at.desc())
                .limit(1)
            )

            away_odds_query = (
                select(Odds)
                .where(
                    Odds.match_id == match_id,
                    Odds.bet_type == "away_win",
                    Odds.is_active,
                )
                .order_by(Odds.created_at.desc())
                .limit(1)
            )

            # 执行查询
            home_odds_result = await self.db_session.execute(home_odds_query)
            draw_odds_result = await self.db_session.execute(draw_odds_query)
            away_odds_result = await self.db_session.execute(away_odds_query)

            home_odds_data = home_odds_result.scalar_one_or_none()
            draw_odds_data = draw_odds_result.scalar_one_or_none()
            away_odds_data = away_odds_result.scalar_one_or_none()

            if not all([home_odds_data, draw_odds_data, away_odds_data]):
                self.logger.warning(f"Incomplete odds data found for match {match_id}")
                return None

            # 计算平均赔率和隐含概率
            home_odds = Decimal(str(home_odds_data.odds_value))
            draw_odds = Decimal(str(draw_odds_data.odds_value))
            away_odds = Decimal(str(away_odds_data.odds_value))

            # 隐含概率计算
            home_implied_prob = float(1 / home_odds) if home_odds > 0 else None
            draw_implied_prob = float(1 / draw_odds) if draw_odds > 0 else None
            away_implied_prob = float(1 / away_odds) if away_odds > 0 else None

            return OddsFeatures(
                match_id=match_id,
                calculation_date=calculation_date,
                home_odds_avg=home_odds,
                draw_odds_avg=draw_odds,
                away_odds_avg=away_odds,
                home_implied_probability=home_implied_prob,
                draw_implied_probability=draw_implied_prob,
                away_implied_probability=away_implied_prob,
                bookmaker_count=1,  # 简化实现，基于实际查询结果
                max_home_odds=home_odds,
                min_home_odds=home_odds,
                odds_range_home=0.0,  # 简化实现
            )

        except Exception as e:
            self.logger.error(
                f"Error calculating odds features for match {match_id}: {e}"
            )
            return None

    async def calculate_all_match_features(
        self, match_id: int, calculation_date: datetime | None = None
    ) -> AllMatchFeatures | None:
        """计算比赛的所有特征

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期，默认为当前时间

        Returns:
            AllMatchFeatures: 比赛完整特征集合
        """
        try:
            if calculation_date is None:
                calculation_date = datetime.now()

            # 获取比赛信息
            match_query = select(Match).where(Match.id == match_id)
            match_result = await self.db_session.execute(match_query)
            match = match_result.scalar_one_or_none()

            if not match:
                self.logger.error(f"Match {match_id} not found")
                return None

            # 创建比赛实体
            match_entity = MatchEntity(
                match_id=match.id,
                home_team_id=match.home_team_id,
                away_team_id=match.away_team_id,
                league_id=getattr(match, "league_id", 1),  # 使用默认值1如果字段不存在
                match_time=match.match_date,
                season=getattr(
                    match, "season", "2024-2025"
                ),  # 使用默认值如果字段不存在
            )

            # 计算各部分特征
            home_recent = await self.calculate_recent_performance_features(
                match.home_team_id, calculation_date
            )
            away_recent = await self.calculate_recent_performance_features(
                match.away_team_id, calculation_date
            )
            h2h_features = await self.calculate_historical_matchup_features(
                match.home_team_id, match.away_team_id, calculation_date
            )
            odds_features = await self.calculate_odds_features(
                match_id, calculation_date
            )

            # 检查必需特征
            if not all([home_recent, away_recent, h2h_features, odds_features]):
                self.logger.warning(f"Missing some features for match {match_id}")
                # 可以选择返回部分特征或None
                return None

            return AllMatchFeatures(
                match_entity=match_entity,
                home_team_recent=home_recent,
                away_team_recent=away_recent,
                historical_matchup=h2h_features,
                odds_features=odds_features,
            )

        except Exception as e:
            self.logger.error(
                f"Error calculating all features for match {match_id}: {e}"
            )
            return None

    async def calculate_team_features(
        self, team_id: int, calculation_date: datetime | None = None
    ) -> AllTeamFeatures | None:
        """计算球队的所有特征

        Args:
            team_id: 球队ID
            calculation_date: 计算日期，默认为当前时间

        Returns:
            AllTeamFeatures: 球队完整特征集合
        """
        try:
            if calculation_date is None:
                calculation_date = datetime.now()

            # 获取球队信息
            team_query = select(Team).where(Team.id == team_id)
            team_result = await self.db_session.execute(team_query)
            team = team_result.scalar_one_or_none()

            if not team:
                self.logger.error(f"Team {team_id} not found")
                return None

            # 创建球队实体
            team_entity = TeamEntity(
                id=team.id,
                name=team.name,
                short_name=team.short_name,
                country=team.country,
            )

            # 计算近期战绩特征
            recent_performance = await self.calculate_recent_performance_features(
                team_id, calculation_date
            )

            if not recent_performance:
                self.logger.warning(f"No recent performance for team {team_id}")
                return None

            return AllTeamFeatures(
                team_entity=team_entity, recent_performance=recent_performance
            )

        except Exception as e:
            self.logger.error(f"Error calculating team features for {team_id}: {e}")
            return None

    async def batch_calculate_match_features(
        self, match_ids: list[int], calculation_date: datetime | None = None
    ) -> dict[int, AllMatchFeatures | None]:
        """批量计算比赛特征

        Args:
            match_ids: 比赛ID列表
            calculation_date: 计算日期

        Returns:
            Dict[int, AllMatchFeatures]: 比赛ID到特征的映射
        """
        if calculation_date is None:
            calculation_date = datetime.now()

        results = {}
        for match_id in match_ids:
            try:
                features = await self.calculate_all_match_features(
                    match_id, calculation_date
                )
                results[match_id] = features
            except Exception as e:
                self.logger.error(
                    f"Failed to calculate features for match {match_id}: {e}"
                )
                results[match_id] = None

        return results
