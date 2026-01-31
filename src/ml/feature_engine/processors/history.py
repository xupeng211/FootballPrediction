"""
HistoricalRollingProcessor - 历史追溯处理器（V24.0 时序引擎）
==========================================================

负责提取历史时序特征，通过多时间窗口滚动统计，将单场快照升级为时空矩阵：

    - L3 (Last 3): 近 3 场均值与标准差
    - L5 (Last 5): 近 5 场趋势（线性回归斜率）
    - H2H (Head to Head): 两队交锋历史统计（近 5 场）

核心指标（20 个）:
    - 基础: xG, shots, possession, passes
    - 进阶: rating, corners, fouls, offsides
    - 高级: momentum_mean, pressure_score, tempo

设计模式:
    - 滚动窗口: 滑动时间窗口统计
    - 趋势分析: 线性回归斜率计算
    - 对战历史: 主客队专属交锋记录

作者: FootballPrediction Architecture Team
版本: V24.0-alpha
"""

from dataclasses import dataclass
import logging
import statistics
from typing import Any

from src.ml.feature_engine.base import BaseProcessor, ProcessorConfig, ProcessorResult
from src.ml.feature_engine.models import HomeAway, MatchData

logger = logging.getLogger(__name__)


@dataclass
class MatchSnapshot:
    """比赛快照（用于历史统计）"""

    match_id: str
    date: str
    team_id: str
    opponent_id: str | None
    is_home: bool
    stats: dict[str, float]


class HistoricalRollingProcessorConfig(ProcessorConfig):
    """
    HistoricalRollingProcessor 配置

    Attributes:
        enable_l3_stats: 是否启用 L3 窗口统计
        enable_l5_trend: 是否启用 L5 趋势分析
        enable_h2h_stats: 是否启用 H2H 对战统计
        l3_window: L3 窗口大小（场数）
        l5_window: L5 窗口大小（场数）
        h2h_window: H2H 窗口大小（场数）
        min_matches: 最少历史比赛数量
    """

    enable_l3_stats: bool = True
    enable_l5_trend: bool = True
    enable_h2h_stats: bool = True
    l3_window: int = 3
    l5_window: int = 5
    h2h_window: int = 5
    min_matches: int = 2


