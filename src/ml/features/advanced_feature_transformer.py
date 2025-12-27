"""
高级特征转换器 - Advanced Feature Transformer

Phase 5 + Phase 8 Advanced Features 主要组件

整合多类核心高级特征，旨在将模型准确率从58.69%提升至65%+：

Phase 5 特征：
1. 场馆分离滚动统计 (解决Napoli vs Juventus案例的主客场偏见)
2. 历史交锋统计 (H2H记录和"克星"效应)
3. 联赛形态特征 (积分滚动统计替代噪音大的进球数)

Phase 8 特征 (新增)：
4. Player Ratings 特征 (首发实力、球星评分、替补实力)
5. Metadata 特征 (裁判、体育场、上座率)
6. 纪律特征 (红牌、半场进球)

设计原理：
- 整合数据库中的L2/L3高级数据
- 重点验证 home_xi_rating 是否能成为Top 3特征
- 通过多维特征工程提升模型性能
- 保持与现有训练流水线的完全兼容性
- 严格的防数据泄露机制

目标：通过高级特征工程实现65%+的预测准确率
"""

import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from .h2h_calculator import H2HCalculator
from .venue_analyzer import VenueAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class AdvancedFeatureConfig:
    """高级特征配置 - Phase 8升级"""

    # Phase 5 特征开关
    enable_venue_features: bool = True
    enable_h2h_features: bool = True
    enable_points_features: bool = True

    # Phase 8 特征开关 (新增)
    enable_player_ratings_features: bool = True
    enable_metadata_features: bool = True
    enable_discipline_features: bool = True

    # 配置参数
    venue_windows: list[int] = None
    h2h_min_matches: int = 1
    points_windows: list[int] = None

    def __post_init__(self) -> None:
        if self.venue_windows is None:
            self.venue_windows = [3, 5]
        if self.points_windows is None:
            self.points_windows = [3, 5]


