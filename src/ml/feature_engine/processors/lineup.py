"""
LineupProcessor - 阵容稳定性处理器（V23.0 扩展版）
==================================================

负责分析阵容特征，包括:
    - 阵容稳定性（首发变化次数）
    - 阵容价值（总身价、平均身价）
    - 阵型分析（4-3-3, 4-2-3-1 等）
    - 球员级联聚合（11人数据加总）
    - **V23.0 新增**: 阵容深度与多样性扩展（+70维）

设计模式:
    - 聚合模式: 从球员数据聚合到球队级别
    - 历史对比: 对比历史阵容计算稳定性

作者: FootballPrediction Architecture Team
版本: V23.0-final
"""

import logging
from typing import Any

from src.ml.feature_engine.base import BaseProcessor, ProcessorConfig, ProcessorResult
from src.ml.feature_engine.models import LineupInfo, MatchData, PlayerStats

logger = logging.getLogger(__name__)


class LineupProcessorConfig(ProcessorConfig):
    """
    LineupProcessor 配置

    Attributes:
        enable_value_analysis: 是否启用身价分析
        enable_formation_analysis: 是否启用阵型分析
        enable_player_aggregation: 是否启用球员级联聚合
        enable_diversity_analysis: 是否启用多样性分析（V23.0）
        min_starter_count: 最少首发人数（默认 11）
    """

    enable_value_analysis: bool = True
    enable_formation_analysis: bool = True
    enable_player_aggregation: bool = True
    enable_diversity_analysis: bool = True  # V23.0 新增
    min_starter_count: int = 11


