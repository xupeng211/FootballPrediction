"""
场馆分析器 - Venue Analyzer

Phase 5 Advanced Features 核心组件之一

专门用于解决Phase 4中发现的Napoli vs Juventus案例中的主客场偏见问题。
通过将主客场比赛完全分离计算滚动统计，消除数据混淆问题。

核心功能：
1. 主队专用滚动统计 (主场表现)
2. 客队专用滚动统计 (客场表现)
3. 主客场对比特征 (表现差异)
4. 场馆优势量化分析

目标：通过场馆分离特征将模型准确率提升5-8%
"""

import logging
import pandas as pd
from typing import Dict, List, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VenueStats:
    """场馆统计数据结构"""

    home_goals_rolling_3: float = 0.0  # 主队主场3场平均进球
    home_goals_rolling_5: float = 0.0  # 主队主场5场平均进球
    away_goals_rolling_3: float = 0.0  # 客队客场3场平均进球
    away_goals_rolling_5: float = 0.0  # 客队客场5场平均进球
    home_away_goal_diff_3: float = 0.0  # 主客场3场进球差
    home_away_goal_diff_5: float = 0.0  # 主客场5场进球差
    home_advantage_3: float = 0.0  # 主场优势指数(3场)
    home_advantage_5: float = 0.0  # 主场优势指数(5场)

    def to_dict(self) -> Dict[str, float]:
        """转换为字典格式"""
        return {
            "venue_home_goals_rolling_3": self.home_goals_rolling_3,
            "venue_home_goals_rolling_5": self.home_goals_rolling_5,
            "venue_away_goals_rolling_3": self.away_goals_rolling_3,
            "venue_away_goals_rolling_5": self.away_goals_rolling_5,
            "venue_home_vs_away_diff_3": self.home_away_goal_diff_3,
            "venue_home_vs_away_diff_5": self.home_away_goal_diff_5,
            "venue_home_advantage_3": self.home_advantage_3,
            "venue_home_advantage_5": self.home_advantage_5,
        }