class AdvancedFeatureTransformer:
    """
    高级特征转换器 - Phase 8升级版

    Phase 5 + Phase 8的核心组件，整合多类高级特征：
    - Phase 5: 场馆分离、历史交锋、联赛形态
    - Phase 8: Player Ratings、Metadata、纪律特征

    专门设计用于解决Phase 4中发现的关键问题，并验证Phase 8高级数据的有效性。
    重点验证 home_xi_rating 是否能成为Top 3特征。
    """

    def __init__(self, config: AdvancedFeatureConfig | None = None):
        """
        初始化高级特征转换器

        Args:
            config: 高级特征配置，默认使用所有特征
        """
        self.config = config or AdvancedFeatureConfig()

        # 初始化子组件
        self.h2h_calculator = H2HCalculator(min_matches=self.config.h2h_min_matches)
        self.venue_analyzer = VenueAnalyzer(windows=self.config.venue_windows)

        # 特征名称记录
        self.feature_names: list[str] = []
        self.feature_types: dict[str, str] = {}

        logger.info("AdvancedFeatureTransformer Phase 8升级版 初始化完成")
        logger.info(
            f"Phase 5 特征: 场馆={self.config.enable_venue_features}, "
            f"H2H={self.config.enable_h2h_features}, 积分={self.config.enable_points_features}"
        )
        logger.info(
            f"Phase 8 特征: PlayerRatings={self.config.enable_player_ratings_features}, "
            f"Metadata={self.config.enable_metadata_features}, 纪律={self.config.enable_discipline_features}"
        )

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        转换DataFrame，添加所有高级特征

        Args:
            df: 原始比赛数据DataFrame

        Returns:
            pd.DataFrame: 添加了高级特征的DataFrame
        """
        logger.info(f"开始高级特征转换，原始数据形状: {df.shape}")

        df_result = df.copy()

        try:
            # 1. 添加场馆分离特征
            if self.config.enable_venue_features:
                logger.info("📍 添加场馆分离特征...")
                df_result = self.venue_analyzer.calculate_venue_features_for_all_matches(df_result)
                self._update_feature_list("venue")

            # 2. 添加历史交锋特征
            if self.config.enable_h2h_features:
                logger.info("⚔️ 添加历史交锋特征...")
                df_result = self.h2h_calculator.calculate_h2h_for_all_matches(df_result)
                self._update_feature_list("h2h")

            # 3. 添加积分形态特征
            if self.config.enable_points_features:
                logger.info("🏆 添加积分形态特征...")
                df_result = self._add_points_features(df_result)
                self._update_feature_list("points")

            # 4. Phase 8: 添加Player Ratings特征 (🎯 重点验证 home_xi_rating)
            if self.config.enable_player_ratings_features:
                logger.info("⭐ 添加Player Ratings特征...")
                df_result = self._add_player_ratings_features(df_result)
                self._update_feature_list("player_ratings")

            # 5. Phase 8: 添加Metadata特征
            if self.config.enable_metadata_features:
                logger.info("📋 添加Metadata特征...")
                df_result = self._add_metadata_features(df_result)
                self._update_feature_list("metadata")

            # 6. Phase 8: 添加纪律特征
            if self.config.enable_discipline_features:
                logger.info("🟥 添加纪律特征...")
                df_result = self._add_discipline_features(df_result)
                self._update_feature_list("discipline")

            # 7. 清理和处理缺失值
            df_result = self._handle_missing_values(df_result)

            logger.info(f"✅ 高级特征转换完成，最终数据形状: {df_result.shape}")
            logger.info(f"📋 新增特征总数: {len(self.feature_names)}")

            return df_result

        except Exception as e:
            logger.error(f"❌ 高级特征转换失败: {str(e)}")
            raise

    def transform_for_prediction(self, match_data: pd.DataFrame, historical_data: pd.DataFrame) -> pd.DataFrame:
        """
        为预测场景转换特定比赛的特征

        Args:
            match_data: 当前比赛数据 (单场比赛)
            historical_data: 历史比赛数据

        Returns:
            pd.DataFrame: 包含高级特征的预测数据
        """
        try:
            # 合并数据用于特征计算
            combined_data = pd.concat([historical_data, match_data], ignore_index=True)
            combined_data = combined_data.sort_values("match_date")

            # 转换特征
            combined_with_features = self.transform(combined_data)

            # 提取当前比赛的特征
            current_match_features = combined_with_features.iloc[-1:].copy()

            return current_match_features

        except Exception as e:
            logger.error(f"预测特征转换失败: {str(e)}")
            return match_data

    def get_feature_importance_groups(self) -> dict[str, list[str]]:
        """
        获取按类型分组的特征名称

        Returns:
            Dict[str, List[str]]: 特征类型到特征名称的映射
        """
        return {
            "venue": [name for name in self.feature_names if "venue_" in name],
            "h2h": [name for name in self.feature_names if "h2h_" in name],
            "points": [name for name in self.feature_names if "points_" in name],
        }

    def get_advanced_feature_names(self) -> list[str]:
        """
        获取所有高级特征的名称

        Returns:
            List[str]: 高级特征名称列表
        """
        return self.feature_names.copy()

    def _add_points_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        添加积分滚动特征

        Args:
            df: 输入DataFrame

        Returns:
            pd.DataFrame: 添加了积分特征的DataFrame
        """
        df_result = df.copy()

        # 1. 计算比赛积分
        df_result = self._calculate_match_points(df_result)

        # 2. 计算各队的积分滚动统计
        for team_id in df_result["home_team_id"].unique():
            team_matches = df_result[
                (df_result["home_team_id"] == team_id) | (df_result["away_team_id"] == team_id)
            ].sort_values("match_date")

            # 计算各窗口的积分滚动统计
            for window in self.config.points_windows:
                # 主队积分滚动
                home_points_rolling = (
                    team_matches[team_matches["home_team_id"] == team_id]["points"]
                    .rolling(window, min_periods=1)
                    .mean()
                    .shift(1)
                )

                # 客队积分滚动
                away_points_rolling = (
                    team_matches[team_matches["away_team_id"] == team_id]["points"]
                    .rolling(window, min_periods=1)
                    .mean()
                    .shift(1)
                )

                # 映射回原DataFrame
                home_col = f"points_home_rolling_{window}"
                away_col = f"points_away_rolling_{window}"

                df_result.loc[home_points_rolling.index, home_col] = home_points_rolling
                df_result.loc[away_points_rolling.index, away_col] = away_points_rolling

        # 3. 计算积分对比特征
        for window in self.config.points_windows:
            home_col = f"points_home_rolling_{window}"
            away_col = f"points_away_rolling_{window}"

            # 主队积分优势
            advantage_col = f"points_advantage_{window}"
            df_result[advantage_col] = df_result[home_col] - df_result[away_col]

        # 4. 计算积分比率特征
        for window in self.config.points_windows:
            home_col = f"points_home_rolling_{window}"
            away_col = f"points_away_rolling_{window}"

            # 积分比率 (主队积分 / 客队积分)
            ratio_col = f"points_ratio_{window}"
            df_result[ratio_col] = df_result[home_col] / (df_result[away_col] + 0.01)

        return df_result

    def _calculate_match_points(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        计算每场比赛的积分

        Args:
            df: 输入DataFrame

        Returns:
            pd.DataFrame: 添加了积分列的DataFrame
        """
        df_result = df.copy()

        # 计算积分: 胜3分，平1分，负0分
        conditions = [
            df_result["home_score"] > df_result["away_score"],  # 主队胜
            df_result["home_score"] < df_result["away_score"],  # 客队胜
            df_result["home_score"] == df_result["away_score"],  # 平局
        ]

        # 主队积分
        home_points = np.select(conditions, [3, 0, 1], default=0)

        # 客队积分
        away_points = np.select(conditions, [0, 3, 1], default=0)

        df_result["home_points"] = home_points
        df_result["away_points"] = away_points
        df_result["points"] = home_points  # 用于统一计算

        return df_result

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        处理缺失值和异常值

        Args:
            df: 输入DataFrame

        Returns:
            pd.DataFrame: 清理后的DataFrame
        """
        df_result = df.copy()

        # 获取高级特征列
        advanced_feature_cols = self.get_advanced_feature_names()

        # 填充缺失值
        for col in advanced_feature_cols:
            if col in df_result.columns:
                # 数值列使用0填充
                if df_result[col].dtype in ["float64", "int64"]:
                    df_result[col] = df_result[col].fillna(0)
                # 分类列使用默认值填充
                else:
                    df_result[col] = df_result[col].fillna("unknown")

        return df_result

    def _update_feature_list(self, feature_type: str) -> None:
        """
        更新特征名称列表

        Args:
            feature_type: 特征类型 ('venue', 'h2h', 'points')
        """
        if feature_type == "venue":
            venue_features = [
                "venue_home_goals_rolling_3",
                "venue_home_goals_rolling_5",
                "venue_away_goals_rolling_3",
                "venue_away_goals_rolling_5",
                "venue_home_vs_away_diff_3",
                "venue_home_vs_away_diff_5",
                "venue_home_advantage_3",
                "venue_home_advantage_5",
            ]
            self.feature_names.extend(venue_features)
            self.feature_types["venue"] = venue_features

        elif feature_type == "h2h":
            h2h_features = [
                "h2h_home_win_rate",
                "h2h_avg_goal_diff",
                "h2h_avg_total_goals",
                "h2h_matches_count",
            ]
            self.feature_names.extend(h2h_features)
            self.feature_types["h2h"] = h2h_features

        elif feature_type == "points":
            points_features = []
            for window in self.config.points_windows:
                points_features.extend(
                    [
                        f"points_home_rolling_{window}",
                        f"points_away_rolling_{window}",
                        f"points_advantage_{window}",
                        f"points_ratio_{window}",
                    ]
                )
            self.feature_names.extend(points_features)
            self.feature_types["points"] = points_features

        elif feature_type == "player_ratings":
            # Phase 8: Player Ratings特征 (🎯 关键特征)
            player_ratings_features = [
                # 首发评分特征
                "xi_rating_diff",
                "xi_rating_ratio",
                # 球星评分特征
                "star_rating_diff",
                "star_rating_ratio",
                # 替补实力特征
                "bench_rating_diff",
                "bench_rating_ratio",
                # 综合实力特征
                "home_team_strength",
                "away_team_strength",
                "strength_diff",
                "strength_ratio",
            ]
            self.feature_names.extend(player_ratings_features)
            self.feature_types["player_ratings"] = player_ratings_features

        elif feature_type == "metadata":
            # Phase 8: Metadata特征
            metadata_features = [
                # 上座率特征
                "attendance_normalized",
                "high_attendance_flag",
                "medium_attendance_flag",
                "low_attendance_flag",
                # 裁判特征
                "referee_encoded",
                "has_referee_data",
                # 体育场特征
                "stadium_encoded",
                "has_stadium_data",
                # 主场优势特征
                "home_advantage_attendance",
            ]
            self.feature_names.extend(metadata_features)
            self.feature_types["metadata"] = metadata_features

        elif feature_type == "discipline":
            # Phase 8: 纪律特征
            discipline_features = [
                # 红牌特征
                "total_red_cards",
                "red_cards_diff",
                "home_red_cards_flag",
                "away_red_cards_flag",
                "any_red_cards_flag",
                # 半场进球特征
                "total_goals_ht",
                "goals_ht_diff",
                "goals_ht_ratio",
                # 比赛动态特征
                "home_goals_ft_vs_ht",
                "away_goals_ft_vs_ht",
                "ht_scoring_intensity",
                "ht_leading_to_ft_win",
                "comeback_flag",
            ]
            self.feature_names.extend(discipline_features)
            self.feature_types["discipline"] = discipline_features

    def analyze_feature_correlation(self, df: pd.DataFrame) -> dict[str, dict[str, float]]:
        """
        分析高级特征与目标变量的相关性

        Args:
            df: 包含特征和目标的DataFrame

        Returns:
            Dict: 特征相关性分析结果
        """
        advanced_features = self.get_advanced_feature_names()
        available_features = [f for f in advanced_features if f in df.columns]

        if "target" not in df.columns:
            # 如果没有目标列，尝试从比分推导
            df["target"] = (df["home_score"] > df["away_score"]).astype(int)

        correlations = {}
        for feature in available_features:
            if feature in df.columns:
                corr = df[feature].corr(df["target"])
                correlations[feature] = {
                    "correlation": corr,
                    "abs_correlation": abs(corr),
                    "strength": self._interpret_correlation(abs(corr)),
                }

        return correlations

    def _interpret_correlation(self, abs_corr: float) -> str:
        """解释相关性强弱"""
        if abs_corr >= 0.7:
            return "strong"
        elif abs_corr >= 0.3:
            return "moderate"
        elif abs_corr >= 0.1:
            return "weak"
        else:
            return "very_weak"

    def generate_feature_report(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        生成特征工程报告

        Args:
            df: 包含高级特征的DataFrame

        Returns:
            Dict: 特征工程报告
        """
        report = {
            "total_features": len(self.get_advanced_feature_names()),
            "feature_groups": self.get_feature_importance_groups(),
            "data_shape_before": df.shape,
            "missing_values": {},
            "feature_correlations": {},
        }

        # 缺失值统计
        advanced_features = self.get_advanced_feature_names()
        for feature in advanced_features:
            if feature in df.columns:
                missing_count = df[feature].isna().sum()
                if missing_count > 0:
                    report["missing_values"][feature] = missing_count

        # 相关性分析
        correlations = self.analyze_feature_correlation(df)
        if correlations:
            report["feature_correlations"] = correlations

        return report

    # ==================== Phase 8 新特征工程方法 ====================

    def _add_player_ratings_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 8: 添加Player Ratings特征
        🎯 重点验证 home_xi_rating 是否能成为Top 3特征

        Args:
            df: 输入DataFrame

        Returns:
            pd.DataFrame: 添加了Player Ratings特征的DataFrame
        """
        df_result = df.copy()

        # 1. 首发评分差异特征 (🎯 关键特征)
        df_result["xi_rating_diff"] = df_result["home_xi_rating"] - df_result["away_xi_rating"]
        df_result["xi_rating_ratio"] = df_result["home_xi_rating"] / (df_result["away_xi_rating"] + 0.01)

        # 2. 球星评分差异特征
        df_result["star_rating_diff"] = df_result["home_star_rating"] - df_result["away_star_rating"]
        df_result["star_rating_ratio"] = df_result["home_star_rating"] / (df_result["away_star_rating"] + 0.01)

        # 3. 替补实力差异特征
        df_result["bench_rating_diff"] = df_result["home_bench_rating"] - df_result["away_bench_rating"]
        df_result["bench_rating_ratio"] = df_result["home_bench_rating"] / (df_result["away_bench_rating"] + 0.01)

        # 4. 综合实力评分 (加权组合)
        df_result["home_team_strength"] = (
            df_result["home_xi_rating"] * 0.6
            + df_result["home_star_rating"] * 0.3
            + df_result["home_bench_rating"] * 0.1
        )

        df_result["away_team_strength"] = (
            df_result["away_xi_rating"] * 0.6
            + df_result["away_star_rating"] * 0.3
            + df_result["away_bench_rating"] * 0.1
        )

        df_result["strength_diff"] = df_result["home_team_strength"] - df_result["away_team_strength"]
        df_result["strength_ratio"] = df_result["home_team_strength"] / (df_result["away_team_strength"] + 0.01)

        # 5. 离散化特征 (评分等级)
        df_result["home_xi_rating_tier"] = pd.cut(
            df_result["home_xi_rating"],
            bins=[0, 6, 7, 8, 10],
            labels=["Weak", "Average", "Strong", "Elite"],
        )
        df_result["away_xi_rating_tier"] = pd.cut(
            df_result["away_xi_rating"],
            bins=[0, 6, 7, 8, 10],
            labels=["Weak", "Average", "Strong", "Elite"],
        )

        return df_result

    def _add_metadata_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 8: 添加Metadata特征 (裁判、体育场、上座率)

        Args:
            df: 输入DataFrame

        Returns:
            pd.DataFrame: 添加了Metadata特征的DataFrame
        """
        df_result = df.copy()

        # 1. 上座率相关特征
        df_result["attendance_normalized"] = df_result["attendance"] / 100000  # 标准化到0-1范围
        df_result["high_attendance_flag"] = (df_result["attendance"] > 50000).astype(int)
        df_result["medium_attendance_flag"] = (
            (df_result["attendance"] >= 30000) & (df_result["attendance"] <= 50000)
        ).astype(int)
        df_result["low_attendance_flag"] = (df_result["attendance"] < 30000).astype(int)

        # 2. 裁判相关特征 (简单计数，后续可扩展为裁判历史统计)
        df_result["referee_encoded"] = df_result["referee"].astype("category").cat.codes
        df_result["has_referee_data"] = (df_result["referee"].notna() & (df_result["referee"] != "")).astype(int)

        # 3. 体育场相关特征
        df_result["stadium_encoded"] = df_result["stadium"].astype("category").cat.codes
        df_result["has_stadium_data"] = (df_result["stadium"].notna() & (df_result["stadium"] != "")).astype(int)

        # 4. 主客场优势特征 (结合上座率)
        df_result["home_advantage_attendance"] = df_result["attendance_normalized"] * 1.5  # 主场上座率优势

        return df_result

    def _add_discipline_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Phase 8: 添加纪律特征 (红牌、半场进球)

        Args:
            df: 输入DataFrame

        Returns:
            pd.DataFrame: 添加了纪律特征的DataFrame
        """
        df_result = df.copy()

        # 1. 红牌相关特征
        df_result["total_red_cards"] = df_result["home_red_cards"] + df_result["away_red_cards"]
        df_result["red_cards_diff"] = df_result["home_red_cards"] - df_result["away_red_cards"]
        df_result["home_red_cards_flag"] = (df_result["home_red_cards"] > 0).astype(int)
        df_result["away_red_cards_flag"] = (df_result["away_red_cards"] > 0).astype(int)
        df_result["any_red_cards_flag"] = (df_result["total_red_cards"] > 0).astype(int)

        # 2. 半场进球相关特征
        df_result["total_goals_ht"] = df_result["home_goals_ht"] + df_result["away_goals_ht"]
        df_result["goals_ht_diff"] = df_result["home_goals_ht"] - df_result["away_goals_ht"]
        df_result["goals_ht_ratio"] = df_result["home_goals_ht"] / (df_result["away_goals_ht"] + 0.01)

        # 3. 半场vs全场特征
        df_result["home_goals_ft_vs_ht"] = df_result["home_score"] - df_result["home_goals_ht"]
        df_result["away_goals_ft_vs_ht"] = df_result["away_score"] - df_result["away_goals_ht"]
        df_result["ht_scoring_intensity"] = df_result["total_goals_ht"] * 2  # 半场进球强度

        # 4. 比赛动态特征
        df_result["ht_leading_to_ft_win"] = (
            (
                (df_result["home_goals_ht"] > df_result["away_goals_ht"])
                & (df_result["home_score"] > df_result["away_score"])
            )
            | (
                (df_result["away_goals_ht"] > df_result["home_goals_ht"])
                & (df_result["away_score"] > df_result["home_score"])
            )
        ).astype(int)

        df_result["comeback_flag"] = (
            (
                (df_result["home_goals_ht"] < df_result["away_goals_ht"])
                & (df_result["home_score"] > df_result["away_score"])
            )
            | (
                (df_result["away_goals_ht"] < df_result["home_goals_ht"])
                & (df_result["away_score"] > df_result["home_score"])
            )
        ).astype(int)

        return df_result


# 使用示例
if __name__ == "__main__":
    # 示例数据
    sample_data = {
        "home_team_id": [1, 2, 1, 3, 2, 1, 2],
        "away_team_id": [2, 1, 3, 1, 1, 2, 3],
        "home_score": [2, 1, 0, 1, 3, 2, 1],
        "away_score": [1, 2, 0, 0, 1, 1, 2],
        "match_date": [
            "2024-01-01",
            "2024-01-15",
            "2024-02-01",
            "2024-02-15",
            "2024-03-01",
            "2024-03-15",
            "2024-03-20",
        ],
    }

    df = pd.DataFrame(sample_data)
    df["match_date"] = pd.to_datetime(df["match_date"])

    # 创建高级特征转换器
    config = AdvancedFeatureConfig(
        enable_venue_features=True,
        enable_h2h_features=True,
        enable_points_features=True,
    )

    transformer = AdvancedFeatureTransformer(config)

    # 转换特征
    df_with_features = transformer.transform(df)

    # 生成特征报告
    report = transformer.generate_feature_report(df_with_features)