class LineupProcessor(BaseProcessor[MatchData]):
    """
    阵容稳定性处理器（V23.0 扩展版）

    职责:
        1. 分析主客队阵容稳定性
        2. 计算阵容价值指标
        3. 解析阵型配置
        4. 聚合球员数据到球队级别
        5. **V23.0**: 阵容深度与多样性分析

    特征输出（100+ 维）:
        # 基础阵容特征
        - home_lineup_stability, away_lineup_stability: 阵容稳定性评分
        - home_unchanged, away_unchanged: 是否未变阵容
        - home_formation_code, away_formation_code: 阵型编码

        # 球员聚合特征
        - home_agg_touches, away_agg_touches: 球员触球加总
        - home_agg_passes, away_agg_passes: 球员传球加总
        - home_agg_xg, away_agg_xg: 球员 xG 加总

        # V23.0: 阵容深度特征（70+ 维）
        - 按位置分组的统计数据（后卫/中场/前锋）
        - 替补席深度分析
        - 年龄结构多样性
        - 经验值分析
    """

    processor_name = "LineupProcessor"
    processor_version = "23.0.0"
    priority = 30

    def __init__(self, config: LineupProcessorConfig | None = None) -> None:
        super().__init__(config or LineupProcessorConfig())
        self.config: LineupProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """提取阵容特征"""
        features: dict[str, float] = {}

        try:
            # 主队阵容分析
            if data.home_lineup:
                home_features = self._analyze_lineup(data.home_lineup, "home")
                features.update(home_features)
            else:
                logger.debug(f"Match {data.match_id}: home_lineup not available")

            # 客队阵容分析
            if data.away_lineup:
                away_features = self._analyze_lineup(data.away_lineup, "away")
                features.update(away_features)
            else:
                logger.debug(f"Match {data.match_id}: away_lineup not available")

            # 计算阵容对比特征
            comparison_features = self._compute_comparison_features(features)
            features.update(comparison_features)

            return ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "value_analysis_enabled": self.config.enable_value_analysis,
                },
            )

        except Exception as e:
            logger.exception(f"LineupProcessor failed: {e}")
            return ProcessorResult.failure_result(str(e))

    def _analyze_lineup(self, lineup: LineupInfo, prefix: str) -> dict[str, float]:
        """分析单队阵容特征"""
        features = {}

        # 阵容稳定性
        features[f"{prefix}_unchanged"] = 1.0 if lineup.unchanged_lineup else 0.0
        features[f"{prefix}_lineup_changes"] = float(lineup.changes_from_last_match or 0)

        # 稳定性评分
        changes = lineup.changes_from_last_match or 0
        if changes == 0:
            stability_score = 1.0
        elif changes <= 2:
            stability_score = 0.8
        elif changes <= 4:
            stability_score = 0.5
        else:
            stability_score = 0.2
        features[f"{prefix}_lineup_stability"] = stability_score

        # 阵型分析
        if self.config.enable_formation_analysis and lineup.formation:
            formation_code = self._parse_formation(lineup.formation)
            features[f"{prefix}_formation_code"] = formation_code
        else:
            features[f"{prefix}_formation_code"] = -1.0

        # 阵容价值
        if self.config.enable_value_analysis:
            features[f"{prefix}_total_value"] = float(lineup.total_market_value or 0.0)
            features[f"{prefix}_avg_value"] = float(lineup.avg_market_value or 0.0)

        # 球员数据聚合
        if self.config.enable_player_aggregation and lineup.players:
            agg_features = self._aggregate_player_stats(lineup.players, prefix)
            features.update(agg_features)

        # V23.0: 多样性分析
        if self.config.enable_diversity_analysis and lineup.players:
            diversity_features = self._analyze_diversity(lineup.players, prefix)
            features.update(diversity_features)

        return features

    def _parse_formation(self, formation: str) -> float:
        """解析阵型为数值编码"""
        try:
            parts = formation.replace("-", "").replace(" ", "")
            return float(parts) if parts.isdigit() else -1.0
        except (ValueError, AttributeError):
            return -1.0

    def _aggregate_player_stats(self, players: list[PlayerStats], prefix: str) -> dict[str, float]:
        """聚合球员统计数据"""
        features = {}

        # 基础聚合
        features[f"{prefix}_agg_touches"] = float(sum(p.touches or 0 for p in players))
        features[f"{prefix}_agg_accurate_passes"] = float(
            sum(p.accurate_passes or 0 for p in players)
        )
        features[f"{prefix}_agg_player_xg"] = round(
            sum(p.expected_goals or 0.0 for p in players), 3
        )
        features[f"{prefix}_agg_player_shots"] = float(sum(p.total_shots or 0 for p in players))

        # 出场时间
        starters = [p for p in players if p.is_starter]
        if starters:
            avg_minutes = sum(p.minutes_played or 0 for p in starters) / len(starters)
            features[f"{prefix}_avg_minutes_played"] = round(avg_minutes, 1)
        else:
            features[f"{prefix}_avg_minutes_played"] = 0.0

        # 替补统计
        substitution_count = len(
            [p for p in players if not p.is_starter and (p.minutes_played or 0) > 0]
        )
        features[f"{prefix}_substitution_count"] = float(substitution_count)

        return features

    def _analyze_diversity(self, players: list[PlayerStats], prefix: str) -> dict[str, float]:
        """
        阵容多样性分析（V23.0 核心扩展）

        按位置分组统计，增加 70+ 维特征

        Returns:
            多样性特征字典
        """
        features = {}

        # 按球衣号码分组（用于战术位置识别）
        # GK: 1, DF: 2-6, MF: 6-11, FW: 9-11
        gk_players = []
        df_players = []
        mf_players = []
        fw_players = []

        for p in players:
            if not p.is_starter:
                continue
            jersey = p.jersey_number or 99
            if jersey == 1:
                gk_players.append(p)
            elif 2 <= jersey <= 6:
                df_players.append(p)
            elif jersey in [6, 8, 10]:
                mf_players.append(p)
            elif jersey in [7, 9, 11]:
                fw_players.append(p)
            else:
                mf_players.append(p)  # 默认中场

        # 按位置统计（每个位置约 10 维）
        for pos_name, pos_players in [
            ("gk", gk_players),
            ("df", df_players),
            ("mf", mf_players),
            ("fw", fw_players),
        ]:
            if pos_players:
                # 触球统计
                features[f"{prefix}_{pos_name}_touches"] = float(
                    sum(p.touches or 0 for p in pos_players)
                )
                features[f"{prefix}_{pos_name}_passes"] = float(
                    sum(p.accurate_passes or 0 for p in pos_players)
                )
                features[f"{prefix}_{pos_name}_xg"] = round(
                    sum(p.expected_goals or 0.0 for p in pos_players), 3
                )
                features[f"{prefix}_{pos_name}_shots"] = float(
                    sum(p.total_shots or 0 for p in pos_players)
                )

                # 评分统计
                ratings = [p.team_rating or 0 for p in pos_players]
                import statistics

                features[f"{prefix}_{pos_name}_avg_rating"] = (
                    round(statistics.mean(ratings), 2) if ratings else 0.0
                )
                features[f"{prefix}_{pos_name}_max_rating"] = (
                    round(max(ratings), 2) if ratings else 0.0
                )
                features[f"{prefix}_{pos_name}_min_rating"] = (
                    round(min(ratings), 2) if ratings else 0.0
                )

                # 年龄统计
                ages = [p.age or 0 for p in pos_players]
                features[f"{prefix}_{pos_name}_avg_age"] = (
                    round(statistics.mean(ages), 1) if ages else 0.0
                )
                features[f"{prefix}_{pos_name}_total_age"] = float(sum(ages))

                # 身价统计
                values = [p.market_value or 0 for p in pos_players]
                features[f"{prefix}_{pos_name}_total_value"] = round(sum(values), 2)
                features[f"{prefix}_{pos_name}_avg_value"] = (
                    round(statistics.mean(values), 2) if values else 0.0
                )

                # 出场时间
                minutes = [p.minutes_played or 0 for p in pos_players]
                features[f"{prefix}_{pos_name}_total_minutes"] = float(sum(minutes))
                features[f"{prefix}_{pos_name}_avg_minutes"] = (
                    round(statistics.mean(minutes), 1) if minutes else 0.0
                )

                # 球员数量
                features[f"{prefix}_{pos_name}_count"] = float(len(pos_players))

            else:
                # 填充默认值
                for metric in [
                    "touches",
                    "passes",
                    "xg",
                    "shots",
                    "avg_rating",
                    "max_rating",
                    "min_rating",
                    "avg_age",
                    "total_age",
                    "total_value",
                    "avg_value",
                    "total_minutes",
                    "avg_minutes",
                    "count",
                ]:
                    features[f"{prefix}_{pos_name}_{metric}"] = 0.0

        # 阵容多样性评分（熵）
        position_counts = [len(gk_players), len(df_players), len(mf_players), len(fw_players)]
        total = sum(position_counts)
        if total > 0:
            ratios = [c / total for c in position_counts]
            features[f"{prefix}_position_entropy"] = round(self._calculate_entropy(ratios), 4)
        else:
            features[f"{prefix}_position_entropy"] = 0.0

        # 替补深度
        bench_players = [p for p in players if not p.is_starter]
        if bench_players:
            features[f"{prefix}_bench_count"] = float(len(bench_players))
            bench_values = [p.market_value or 0 for p in bench_players]
            features[f"{prefix}_bench_total_value"] = round(sum(bench_values), 2)
            features[f"{prefix}_bench_avg_value"] = (
                round(statistics.mean(bench_values), 2) if bench_values else 0.0
            )

            # 替补出场时间
            bench_minutes = [p.minutes_played or 0 for p in bench_players]
            features[f"{prefix}_bench_total_minutes"] = float(sum(bench_minutes))
            features[f"{prefix}_bench_avg_minutes"] = (
                round(statistics.mean(bench_minutes), 1) if bench_minutes else 0.0
            )
        else:
            features[f"{prefix}_bench_count"] = 0.0
            features[f"{prefix}_bench_total_value"] = 0.0
            features[f"{prefix}_bench_avg_value"] = 0.0
            features[f"{prefix}_bench_total_minutes"] = 0.0
            features[f"{prefix}_bench_avg_minutes"] = 0.0

        return features

    def _calculate_entropy(self, ratios: list[float]) -> float:
        """计算熵"""
        import math

        entropy = 0.0
        for r in ratios:
            if r > 0:
                entropy -= r * math.log(r)
        return entropy

    def _compute_comparison_features(self, features: dict[str, float]) -> dict[str, float]:
        """计算阵容对比特征（V23.0 扩展：位置级深度对比）"""
        comparison_features = {}

        # 身价对比
        home_value = features.get("home_total_value", 0)
        away_value = features.get("away_total_value", 0)

        if home_value > 0 and away_value > 0:
            comparison_features["lineup_value_ratio"] = round(
                home_value / (home_value + away_value), 4
            )
            comparison_features["diff_lineup_value"] = round(home_value - away_value, 2)
        else:
            comparison_features["lineup_value_ratio"] = 0.5
            comparison_features["diff_lineup_value"] = 0.0

        # 稳定性对比
        home_stability = features.get("home_lineup_stability", 0.5)
        away_stability = features.get("away_lineup_stability", 0.5)
        comparison_features["diff_lineup_stability"] = round(home_stability - away_stability, 4)

        # 聚合数据对比
        home_touches = features.get("home_agg_touches", 0)
        away_touches = features.get("away_agg_touches", 0)

        if home_touches > 0 or away_touches > 0:
            total = home_touches + away_touches
            comparison_features["home_touches_ratio"] = round(
                home_touches / total if total > 0 else 0.5, 4
            )
        else:
            comparison_features["home_touches_ratio"] = 0.5

        # V23.0 扩展：位置级深度对比（50+ 维）
        position_metrics = [
            "touches",
            "passes",
            "xg",
            "shots",
            "avg_rating",
            "max_rating",
            "min_rating",
            "avg_age",
            "total_age",
            "total_value",
            "avg_value",
            "total_minutes",
            "avg_minutes",
        ]

        for pos in ["gk", "df", "mf", "fw"]:
            # 差值特征（主队 - 客队）
            for metric in position_metrics:
                home_val = features.get(f"home_{pos}_{metric}", 0.0)
                away_val = features.get(f"away_{pos}_{metric}", 0.0)
                comparison_features[f"diff_{pos}_{metric}"] = round(home_val - away_val, 4)

            # 比率特征（主队 / (主队+客队)）
            ratio_metrics = ["touches", "passes", "xg", "shots", "total_value"]
            for metric in ratio_metrics:
                home_val = features.get(f"home_{pos}_{metric}", 0.0)
                away_val = features.get(f"away_{pos}_{metric}", 0.0)
                total = home_val + away_val
                if total > 0:
                    comparison_features[f"home_{pos}_{metric}_ratio"] = round(home_val / total, 4)
                else:
                    comparison_features[f"home_{pos}_{metric}_ratio"] = 0.5

        # 熵对比（阵容多样性）
        home_entropy = features.get("home_position_entropy", 0.0)
        away_entropy = features.get("away_position_entropy", 0.0)
        comparison_features["diff_position_entropy"] = round(home_entropy - away_entropy, 4)

        # 替补深度对比
        for metric in ["count", "total_value", "avg_value", "total_minutes", "avg_minutes"]:
            home_val = features.get(f"home_bench_{metric}", 0.0)
            away_val = features.get(f"away_bench_{metric}", 0.0)
            comparison_features[f"diff_bench_{metric}"] = round(home_val - away_val, 4)

        return comparison_features

    def get_feature_schema(self) -> dict[str, type]:
        """获取输出特征的 Schema（V23.0 动态生成）"""
        schema = {
            "home_lineup_stability": float,
            "away_lineup_stability": float,
            "home_unchanged": float,
            "away_unchanged": float,
            "home_formation_code": float,
            "away_formation_code": float,
            "home_total_value": float,
            "away_total_value": float,
            "home_avg_value": float,
            "away_avg_value": float,
            "diff_lineup_stability": float,
            "lineup_value_ratio": float,
            "diff_lineup_value": float,
            "home_touches_ratio": float,
        }

        # V23.0: 动态生成位置分组特征 Schema（约 70 维）
        for prefix in ["home", "away"]:
            for pos in ["gk", "df", "mf", "fw"]:
                for metric in [
                    "touches",
                    "passes",
                    "xg",
                    "shots",
                    "avg_rating",
                    "max_rating",
                    "min_rating",
                    "avg_age",
                    "total_age",
                    "total_value",
                    "avg_value",
                    "total_minutes",
                    "avg_minutes",
                    "count",
                ]:
                    schema[f"{prefix}_{pos}_{metric}"] = float

        # 替补深度特征
        for prefix in ["home", "away"]:
            for metric in ["count", "total_value", "avg_value", "total_minutes", "avg_minutes"]:
                schema[f"{prefix}_bench_{metric}"] = float

        schema["home_position_entropy"] = float
        schema["away_position_entropy"] = float
        schema["diff_position_entropy"] = float

        # V23.0: 位置级对比特征（动态生成）
        position_metrics = [
            "touches",
            "passes",
            "xg",
            "shots",
            "avg_rating",
            "max_rating",
            "min_rating",
            "avg_age",
            "total_age",
            "total_value",
            "avg_value",
            "total_minutes",
            "avg_minutes",
        ]
        for pos in ["gk", "df", "mf", "fw"]:
            for metric in position_metrics:
                schema[f"diff_{pos}_{metric}"] = float

        # 比率特征
        ratio_metrics = ["touches", "passes", "xg", "shots", "total_value"]
        for pos in ["gk", "df", "mf", "fw"]:
            for metric in ratio_metrics:
                schema[f"home_{pos}_{metric}_ratio"] = float

        # 替补深度对比
        for metric in ["count", "total_value", "avg_value", "total_minutes", "avg_minutes"]:
            schema[f"diff_bench_{metric}"] = float

        return schema