class VenueAnalyzer:
    """
    场馆分析器

    通过分离主客场比赛统计，解决传统滚动统计中的主客场混淆问题。
    专门设计用于改进像Napoli vs Juventus这样的案例预测。
    """

    def __init__(self, windows: List[int] = [3, 5]):
        """
        初始化场馆分析器

        Args:
            windows: 滚动窗口大小列表
        """
        self.windows = windows
        logger.info(f"VenueAnalyzer 初始化完成，滚动窗口: {windows}")

    def calculate_venue_features_for_match(
        self, df: pd.DataFrame, home_id: int, away_id: int, match_date: pd.Timestamp
    ) -> VenueStats:
        """
        为特定比赛计算场馆特征

        Args:
            df: 包含所有历史比赛的DataFrame
            home_id: 主队ID
            away_id: 客队ID
            match_date: 当前比赛日期

        Returns:
            VenueStats: 场馆统计数据
        """
        try:
            # 1. 计算主队主场表现
            home_venue_stats = self._calculate_team_venue_stats(
                df, home_id, "home", match_date
            )

            # 2. 计算客队客场表现
            away_venue_stats = self._calculate_team_venue_stats(
                df, away_id, "away", match_date
            )

            # 3. 合并统计结果
            venue_stats = VenueStats()
            venue_stats.home_goals_rolling_3 = home_venue_stats.get(3, 0.0)
            venue_stats.home_goals_rolling_5 = home_venue_stats.get(5, 0.0)
            venue_stats.away_goals_rolling_3 = away_venue_stats.get(3, 0.0)
            venue_stats.away_goals_rolling_5 = away_venue_stats.get(5, 0.0)

            # 4. 计算对比特征
            venue_stats.home_away_goal_diff_3 = (
                venue_stats.home_goals_rolling_3 - venue_stats.away_goals_rolling_3
            )
            venue_stats.home_away_goal_diff_5 = (
                venue_stats.home_goals_rolling_5 - venue_stats.away_goals_rolling_5
            )

            # 5. 计算主场优势指数
            venue_stats.home_advantage_3 = self._calculate_home_advantage(
                df, home_id, match_date, 3
            )
            venue_stats.home_advantage_5 = self._calculate_home_advantage(
                df, home_id, match_date, 5
            )

                f"场馆特征计算完成: {home_id}(主) vs {away_id}(客), "
                f"主场进球(3场): {venue_stats.home_goals_rolling_3:.2f}"
            )

            return venue_stats

        except Exception as e:
            logger.error(f"计算场馆特征失败: {str(e)}")
            return VenueStats()

    def calculate_venue_features_for_all_matches(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        为DataFrame中的所有比赛计算场馆特征

        Args:
            df: 包含所有比赛的DataFrame

        Returns:
            pd.DataFrame: 添加了场馆特征的DataFrame
        """
        logger.info("开始计算所有比赛的场馆特征...")

        # 按日期排序确保时间顺序
        df_sorted = df.sort_values("match_date").copy()

        # 为每支球队计算主场和客场滚动统计
        df_with_home_stats = self._add_home_venue_features(df_sorted)
        df_with_venue_stats = self._add_away_venue_features(df_with_home_stats)

        # 计算对比特征
        df_with_venue_stats["venue_home_vs_away_diff_3"] = (
            df_with_venue_stats["venue_home_goals_rolling_3"]
            - df_with_venue_stats["venue_away_goals_rolling_3"]
        )
        df_with_venue_stats["venue_home_vs_away_diff_5"] = (
            df_with_venue_stats["venue_home_goals_rolling_5"]
            - df_with_venue_stats["venue_away_goals_rolling_5"]
        )

        # 计算主场优势指数
        df_with_venue_stats["venue_home_advantage_3"] = df_with_venue_stats[
            "venue_home_goals_rolling_3"
        ] / (df_with_venue_stats["venue_away_goals_rolling_3"] + 0.01)
        df_with_venue_stats["venue_home_advantage_5"] = df_with_venue_stats[
            "venue_home_goals_rolling_5"
        ] / (df_with_venue_stats["venue_away_goals_rolling_5"] + 0.01)

        logger.info("场馆特征计算完成，新增特征数量: 8")

        return df_with_venue_stats

    def _calculate_team_venue_stats(
        self, df: pd.DataFrame, team_id: int, venue_type: str, match_date: pd.Timestamp
    ) -> Dict[int, float]:
        """
        计算特定球队在特定场馆类型的滚动统计

        Args:
            df: 包含所有比赛的DataFrame
            team_id: 球队ID
            venue_type: 场馆类型 ('home' 或 'away')
            match_date: 当前比赛日期

        Returns:
            Dict[int, float]: 各窗口大小的平均进球数
        """
        # 筛选球队在特定场馆的历史比赛
        if venue_type == "home":
            team_matches = df[
                (df["home_team_id"] == team_id)
                & (pd.to_datetime(df["match_date"]) < match_date)
            ].sort_values("match_date")
            goals_col = "home_score"
        else:  # venue_type == 'away'
            team_matches = df[
                (df["away_team_id"] == team_id)
                & (pd.to_datetime(df["match_date"]) < match_date)
            ].sort_values("match_date")
            goals_col = "away_score"

        if team_matches.empty:
            return {window: 0.0 for window in self.windows}

        # 计算各窗口的滚动平均
        venue_stats = {}
        for window in self.windows:
            rolling_mean = (
                team_matches[goals_col]
                .rolling(window, min_periods=1)
                .mean()
                .shift(1)  # 防止数据泄露
            )

            # 获取最近一场比赛的滚动平均值
            if not rolling_mean.empty:
                venue_stats[window] = rolling_mean.iloc[-1]
            else:
                venue_stats[window] = 0.0

        return venue_stats

    def _add_home_venue_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加主场场馆特征"""
        df_result = df.copy()

        for team_id in df["home_team_id"].unique():
            # 获取该球队的所有主场比赛
            home_matches = df[df["home_team_id"] == team_id].sort_values("match_date")

            # 计算各窗口的滚动平均
            for window in self.windows:
                col_name = f"venue_home_goals_rolling_{window}"
                rolling_stats = (
                    home_matches["home_score"]
                    .rolling(window, min_periods=1)
                    .mean()
                    .shift(1)  # 防止数据泄露
                )

                # 将统计结果映射回原DataFrame
                df_result.loc[home_matches.index, col_name] = rolling_stats

        return df_result

    def _add_away_venue_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """添加客场场馆特征"""
        df_result = df.copy()

        for team_id in df["away_team_id"].unique():
            # 获取该球队的所有客场比赛
            away_matches = df[df["away_team_id"] == team_id].sort_values("match_date")

            # 计算各窗口的滚动平均
            for window in self.windows:
                col_name = f"venue_away_goals_rolling_{window}"
                rolling_stats = (
                    away_matches["away_score"]
                    .rolling(window, min_periods=1)
                    .mean()
                    .shift(1)  # 防止数据泄露
                )

                # 将统计结果映射回原DataFrame
                df_result.loc[away_matches.index, col_name] = rolling_stats

        return df_result

    def _calculate_home_advantage(
        self, df: pd.DataFrame, team_id: int, match_date: pd.Timestamp, window: int
    ) -> float:
        """
        计算主场优势指数

        Args:
            df: 包含所有比赛的DataFrame
            team_id: 球队ID
            match_date: 当前比赛日期
            window: 滚动窗口大小

        Returns:
            float: 主场优势指数
        """
        try:
            # 获取该球队的主场和客场历史表现
            home_stats = self._calculate_team_venue_stats(
                df, team_id, "home", match_date
            )
            away_stats = self._calculate_team_venue_stats(
                df, team_id, "away", match_date
            )

            home_goals = home_stats.get(window, 0.0)
            away_goals = away_stats.get(window, 0.0)

            # 主场优势指数 = 主场平均进球 / (客场平均进球 + 0.01)
            # 加0.01防止除零错误
            home_advantage = home_goals / (away_goals + 0.01)

            return home_advantage

        except Exception as e:
            logger.error(f"计算主场优势失败: {str(e)}")
            return 1.0  # 默认中性优势

    def get_venue_summary(self, df: pd.DataFrame, team_id: int) -> Dict[str, Any]:
        """
        获取球队的场馆表现摘要

        Args:
            df: 包含所有比赛的DataFrame
            team_id: 球队ID

        Returns:
            Dict: 场馆表现摘要
        """
        # 分离主场和客场比赛
        home_matches = df[df["home_team_id"] == team_id]
        away_matches = df[df["away_team_id"] == team_id]

        # 计算基础统计
        home_games = len(home_matches)
        away_games = len(away_matches)

        home_goals = home_matches["home_score"].sum() if home_games > 0 else 0
        away_goals = away_matches["away_score"].sum() if away_games > 0 else 0

        home_wins = len(
            home_matches[home_matches["home_score"] > home_matches["away_score"]]
        )
        away_wins = len(
            away_matches[away_matches["away_score"] > away_matches["home_score"]]
        )

        # 计算平均指标
        avg_home_goals = home_goals / home_games if home_games > 0 else 0
        avg_away_goals = away_goals / away_games if away_games > 0 else 0

        home_win_rate = home_wins / home_games if home_games > 0 else 0
        away_win_rate = away_wins / away_games if away_games > 0 else 0

        # 计算主场优势
        home_advantage = (
            avg_home_goals / (avg_away_goals + 0.01) if avg_away_goals > 0 else 1.0
        )

        return {
            "team_id": team_id,
            "home_games": home_games,
            "away_games": away_games,
            "total_games": home_games + away_games,
            "home_goals": home_goals,
            "away_goals": away_goals,
            "avg_home_goals": avg_home_goals,
            "avg_away_goals": avg_away_goals,
            "home_wins": home_wins,
            "away_wins": away_wins,
            "home_win_rate": home_win_rate,
            "away_win_rate": away_win_rate,
            "home_advantage": home_advantage,
        }


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

    # 创建场馆分析器
    venue_analyzer = VenueAnalyzer(windows=[3, 5])

    # 计算场馆特征
    venue_stats = venue_analyzer.calculate_venue_features_for_match(
        df, 1, 2, pd.Timestamp("2024-03-25")
    )

    # 获取场馆摘要
    summary = venue_analyzer.get_venue_summary(df, 1)
