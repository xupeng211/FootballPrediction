"""
数据处理器
Data Handlers

提供特殊数据的处理功能。
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

from src.core.logging import get_logger
from src.data.processing.missing_data_handler import MissingDataHandler

logger = get_logger(__name__)


class MissingDataHandler:
    """
    缺失数据处理器 / Missing Data Handler

    处理数据集中的缺失值。
    Handles missing values in datasets.
    """

    def __init__(self):
        """初始化处理器 / Initialize handler"""
        self.logger = get_logger(f"{__name__}.MissingDataHandler")
        self.handler = MissingDataHandler()

    async def handle_missing_data(
        self, data: pd.DataFrame, strategy: str = "auto"
    ) -> Optional[pd.DataFrame]:
        """
        处理缺失数据 / Handle Missing Data

        Args:
            data: 包含缺失值的数据框 / DataFrame with missing values
            strategy: 处理策略 / Processing strategy

        Returns:
            处理后的数据框 / Processed DataFrame
        """
        try:
            # 分析缺失模式
            missing_analysis = self._analyze_missing_data(data)
            self.logger.info(f"缺失数据分析: {missing_analysis}")

            # 根据策略处理
            if strategy == "auto":
                strategy = self._select_best_strategy(missing_analysis)

            # 执行处理
            if strategy == "drop":
                data = self._drop_missing(data, missing_analysis)
            elif strategy == "fill":
                data = self._fill_missing(data, missing_analysis)
            elif strategy == "interpolate":
                data = self._interpolate_missing(data, missing_analysis)

            self.logger.info(f"使用 {strategy} 策略处理缺失数据完成")
            return data

        except Exception as e:
            self.logger.error(f"处理缺失数据失败: {e}")
            return None

    def _analyze_missing_data(self, data: pd.DataFrame) -> Dict[str, Any]:
        """分析缺失数据模式 / Analyze Missing Data Pattern"""
        analysis = {
            "total_missing": data.isnull().sum().sum(),
            "missing_by_column": data.isnull().sum().to_dict(),
            "missing_percentage": (data.isnull().sum() / len(data) * 100).to_dict(),
            "complete_rows": len(data.dropna()),
            "total_rows": len(data),
        }

        return analysis

    def _select_best_strategy(self, analysis: Dict[str, Any]) -> str:
        """选择最佳处理策略 / Select Best Strategy"""
        total_rows = analysis["total_rows"]
        complete_rows = analysis["complete_rows"]

        # 如果完整行太少，考虑删除
        if complete_rows / total_rows < 0.5:
            return "fill"

        # 检查缺失率
        max_missing_pct = max(analysis["missing_percentage"].values())
        if max_missing_pct > 80:
            return "drop"
        elif max_missing_pct > 30:
            return "interpolate"
        else:
            return "fill"

    def _drop_missing(
        self, data: pd.DataFrame, analysis: Dict[str, Any]
    ) -> pd.DataFrame:
        """删除缺失数据 / Drop Missing Data"""
        # 删除缺失率过高的列
        threshold = 0.5
        columns_to_drop = []
        for col, pct in analysis["missing_percentage"].items():
            if pct > threshold * 100:
                columns_to_drop.append(col)

        if columns_to_drop:
            data = data.drop(columns=columns_to_drop)
            self.logger.info(f"删除了 {len(columns_to_drop)} 个高缺失率列")

        # 删除缺失的行
        data = data.dropna()
        self.logger.info(f"删除了缺失行后剩余 {len(data)} 条记录")

        return data

    def _fill_missing(
        self, data: pd.DataFrame, analysis: Dict[str, Any]
    ) -> pd.DataFrame:
        """填充缺失数据 / Fill Missing Data"""
        # 数值列用中位数填充
        numeric_columns = data.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if (
                col in analysis["missing_by_column"]
                and analysis["missing_by_column"][col] > 0
            ):
                median_value = data[col].median()
                data[col] = data[col].fillna(median_value)
                self.logger.debug(f"列 {col} 用中位数 {median_value:.2f} 填充")

        # 分类列用众数填充
        categorical_columns = data.select_dtypes(include=["object"]).columns
        for col in categorical_columns:
            if (
                col in analysis["missing_by_column"]
                and analysis["missing_by_column"][col] > 0
            ):
                mode_value = data[col].mode().iloc[0]
                data[col] = data[col].fillna(mode_value)
                self.logger.debug(f"列 {col} 用众数 {mode_value} 填充")

        return data

    def _interpolate_missing(
        self, data: pd.DataFrame, analysis: Dict[str, Any]
    ) -> pd.DataFrame:
        """插值填充缺失数据 / Interpolate Missing Data"""
        # 适用于时间序列数据
        for col in data.select_dtypes(include=[np.number]).columns:
            if (
                col in analysis["missing_by_column"]
                and analysis["missing_by_column"][col] > 0
            ):
                data[col] = data[col].interpolate(method="linear")
                self.logger.debug(f"列 {col} 使用线性插值填充")

        return data


class MissingScoresHandler:
    """
    缺失比分处理器 / Missing Scores Handler

    处理缺失的比赛比分数据。
    Handles missing match scores data.
    """

    def __init__(self):
        """初始化处理器 / Initialize handler"""
        self.logger = get_logger(f"{__name__}.MissingScoresHandler")

    async def handle_missing_scores(self, data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """
        处理缺失比分 / Handle Missing Scores

        Args:
            data: 包含缺失比分的数据框 / DataFrame with missing scores

        Returns:
            处理后的数据框 / Processed DataFrame
        """
        try:
            # 检查比分列
            if "home_score" not in data.columns or "away_score" not in data.columns:
                self.logger.warning("数据框中缺少比分列")
                return data

            # 识别缺失比分的记录
            missing_mask = data["home_score"].isnull() | data["away_score"].isnull()
            missing_count = missing_mask.sum()

            if missing_count == 0:
                self.logger.info("没有缺失的比分数据")
                return data

            self.logger.info(f"发现 {missing_count} 条缺失比分的记录")

            # 尝试从其他信息推断比分
            data = self._infer_scores_from_other_data(data, missing_mask)

            # 如果仍然有缺失，使用默认值
            still_missing = data["home_score"].isnull() | data["away_score"].isnull()
            if still_missing.sum() > 0:
                data = self._fill_scores_with_defaults(data, still_missing)

            self.logger.info("缺失比分处理完成")
            return data

        except Exception as e:
            self.logger.error(f"处理缺失比分失败: {e}")
            return None

    def _infer_scores_from_other_data(
        self, data: pd.DataFrame, missing_mask: pd.Series
    ) -> pd.DataFrame:
        """从其他数据推断比分 / Infer Scores from Other Data"""
        # 检查是否有半场比分可用于推断
        if "home_ht_score" in data.columns and "away_ht_score" in data.columns:
            # 使用半场比分作为全场比分的参考
            ht_complete = (
                data.loc[missing_mask, "home_ht_score"].notna()
                & data.loc[missing_mask, "away_ht_score"].notna()
            )

            if ht_complete.sum() > 0:
                # 简单策略：半场比分可能接近最终比分
                data.loc[missing_mask & ht_complete, "home_score"] = data.loc[
                    missing_mask & ht_complete, "home_ht_score"
                ]
                data.loc[missing_mask & ht_complete, "away_score"] = data.loc[
                    missing_mask & ht_complete, "away_ht_score"
                ]

                self.logger.info(f"使用半场比分推断 {ht_complete.sum()} 条记录")

        return data

    def _fill_scores_with_defaults(
        self, data: pd.DataFrame, missing_mask: pd.Series
    ) -> pd.DataFrame:
        """使用默认值填充比分 / Fill Scores with Defaults"""
        # 使用平均值作为默认值
        mean_home_score = data["home_score"].mean()
        mean_away_score = data["away_score"].mean()

        if pd.isna(mean_home_score):
            mean_home_score = 1.0
        if pd.isna(mean_away_score):
            mean_away_score = 1.0

        data.loc[missing_mask, "home_score"] = mean_home_score
        data.loc[missing_mask, "away_score"] = mean_away_score

        self.logger.info(f"使用默认值填充 {missing_mask.sum()} 条记录")

        return data


class MissingTeamDataHandler:
    """
    缺失队伍数据处理器 / Missing Team Data Handler

    处理缺失的队伍数据。
    Handles missing team data.
    """

    def __init__(self):
        """初始化处理器 / Initialize handler"""
        self.logger = get_logger(f"{__name__}.MissingTeamDataHandler")

    async def handle_missing_team_data(
        self, data: pd.DataFrame, team_type: str = "both"
    ) -> Optional[pd.DataFrame]:
        """
        处理缺失队伍数据 / Handle Missing Team Data

        Args:
            data: 包含缺失队伍数据的数据框 / DataFrame with missing team data
            team_type: 队伍类型（home/away/both） / Team type

        Returns:
            处理后的数据框 / Processed DataFrame
        """
        try:
            processed_count = 0

            # 处理主队数据
            if team_type in ["home", "both"]:
                if "home_team_id" in data.columns:
                    missing_home = data["home_team_id"].isnull()
                    if missing_home.sum() > 0:
                        data = self._fill_missing_team_data(data, "home")
                        processed_count += missing_home.sum()

            # 处理客队数据
            if team_type in ["away", "both"]:
                if "away_team_id" in data.columns:
                    missing_away = data["away_team_id"].isnull()
                    if missing_away.sum() > 0:
                        data = self._fill_missing_team_data(data, "away")
                        processed_count += missing_away.sum()

            self.logger.info(f"处理了 {processed_count} 条缺失队伍数据")
            return data

        except Exception as e:
            self.logger.error(f"处理缺失队伍数据失败: {e}")
            return None

    def _fill_missing_team_data(
        self, data: pd.DataFrame, team_type: str
    ) -> pd.DataFrame:
        """填充缺失队伍数据 / Fill Missing Team Data"""
        team_id_col = f"{team_type}_team_id"
        team_name_col = f"{team_type}_team_name"

        # 尝试从队名推断队伍ID
        if team_name_col in data.columns:
            missing_mask = data[team_id_col].isnull() & data[team_name_col].notnull()

            if missing_mask.sum() > 0:
                # 创建队名到ID的映射
                team_mapping = {}
                complete_data = data[
                    data[team_id_col].notna() & data[team_name_col].notna()
                ]

                for _, row in complete_data.iterrows():
                    team_mapping[row[team_name_col]] = row[team_id_col]

                # 使用映射填充
                for idx in data[missing_mask].index:
                    team_name = data.loc[idx, team_name_col]
                    if team_name in team_mapping:
                        data.loc[idx, team_id_col] = team_mapping[team_name]

                filled_count = data[team_id_col].isnull().sum() - missing_mask.sum()
                self.logger.info(f"通过队名填充了 {-filled_count} 个{team_type}队ID")

        # 如果仍然有缺失，使用默认值
        still_missing = data[team_id_col].isnull()
        if still_missing.sum() > 0:
            default_id = 0  # 使用0作为默认队ID
            data.loc[still_missing, team_id_col] = default_id
            self.logger.info(f"使用默认ID填充了 {still_missing.sum()} 个{team_type}队")

        return data
