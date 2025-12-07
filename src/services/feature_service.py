"""特征服务.

提供特征计算、存储和管理的高级接口
"""

import logging
from datetime import datetime
from typing import Union

from sqlalchemy.ext.asyncio import AsyncSession

from ..features.engineering import AllMatchFeatures, AllTeamFeatures, FeatureCalculator
from ..core.cache import cached
from ..features.feature_definitions import (
    HistoricalMatchupFeatures,
    OddsFeatures,
    RecentPerformanceFeatures,
)

logger = logging.getLogger(__name__)


class FeatureService:
    """特征服务.

    提供特征计算和管理的高级接口
    """

    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
        self.calculator = FeatureCalculator(db_session)
        self.logger = logger

    @cached(
        ttl=300,  # 5分钟缓存
        namespace="features",
        stampede_protection=True,
        key_builder=lambda self, match_id, calculation_date=None: f"match_features:{match_id}:{calculation_date.isoformat() if calculation_date else 'none'}",
    )
    async def get_match_features(
        self, match_id: int, calculation_date: datetime | None = None
    ) -> AllMatchFeatures | None:
        """获取比赛特征.

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期

        Returns:
            AllMatchFeatures: 比赛完整特征
        """
        try:
            features = await self.calculator.calculate_all_match_features(
                match_id, calculation_date
            )

            if features:
                self.logger.info(
                    f"Successfully calculated features for match {match_id}"
                )
            else:
                self.logger.warning(
                    f"Failed to calculate features for match {match_id}"
                )

            return features

        except Exception as e:
            self.logger.error(f"Error getting match features for {match_id}: {e}")
            return None

    async def get_team_features(
        self, team_id: int, calculation_date: datetime | None = None
    ) -> AllTeamFeatures | None:
        """获取球队特征.

        Args:
            team_id: 球队ID
            calculation_date: 计算日期

        Returns:
            AllTeamFeatures: 球队完整特征
        """
        try:
            features = await self.calculator.calculate_team_features(
                team_id, calculation_date
            )

            if features:
                self.logger.info(f"Successfully calculated features for team {team_id}")
            else:
                self.logger.warning(f"Failed to calculate features for team {team_id}")

            return features

        except Exception as e:
            self.logger.error(f"Error getting team features for {team_id}: {e}")
            return None

    async def batch_get_match_features(
        self, match_ids: list[int], calculation_date: datetime | None = None
    ) -> dict[int, AllMatchFeatures | None]:
        """批量获取比赛特征.

        Args:
            match_ids: 比赛ID列表
            calculation_date: 计算日期

        Returns:
            dict[int, AllMatchFeatures]: 比赛ID到特征的映射
        """
        try:
            features_dict = await self.calculator.batch_calculate_match_features(
                match_ids, calculation_date
            )

            successful_count = sum(1 for f in features_dict.values() if f is not None)
            total_count = len(match_ids)

            self.logger.info(
                f"Batch feature calculation completed: "
                f"{successful_count}/{total_count} matches processed successfully"
            )

            return features_dict

        except Exception as e:
            self.logger.error(f"Error in batch feature calculation: {e}")
            return dict.fromkeys(match_ids)

    async def get_recent_performance_features(
        self, team_id: int, calculation_date: datetime | None = None
    ) -> RecentPerformanceFeatures | None:
        """获取球队近期战绩特征.

        Args:
            team_id: 球队ID
            calculation_date: 计算日期

        Returns:
            RecentPerformanceFeatures: 近期战绩特征
        """
        try:
            if calculation_date is None:
                calculation_date = datetime.now()

            features = await self.calculator.calculate_recent_performance_features(
                team_id, calculation_date
            )

            return features

        except Exception as e:
            self.logger.error(
                f"Error getting recent performance for team {team_id}: {e}"
            )
            return None

    async def get_historical_matchup_features(
        self,
        home_team_id: int,
        away_team_id: int,
        calculation_date: datetime | None = None,
    ) -> HistoricalMatchupFeatures | None:
        """获取历史对战特征.

        Args:
            home_team_id: 主队ID
            away_team_id: 客队ID
            calculation_date: 计算日期

        Returns:
            HistoricalMatchupFeatures: 历史对战特征
        """
        try:
            if calculation_date is None:
                calculation_date = datetime.now()

            features = await self.calculator.calculate_historical_matchup_features(
                home_team_id, away_team_id, calculation_date
            )

            return features

        except Exception as e:
            self.logger.error(
                f"Error getting H2H features for {home_team_id} vs {away_team_id}: {e}"
            )
            return None

    async def get_odds_features(
        self, match_id: int, calculation_date: datetime | None = None
    ) -> OddsFeatures | None:
        """获取赔率特征.

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期

        Returns:
            OddsFeatures: 赔率特征
        """
        try:
            if calculation_date is None:
                calculation_date = datetime.now()

            features = await self.calculator.calculate_odds_features(
                match_id, calculation_date
            )

            return features

        except Exception as e:
            self.logger.error(f"Error getting odds features for match {match_id}: {e}")
            return None

    async def validate_feature_data(self, features: AllMatchFeatures) -> bool:
        """验证特征数据完整性.

        Args:
            features: 比赛特征

        Returns:
            bool: 验证结果
        """
        try:
            # 基础验证
            if not features:
                return False

            # 检查各部分特征是否存在
            required_parts = [
                features.match_entity,
                features.home_team_recent,
                features.away_team_recent,
                features.historical_matchup,
                features.odds_features,
            ]

            if not all(required_parts):
                missing_parts = []
                part_names = [
                    "match_entity",
                    "home_team_recent",
                    "away_team_recent",
                    "historical_matchup",
                    "odds_features",
                ]

                for i, part in enumerate(required_parts):
                    if not part:
                        missing_parts.append(part_names[i])

                self.logger.warning(f"Missing feature parts: {missing_parts}")
                return False

            # 检查数据合理性
            home_recent = features.home_team_recent
            away_recent = features.away_team_recent

            # 检查胜率是否在合理范围内
            if not (0 <= home_recent.recent_5_win_rate <= 1):
                self.logger.warning("Invalid home team win rate")
                return False

            if not (0 <= away_recent.recent_5_win_rate <= 1):
                self.logger.warning("Invalid away team win rate")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating feature data: {e}")
            return False

    async def get_feature_summary(
        self, match_id: int, calculation_date: datetime | None = None
    ) -> dict | None:
        """获取特征摘要信息.

        Args:
            match_id: 比赛ID
            calculation_date: 计算日期

        Returns:
            Dict: 特征摘要
        """
        try:
            features = await self.get_match_features(match_id, calculation_date)

            if not features:
                return None

            summary = {
                "match_id": match_id,
                "calculation_date": (
                    calculation_date.isoformat()
                    if calculation_date
                    else datetime.now().isoformat()
                ),
                "data_quality": {
                    "has_complete_features": await self.validate_feature_data(features),
                    "feature_parts_count": 5,
                    "missing_parts": [],
                },
                "key_metrics": {
                    "home_team_form": features.home_team_recent.recent_5_win_rate,
                    "away_team_form": features.away_team_recent.recent_5_win_rate,
                    "h2h_home_advantage": features.historical_matchup.h2h_home_win_rate,
                    "market_confidence": features.odds_features.bookmaker_consensus,
                },
            }

            # 检查缺失部分
            if not features.match_entity:
                summary["data_quality"]["missing_parts"].append("match_entity")
            if not features.home_team_recent:
                summary["data_quality"]["missing_parts"].append("home_team_recent")
            if not features.away_team_recent:
                summary["data_quality"]["missing_parts"].append("away_team_recent")
            if not features.historical_matchup:
                summary["data_quality"]["missing_parts"].append("historical_matchup")
            if not features.odds_features:
                summary["data_quality"]["missing_parts"].append("odds_features")

            return summary

        except Exception as e:
            self.logger.error(
                f"Error generating feature summary for match {match_id}: {e}"
            )
            return None