class HistoricalRollingProcessor(BaseProcessor[MatchData]):
    """
    历史追溯处理器（V24.0 时序引擎）

    职责:
        1. 计算近 3 场滚动统计（均值 + 标准差）
        2. 计算近 5 场趋势（线性回归斜率）
        3. 计算两队交锋历史统计（近 5 场）

    特征输出（120+ 维）:
        # L3 滚动统计（约 48 维）
        - home_l3_xg_mean, home_l3_xg_std: 近 3 场 xG 均值/标准差
        - home_l3_shots_mean, home_l3_shots_std: 近 3 场射门均值/标准差
        - home_l3_possession_mean: 近 3 场控球率均值
        ...

        # L5 趋势分析（约 40 维）
        - home_l5_xg_trend: 近 5 场 xG 趋势（斜率）
        - home_l5_shots_trend: 近 5 场射门趋势
        - home_l5_rating_trend: 近 5 场评分趋势
        ...

        # H2H 对战历史（约 32 维）
        - home_h2h_xg_mean: 对阵此对手的 xG 均值
        - home_h2h_win_rate: 对阵此对手的胜率
        - home_h2h_goals_scored_mean: 对阵此对手的场均进球
        ...

    数据来源:
        - context.{home|away}_match_history (外部注入的历史比赛数据)
    """

    processor_name = "HistoricalRollingProcessor"
    processor_version = "24.0.0"
    priority = 15  # 在基础统计之后，战术分析之前

    # 核心指标列表
    CORE_METRICS = [
        "expected_goals",  # xG
        "shots_total",  # 总射门
        "shots_on_target",  # 射正
        "possession",  # 控球率
        "total_passes",  # 总传球
        "accurate_passes",  # 成功传球
        "team_rating",  # 评分
        "corners",  # 角球
        "fouls",  # 犯规
        "offsides",  # 越位
    ]

    # 高级指标列表（用于 H2H）
    ADVANCED_METRICS = [
        "momentum_mean",
        "pressure_score",
        "tempo_score",
    ]

    def __init__(self, config: HistoricalRollingProcessorConfig | None = None) -> None:
        super().__init__(config or HistoricalRollingProcessorConfig())
        self.config: HistoricalRollingProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """提取历史时序特征"""
        features: dict[str, float] = {}
        warnings: list[str] = []

        try:
            # 1. 获取历史数据
            home_history = self._get_match_history(context, HomeAway.HOME, data.home_team)
            away_history = self._get_match_history(context, HomeAway.AWAY, data.away_team)

            # 2. L3 滚动统计
            if self.config.enable_l3_stats:
                if len(home_history) >= self.config.min_matches:
                    home_l3 = self._compute_l3_stats(home_history)
                    features.update(home_l3)
                else:
                    warnings.append("home_history_insufficient_for_l3")
                    features.update(self._create_default_l3_features("home"))

                if len(away_history) >= self.config.min_matches:
                    away_l3 = self._compute_l3_stats(away_history)
                    features.update(away_l3)
                else:
                    warnings.append("away_history_insufficient_for_l3")
                    features.update(self._create_default_l3_features("away"))

            # 3. L5 趋势分析
            if self.config.enable_l5_trend:
                if len(home_history) >= self.config.min_matches:
                    home_l5 = self._compute_l5_trends(home_history)
                    features.update(home_l5)
                else:
                    warnings.append("home_history_insufficient_for_l5")
                    features.update(self._create_default_l5_features("home"))

                if len(away_history) >= self.config.min_matches:
                    away_l5 = self._compute_l5_trends(away_history)
                    features.update(away_l5)
                else:
                    warnings.append("away_history_insufficient_for_l5")
                    features.update(self._create_default_l5_features("away"))

            # 4. H2H 对战历史
            if self.config.enable_h2h_stats:
                home_h2h = self._compute_h2h_stats(home_history, data.away_team, is_home=True)
                features.update(home_h2h)

                away_h2h = self._compute_h2h_stats(away_history, data.home_team, is_home=False)
                features.update(away_h2h)

            # 5. 历史对比特征
            comparison_features = self._compute_comparison_features(features)
            features.update(comparison_features)

            result = ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "home_history_count": len(home_history),
                    "away_history_count": len(away_history),
                    "l3_enabled": self.config.enable_l3_stats,
                    "l5_enabled": self.config.enable_l5_trend,
                    "h2h_enabled": self.config.enable_h2h_stats,
                },
            )

            for warning in warnings:
                result.with_warning(warning)

            return result

        except Exception as e:
            logger.exception(f"HistoricalRollingProcessor failed: {e}")
            return ProcessorResult.failure_result(str(e))

    def _get_match_history(
        self, context: Any, side: HomeAway, team_name: str
    ) -> list[MatchSnapshot]:
        """
        获取历史比赛数据

        数据来源:
            - context.{home|away}_match_history (外部注入)

        Args:
            context: 处理上下文
            side: 主/客队标识
            team_name: 球队名称

        Returns:
            历史比赛快照列表（按时间倒序，最新的在前）
        """
        history_key = f"{side.value}_match_history"

        if context:
            cached = context.get_cached(history_key)
            if cached:
                return cached

        return []

    def _compute_l3_stats(self, history: list[MatchSnapshot]) -> dict[str, float]:
        """
        计算 L3 滚动统计（近 3 场）

        Args:
            history: 历史比赛列表（已按时间倒序）

        Returns:
            L3 统计特征字典
        """
        features = {}
        prefix = history[0].team_id.replace(" ", "_").lower() if history else "unknown"

        # 取近 3 场
        recent_3 = history[: self.config.l3_window]

        for metric in self.CORE_METRICS:
            values = [match.stats.get(metric, 0.0) for match in recent_3]

            if values:
                # 均值
                features[f"{prefix}_l3_{metric}_mean"] = round(statistics.mean(values), 4)

                # 标准差
                if len(values) > 1:
                    features[f"{prefix}_l3_{metric}_std"] = round(statistics.stdev(values), 4)
                else:
                    features[f"{prefix}_l3_{metric}_std"] = 0.0

                # 变异系数（std/mean）
                mean_val = features[f"{prefix}_l3_{metric}_mean"]
                if mean_val != 0:
                    features[f"{prefix}_l3_{metric}_cv"] = round(
                        features[f"{prefix}_l3_{metric}_std"] / abs(mean_val), 4
                    )
                else:
                    features[f"{prefix}_l3_{metric}_cv"] = 0.0
            else:
                features[f"{prefix}_l3_{metric}_mean"] = 0.0
                features[f"{prefix}_l3_{metric}_std"] = 0.0
                features[f"{prefix}_l3_{metric}_cv"] = 0.0

        # 计算胜率
        wins = sum(
            1 for m in recent_3 if m.stats.get("goals_scored", 0) > m.stats.get("goals_conceded", 0)
        )
        features[f"{prefix}_l3_win_rate"] = round(wins / len(recent_3), 4) if recent_3 else 0.0

        # 计算场均进球
        goals_scored = [m.stats.get("goals_scored", 0) for m in recent_3]
        if goals_scored:
            features[f"{prefix}_l3_goals_scored_mean"] = round(statistics.mean(goals_scored), 4)
        else:
            features[f"{prefix}_l3_goals_scored_mean"] = 0.0

        return features

    def _compute_l5_trends(self, history: list[MatchSnapshot]) -> dict[str, float]:
        """
        计算 L5 趋势分析（近 5 场线性回归斜率）

        Args:
            history: 历史比赛列表（已按时间倒序）

        Returns:
            L5 趋势特征字典
        """
        features = {}
        prefix = history[0].team_id.replace(" ", "_").lower() if history else "unknown"

        # 取近 5 场，并反转时间顺序（从旧到新）
        recent_5 = list(reversed(history[: self.config.l5_window]))

        if len(recent_5) < 2:
            # 数据不足，返回默认值
            for metric in self.CORE_METRICS:
                features[f"{prefix}_l5_{metric}_trend"] = 0.0
            return features

        n = len(recent_5)
        x = list(range(n))  # 时间索引：0, 1, 2, ...

        for metric in self.CORE_METRICS:
            y = [m.stats.get(metric, 0.0) for m in recent_5]

            if len(y) >= 2:
                slope = self._compute_linear_slope(x, y)
                features[f"{prefix}_l5_{metric}_trend"] = round(slope, 4)
            else:
                features[f"{prefix}_l5_{metric}_trend"] = 0.0

        return features

    def _compute_h2h_stats(
        self, history: list[MatchSnapshot], opponent: str, is_home: bool
    ) -> dict[str, float]:
        """
        计算 H2H 对战历史（对阵特定对手）

        Args:
            history: 己方历史比赛
            opponent: 对手名称
            is_home: 是否为主队视角

        Returns:
            H2H 统计特征字典
        """
        features = {}
        prefix = "home" if is_home else "away"

        # 筛选出对阵该对手的比赛
        h2h_matches = [m for m in history if m.opponent_id and m.opponent_id == opponent][
            : self.config.h2h_window
        ]

        if not h2h_matches:
            # 无对战记录，返回默认值
            features[f"{prefix}_h2h_matches_count"] = 0.0
            features[f"{prefix}_h2h_win_rate"] = 0.5
            features[f"{prefix}_h2h_goals_scored_mean"] = 0.0
            features[f"{prefix}_h2h_goals_conceded_mean"] = 0.0
            features[f"{prefix}_h2h_xg_mean"] = 0.0
            features[f"{prefix}_h2h_shots_mean"] = 0.0
            return features

        features[f"{prefix}_h2h_matches_count"] = float(len(h2h_matches))

        # 胜率
        wins = sum(
            1
            for m in h2h_matches
            if m.stats.get("goals_scored", 0) > m.stats.get("goals_conceded", 0)
        )
        features[f"{prefix}_h2h_win_rate"] = (
            round(wins / len(h2h_matches), 4) if h2h_matches else 0.5
        )

        # 进球/失球均值
        goals_scored = [m.stats.get("goals_scored", 0) for m in h2h_matches]
        goals_conceded = [m.stats.get("goals_conceded", 0) for m in h2h_matches]

        if goals_scored:
            features[f"{prefix}_h2h_goals_scored_mean"] = round(statistics.mean(goals_scored), 4)
        else:
            features[f"{prefix}_h2h_goals_scored_mean"] = 0.0

        if goals_conceded:
            features[f"{prefix}_h2h_goals_conceded_mean"] = round(
                statistics.mean(goals_conceded), 4
            )
        else:
            features[f"{prefix}_h2h_goals_conceded_mean"] = 0.0

        # 核心 H2H 指标
        for metric in ["expected_goals", "shots_total", "shots_on_target", "possession"]:
            values = [m.stats.get(metric, 0.0) for m in h2h_matches]
            if values:
                features[f"{prefix}_h2h_{metric}_mean"] = round(statistics.mean(values), 4)
            else:
                features[f"{prefix}_h2h_{metric}_mean"] = 0.0

        return features

    def _compute_linear_slope(self, x: list[float], y: list[float]) -> float:
        """计算线性回归斜率"""
        if len(x) < 2 or len(y) < 2:
            return 0.0

        n = len(x)
        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y, strict=False))
        sum_x2 = sum(xi * xi for xi in x)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0

        return (n * sum_xy - sum_x * sum_y) / denominator

    def _compute_comparison_features(self, features: dict[str, float]) -> dict[str, float]:
        """计算历史对比特征"""
        comparison = {}

        # L3 xG 对比
        home_l3_xg = features.get("home_l3_expected_goals_mean", 0.0)
        away_l3_xg = features.get("away_l3_expected_goals_mean", 0.0)
        comparison["diff_l3_xg_mean"] = round(home_l3_xg - away_l3_xg, 4)

        # L5 xG 趋势对比
        home_l5_xg_trend = features.get("home_l5_expected_goals_trend", 0.0)
        away_l5_xg_trend = features.get("away_l5_expected_goals_trend", 0.0)
        comparison["diff_l5_xg_trend"] = round(home_l5_xg_trend - away_l5_xg_trend, 4)

        # H2H 胜率对比
        home_h2h_win_rate = features.get("home_h2h_win_rate", 0.5)
        away_h2h_win_rate = features.get("away_h2h_win_rate", 0.5)
        comparison["diff_h2h_win_rate"] = round(home_h2h_win_rate - away_h2h_win_rate, 4)

        return comparison

    def _create_default_l3_features(self, prefix: str) -> dict[str, float]:
        """创建默认 L3 特征"""
        defaults = {}
        for metric in self.CORE_METRICS:
            defaults[f"{prefix}_l3_{metric}_mean"] = 0.0
            defaults[f"{prefix}_l3_{metric}_std"] = 0.0
            defaults[f"{prefix}_l3_{metric}_cv"] = 0.0
        defaults[f"{prefix}_l3_win_rate"] = 0.5
        defaults[f"{prefix}_l3_goals_scored_mean"] = 0.0
        return defaults

    def _create_default_l5_features(self, prefix: str) -> dict[str, float]:
        """创建默认 L5 特征"""
        defaults = {}
        for metric in self.CORE_METRICS:
            defaults[f"{prefix}_l5_{metric}_trend"] = 0.0
        return defaults

    def get_feature_schema(self) -> dict[str, type]:
        """获取输出特征的 Schema（V24.0 动态生成）"""
        schema = {}

        prefixes = ["home", "away"]

        # L3 滚动统计特征
        for prefix in prefixes:
            for metric in self.CORE_METRICS:
                schema[f"{prefix}_l3_{metric}_mean"] = float
                schema[f"{prefix}_l3_{metric}_std"] = float
                schema[f"{prefix}_l3_{metric}_cv"] = float
            schema[f"{prefix}_l3_win_rate"] = float
            schema[f"{prefix}_l3_goals_scored_mean"] = float

        # L5 趋势特征
        for prefix in prefixes:
            for metric in self.CORE_METRICS:
                schema[f"{prefix}_l5_{metric}_trend"] = float

        # H2H 对战特征
        for prefix in prefixes:
            schema[f"{prefix}_h2h_matches_count"] = float
            schema[f"{prefix}_h2h_win_rate"] = float
            schema[f"{prefix}_h2h_goals_scored_mean"] = float
            schema[f"{prefix}_h2h_goals_conceded_mean"] = float
            for metric in ["expected_goals", "shots_total", "shots_on_target", "possession"]:
                schema[f"{prefix}_h2h_{metric}_mean"] = float

        # 对比特征
        schema["diff_l3_xg_mean"] = float
        schema["diff_l5_xg_trend"] = float
        schema["diff_h2h_win_rate"] = float

        return schema
