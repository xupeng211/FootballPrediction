# mypy: ignore-errors
"""
特征计算器核心模块

定义基础的特征计算器类和通用接口。
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..feature_definitions import (
    AllMatchFeatures,
    AllTeamFeatures,
)
from ..entities import MatchEntity, TeamEntity
from .recent_performance import RecentPerformanceCalculator
from .historical_matchup import HistoricalMatchupCalculator
from .odds_features import OddsFeaturesCalculator
from .batch_calculator import BatchCalculator


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
        from ...database.connection import DatabaseManager

        self.db_manager = DatabaseManager()
        self.config = config or {}
        self.features: list = []  # 存储特征定义

        # 初始化子计算器
        self.recent_calculator = RecentPerformanceCalculator(self.db_manager)
        self.historical_calculator = HistoricalMatchupCalculator(self.db_manager)
        self.odds_calculator = OddsFeaturesCalculator(self.db_manager)
        self.batch_calculator = BatchCalculator(self.db_manager)

    async def calculate_recent_performance_features(
        self,
        team_id: int,
        calculation_date: datetime,
        session: Optional[Any] = None,
    ):
        """计算球队近期战绩特征"""
        return await self.recent_calculator.calculate(
            team_id, calculation_date, session
        )

    async def calculate_historical_matchup_features(
        self,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime,
        session: Optional[Any] = None,
    ):
        """计算历史对战特征"""
        return await self.historical_calculator.calculate(
            home_team_id, away_team_id, calculation_date, session
        )

    async def calculate_odds_features(
        self,
        match_id: int,
        calculation_date: datetime,
        session: Optional[Any] = None,
    ):
        """计算赔率特征"""
        return await self.odds_calculator.calculate(match_id, calculation_date, session)

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
                self.recent_calculator._calculate_recent_performance(
                    session, match_entity.home_team_id, calculation_date
                ),
                self.recent_calculator._calculate_recent_performance(
                    session, match_entity.away_team_id, calculation_date
                ),
                self.historical_calculator._calculate_historical_matchup(
                    session,
                    match_entity.home_team_id,
                    match_entity.away_team_id,
                    calculation_date,
                ),
                self.odds_calculator._calculate_odds_features(
                    session, match_entity.match_id, calculation_date
                ),
            ]

            results = await asyncio.gather(*tasks)

            # 类型转换确保正确的类型匹配
            from typing import cast
            from ..feature_definitions import (
                RecentPerformanceFeatures,
                HistoricalMatchupFeatures,
                OddsFeatures,
            )

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
    ) -> Dict[int, Any]:
        """
        批量计算球队特征

        Args:
            team_ids: 球队ID列表
            calculation_date: 计算日期

        Returns:
            Dict[int, RecentPerformanceFeatures]: 球队ID到特征的映射
        """
        return await self.batch_calculator.calculate_team_features(
            team_ids, calculation_date
        )

    def add_feature(self, feature_def: Dict) -> None:
        """
        添加特征定义

        Args:
            feature_def: 特征定义字典，包含name, type, calculation等字段
        """
        self.features.append(feature_def)

    def get_supported_features(self) -> List[Dict]:
        """
        获取支持的特征列表

        Returns:
            List[Dict]: 特征定义列表
        """
        return self.features.copy()
