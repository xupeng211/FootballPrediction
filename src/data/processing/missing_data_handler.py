"""
缺失数据处理器

实现处理数据缺失的逻辑，包括填充、插值、删除等策略。

填充策略：
- 球队统计：使用历史平均值
- 球员统计：使用位置中位数
- 天气数据：使用季节正常值
- 赔率数据：使用市场共识

基于 DATA_DESIGN.md 第4.3节设计。
"""

import logging
from typing import Any, Dict, List, Optional

import pandas as pd

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from src.database.connection import DatabaseManager
from src.database.models.features import Features


class MissingDataHandler:
    """
    缺失数据处理器

    提供多种策略来处理数据集中的缺失值，
    确保数据完整性，为模型训练做准备。
    """

    FILL_STRATEGIES = {
        "team_stats": "historical_average",  # 历史平均值
        "player_stats": "position_median",  # 位置中位数
        "weather": "seasonal_normal",  # 季节正常值
        "odds": "market_consensus",  # 市场共识
    }

    def __init__(self):
        """初始化缺失数据处理器"""
        self.db_manager = DatabaseManager()
        self.logger = logging.getLogger(f"handler.{self.__class__.__name__}")
        self._feature_average_cache: Dict[str, float] = {}

    async def handle_missing_match_data(
        self, match_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理比赛数据中的缺失值

        Args:
            match_data: 清洗后的比赛数据

        Returns:
            Dict[str, Any]: 处理缺失值后的数据
        """
        # 示例：填充缺失的比分
        if match_data.get("home_score") is None:
            match_data["home_score"] = 0
            self.logger.debug(
                "Filled missing home_score for match %s",
                match_data.get("external_match_id") or match_data.get("id"),
            )

        if match_data.get("away_score") is None:
            match_data["away_score"] = 0
            self.logger.debug(
                "Filled missing away_score for match %s",
                match_data.get("external_match_id") or match_data.get("id"),
            )

        # 示例：填充缺失的场地和裁判
        if not match_data.get("venue"):
            match_data["venue"] = "Unknown"

        if not match_data.get("referee"):
            match_data["referee"] = "Unknown"

        return match_data

    async def handle_missing_features(
        self, match_id: int, features_df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        处理特征数据中的缺失值

        Args:
            match_id: 比赛ID
            features_df: 特征数据DataFrame

        Returns:
            pd.DataFrame: 处理缺失值后的特征数据
        """
        try:
            # 遍历所有特征列
            for col in features_df.columns:
                if features_df[col].isnull().any():
                    fill_strategy = self.FILL_STRATEGIES.get("team_stats", "zero")

                    if fill_strategy == "historical_average":
                        # 使用历史平均值填充
                        historical_avg = await self._get_historical_average(col)
                        features_df[col].fillna(historical_avg, inplace=True)
                        self.logger.info(
                            f"Filled missing {col} with historical average ({historical_avg})"
                        )

                    elif fill_strategy == "median":
                        # 使用中位数填充
                        median_val = features_df[col].median()
                        features_df[col].fillna(median_val, inplace=True)

                    else:
                        # 默认使用0填充
                        features_df[col].fillna(0, inplace=True)

            return features_df

        except Exception as e:
            self.logger.error(
                f"Failed to handle missing features for match {match_id}: {str(e)}"
            )
            # 出错时返回原始数据
            return features_df

    async def _get_historical_average(self, feature_name: str) -> float:
        """
        获取特征的历史平均值

        Args:
            feature_name: 特征名称

        Returns:
            float: 历史平均值
        """
        if feature_name in self._feature_average_cache:
            return self._feature_average_cache[feature_name]

        column = getattr(Features, feature_name, None)
        if column is None:
            self.logger.warning(
                "Feature column %s does not exist on Features model; using default fallback.",
                feature_name,
            )
            return self._fallback_average(feature_name)

        try:
            async with self.db_manager.get_async_session() as session:
                stmt = select(func.avg(column))
                result = await session.execute(stmt)
                avg_value: Optional[float] = result.scalar()

                if avg_value is None:
                    avg_value = self._fallback_average(feature_name)
                else:
                    avg_value = float(avg_value)

                self._feature_average_cache[feature_name] = avg_value
                return avg_value

        except (RuntimeError, SQLAlchemyError) as exc:
            self.logger.warning(
                "Unable to query historical average for %s, fallback will be used. Error: %s",
                feature_name,
                exc,
            )
            return self._fallback_average(feature_name)

    def _fallback_average(self, feature_name: str) -> float:
        """提供默认平均值作为数据库不可用时的回退策略"""
        default_averages = {
            "avg_possession": 50.0,
            "avg_shots_per_game": 12.5,
            "avg_goals_per_game": 1.5,
            "league_position": 10.0,
        }
        return default_averages.get(feature_name, 0.0)

    def interpolate_time_series_data(self, data: pd.Series) -> pd.Series:
        """
        使用插值法填充时间序列数据

        Args:
            data: 时间序列数据

        Returns:
            pd.Series: 填充后的数据
        """
        try:
            # 使用线性插值
            return data.interpolate(method="linear")
        except Exception as e:
            self.logger.error(f"Failed to interpolate time series data: {str(e)}")
            return data

    def remove_rows_with_missing_critical_data(
        self, df: pd.DataFrame, critical_columns: List[str]
    ) -> pd.DataFrame:
        """
        删除包含关键数据缺失的行

        Args:
            df: 数据集
            critical_columns: 关键列列表

        Returns:
            pd.DataFrame: 清理后的数据集
        """
        try:
            original_rows = len(df)
            cleaned_df = df.dropna(subset=critical_columns)
            removed_rows = original_rows - len(cleaned_df)

            if removed_rows > 0:
                self.logger.warning(
                    f"Removed {removed_rows} rows due to missing critical data in columns: {critical_columns}"
                )

            return cleaned_df

        except Exception as e:
            self.logger.error(f"Failed to remove rows with missing data: {str(e)}")
            return df
