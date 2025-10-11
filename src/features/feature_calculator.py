# mypy: ignore-errors
"""
import asyncio
特征计算器

实现足球预测系统的核心特征计算逻辑：
- 近期战绩特征计算
- 历史对战特征计算
- 赔率特征计算
- 批量特征计算和缓存
"""

import asyncio
import statistics
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, desc, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database.connection import DatabaseManager
from ..database.models.match import Match, MatchStatus
from ..database.models.odds import Odds
from .entities import MatchEntity, TeamEntity
from .feature_definitions import (
    AllMatchFeatures,
    AllTeamFeatures,
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)


class FeatureCalculator:
    """
    特征计算器

    负责计算各种特征的核心类，支持：
    - 近期战绩特征计算
    - 历史对战特征计算
    - 赔率特征计算
    - 批量计算和缓存优化
    """

    def __init__(self, config: Optional[Dict] = None):
        self.db_manager = DatabaseManager()
        self.config = config or {}
        self.features: list = []  # 存储特征定义

    async def calculate_recent_performance_features(
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
    def _calculate_form(matches: List[Dict[str, Any]]) -> float:
        """根据比赛结果计算球队状态评分，范围 0-1。"""

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

    async def calculate_historical_matchup_features(
        self,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime,
        session: Optional[AsyncSession] = None,
    ) -> HistoricalMatchupFeatures:
        """
        计算历史对战特征

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            calculation_date: 计算日期
            session: 数据库会话（可选）

        Returns:
            HistoricalMatchupFeatures: 历史对战特征
        """
        if session is None:
            async with self.db_manager.get_async_session() as session:
                return await self._calculate_historical_matchup(
                    session, home_team_id, away_team_id, calculation_date
                )
        else:
            return await self._calculate_historical_matchup(
                session, home_team_id, away_team_id, calculation_date
            )

    async def _calculate_historical_matchup(
        self,
        session: AsyncSession,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime,
    ) -> HistoricalMatchupFeatures:
        """内部历史对战计算逻辑"""

        # 查询所有历史对战
        h2h_query = (
            select(Match)
            .where(
                and_(
                    or_(
                        and_(
                            Match.home_team_id == home_team_id,
                            Match.away_team_id == away_team_id,
                        ),
                        and_(
                            Match.home_team_id == away_team_id,
                            Match.away_team_id == home_team_id,
                        ),
                    ),
                    Match.match_time < calculation_date,
                    Match.match_status == MatchStatus.FINISHED,
                )
            )
            .order_by(desc(Match.match_time))
        )

        result = await session.execute(h2h_query)
        h2h_matches = result.scalars().all()

        # 初始化特征
        features = HistoricalMatchupFeatures(
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            calculation_date=calculation_date,
        )

        total_matches = len(h2h_matches)
        home_wins = away_wins = draws = 0
        home_goals_total = away_goals_total = 0

        # 近5次对战统计
        recent_5_home_wins = recent_5_away_wins = recent_5_draws = 0

        for i, match in enumerate(h2h_matches):
            # 确定当前比赛的主客队
            if match.home_team_id == home_team_id:
                # 主队是home_team_id
                match_home_score = match.home_score or 0
                match_away_score = match.away_score or 0
            else:
                # 主队是away_team_id，需要调换
                match_home_score = match.away_score or 0
                match_away_score = match.home_score or 0

            home_goals_total += match_home_score
            away_goals_total += match_away_score

            # 计算胜负平
            if match_home_score > match_away_score:
                home_wins += 1
                if i < 5:  # 近5次
                    recent_5_home_wins += 1
            elif match_home_score == match_away_score:
                draws += 1
                if i < 5:  # 近5次
                    recent_5_draws += 1
            else:
                away_wins += 1
                if i < 5:  # 近5次
                    recent_5_away_wins += 1

        # 更新特征
        features.h2h_total_matches = total_matches
        features.h2h_home_wins = home_wins
        features.h2h_away_wins = away_wins
        features.h2h_draws = draws
        features.h2h_home_goals_total = home_goals_total
        features.h2h_away_goals_total = away_goals_total
        features.h2h_recent_5_home_wins = recent_5_home_wins
        features.h2h_recent_5_away_wins = recent_5_away_wins
        features.h2h_recent_5_draws = recent_5_draws

        return features

    async def calculate_odds_features(
        self,
        match_id: int,
        calculation_date: datetime,
        session: Optional[AsyncSession] = None,
    ) -> OddsFeatures:
        """
        计算赔率特征

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期
            session: 数据库会话（可选）

        Returns:
            OddsFeatures: 赔率特征
        """
        if session is None:
            async with self.db_manager.get_async_session() as session:
                return await self._calculate_odds_features(
                    session, match_id, calculation_date
                )
        else:
            return await self._calculate_odds_features(
                session, match_id, calculation_date
            )

    async def _calculate_odds_features(
        self, session: AsyncSession, match_id: int, calculation_date: datetime
    ) -> OddsFeatures:
        """内部赔率特征计算逻辑"""

        # 查询比赛相关赔率
        odds_query = select(Odds).where(
            and_(
                Odds.match_id == match_id,
                Odds.collected_at <= calculation_date,
                Odds.market_type == "1x2",  # 胜平负市场
            )
        )

        result = await session.execute(odds_query)
        odds_list = result.scalars().all()

        # 初始化特征
        features = OddsFeatures(match_id=match_id, calculation_date=calculation_date)

        if not odds_list:
            return features

        # 提取赔率数据
        home_odds_values = []
        draw_odds_values = []
        away_odds_values = []

        for odds in odds_list:
            if odds.home_odds is not None:
                home_odds_values.append(float(odds.home_odds))
            if odds.draw_odds is not None:
                draw_odds_values.append(float(odds.draw_odds))
            if odds.away_odds is not None:
                away_odds_values.append(float(odds.away_odds))

        # 计算平均赔率
        if home_odds_values:
            features.home_odds_avg = Decimal(str(statistics.mean(home_odds_values)))
            features.max_home_odds = Decimal(str(max(home_odds_values)))
            features.min_home_odds = Decimal(str(min(home_odds_values)))
            features.odds_range_home = max(home_odds_values) - min(home_odds_values)
            features.odds_variance_home = (
                statistics.variance(home_odds_values)
                if len(home_odds_values) > 1
                else 0.0
            )

        if draw_odds_values:
            features.draw_odds_avg = Decimal(str(statistics.mean(draw_odds_values)))
            features.odds_variance_draw = (
                statistics.variance(draw_odds_values)
                if len(draw_odds_values) > 1
                else 0.0
            )

        if away_odds_values:
            features.away_odds_avg = Decimal(str(statistics.mean(away_odds_values)))
            features.odds_variance_away = (
                statistics.variance(away_odds_values)
                if len(away_odds_values) > 1
                else 0.0
            )

        # 计算隐含概率
        if features.home_odds_avg:
            features.home_implied_probability = 1.0 / float(features.home_odds_avg)
        if features.draw_odds_avg:
            features.draw_implied_probability = 1.0 / float(features.draw_odds_avg)
        if features.away_odds_avg:
            features.away_implied_probability = 1.0 / float(features.away_odds_avg)

        # 博彩公司数量
        features.bookmaker_count = len(set(odds.bookmaker for odds in odds_list))

        return features

    async def calculate_all_match_features(
        self, match_entity: MatchEntity, calculation_date: Optional[datetime] = None
    ) -> AllMatchFeatures:
        """
        计算比赛的所有特征

        Args:
            match_entity: 比赛实体
            calculation_date: 计算日期（默认为比赛时间）

        Returns:
            AllMatchFeatures: 完整比赛特征
        """
        if calculation_date is None:
            calculation_date = match_entity.match_time

        async with self.db_manager.get_async_session() as session:
            # 并行计算所有特征
            tasks = [
                self._calculate_recent_performance(
                    session, match_entity.home_team_id, calculation_date
                ),
                self._calculate_recent_performance(
                    session, match_entity.away_team_id, calculation_date
                ),
                self._calculate_historical_matchup(
                    session,
                    match_entity.home_team_id,
                    match_entity.away_team_id,
                    calculation_date,
                ),
                self._calculate_odds_features(
                    session, match_entity.match_id, calculation_date
                ),
            ]

            results = await asyncio.gather(*tasks)

            # 类型转换确保正确的类型匹配
            from typing import cast

            return AllMatchFeatures(
                match_entity=match_entity,
                home_team_recent=cast(RecentPerformanceFeatures, results[0]),
                away_team_recent=cast(RecentPerformanceFeatures, results[1]),
                historical_matchup=cast(HistoricalMatchupFeatures, results[2]),
                odds_features=cast(OddsFeatures, results[3]),
            )

    async def calculate_all_team_features(
        self, team_entity: TeamEntity, calculation_date: Optional[datetime] = None
    ) -> AllTeamFeatures:
        """
        计算球队的所有特征

        Args:
            team_entity: 球队实体
            calculation_date: 计算日期（默认为当前时间）

        Returns:
            AllTeamFeatures: 完整球队特征
        """
        if calculation_date is None:
            calculation_date = datetime.now()

        recent_performance = await self.calculate_recent_performance_features(
            team_entity.team_id, calculation_date
        )

        return AllTeamFeatures(
            team_entity=team_entity, recent_performance=recent_performance
        )

    async def batch_calculate_team_features(
        self, team_ids: List[int], calculation_date: Optional[datetime] = None
    ) -> Dict[int, RecentPerformanceFeatures]:
        """
        批量计算球队特征

        Args:
            team_ids: 球队ID列表
            calculation_date: 计算日期

        Returns:
            Dict[int, RecentPerformanceFeatures]: 球队ID到特征的映射
        """
        if calculation_date is None:
            calculation_date = datetime.now()

        results = {}
        async with self.db_manager.get_async_session() as session:
            tasks = [
                self._calculate_recent_performance(session, team_id, calculation_date)
                for team_id in team_ids
            ]

            features_list = await asyncio.gather(*tasks)

            for team_id, features in zip(team_ids, features_list):
                results[team_id] = features

        return results

    def add_feature(self, feature_def: Dict) -> None:
        """
        添加特征定义

        Args:
            feature_def: 特征定义字典，包含name, type, calculation等字段
        """
        self.features.append(feature_def)

    def calculate_mean(self, data) -> Optional[float]:
        """
        计算均值

        Args:
            data: 数据列表或Series

        Returns:
            均值，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) == 0:
                return None
            return float(statistics.mean(data))
        except (TypeError, ValueError, statistics.StatisticsError):
            return None

    def calculate_std(self, data) -> Optional[float]:
        """
        计算标准差

        Args:
            data: 数据列表或Series

        Returns:
            标准差，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) <= 1:
                return None
            return float(statistics.stdev(data))
        except (TypeError, ValueError, statistics.StatisticsError):
            return None

    def calculate_min(self, data) -> Optional[float]:
        """
        计算最小值

        Args:
            data: 数据列表或Series

        Returns:
            最小值，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) == 0:
                return None
            return float(min(data))
        except (TypeError, ValueError):
            return None

    def calculate_max(self, data) -> Optional[float]:
        """
        计算最大值

        Args:
            data: 数据列表或Series

        Returns:
            最大值，如果数据为空或无效则返回None
        """
        try:
            if data is None or len(data) == 0:
                return None
            return float(max(data))
        except (TypeError, ValueError):
            return None

    def calculate_rolling_mean(self, data, window: int = 3):
        """
        计算滚动均值

        Args:
            data: 数据Series或列表
            window: 窗口大小

        Returns:
            滚动均值Series
        """
        try:
            import pandas as pd

            if hasattr(data, "rolling"):
                # 如果是pandas Series
                return data.rolling(window=window, min_periods=1).mean()
            else:
                # 如果是列表，转换为Series
                series = pd.Series(data)
                return series.rolling(window=window, min_periods=1).mean()
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError):
            import pandas as pd

            return pd.Series([None] * len(data))
