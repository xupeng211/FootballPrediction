"""
TacticalCrossProcessor - 战术交叉处理器（V24.0 维度爆破）
========================================================

负责自动生成核心因子的交互特征，通过暴力组合实现维度指数级扩张：

    - 物理交叉: 身价 × 位置，年龄 × 疲劳度
    - 战术交叉: 压迫感 × 控球率，动量 × 评分
    - 对比交叉: 主客队差值 × 场馆压力
    - 时序交叉: L3 趋势 × L5 趋势
    - 全量笛卡尔积: 所有因子两两交叉（200+ 组）

设计模式:
    - 笛卡尔积: 遍历所有因子对
    - 智能过滤: 只保留有实战意义的组合
    - 非线性变换: 支持 log, sqrt, sigmoid, square 等变换

作者: FootballPrediction Architecture Team
版本: V24.0-alpha
"""

import logging
import math
import statistics
from typing import Any

from ..base import BaseProcessor, ProcessorConfig, ProcessorResult
from ..models import MatchData

logger = logging.getLogger(__name__)


class TacticalCrossProcessorConfig(ProcessorConfig):
    """
    TacticalCrossProcessor 配置

    Attributes:
        enable_physical_cross: 是否启用物理交叉
        enable_tactical_cross: 是否启用战术交叉
        enable_comparison_cross: 是否启用对比交叉
        enable_temporal_cross: 是否启用时序交叉
        enable_cartesian_cross: 是否启用全量笛卡尔积交叉（V24.0 核心爆破）
        enable_nonlinear_transform: 是否启用非线性变换
        enable_polynomial_features: 是否启用多项式特征
        max_cross_features: 最大交叉特征数量（防止维度爆炸）
    """

    enable_physical_cross: bool = True
    enable_tactical_cross: bool = True
    enable_comparison_cross: bool = True
    enable_temporal_cross: bool = True
    enable_cartesian_cross: bool = True  # V24.0 核心爆破
    enable_nonlinear_transform: bool = True
    enable_polynomial_features: bool = True
    enable_higher_degree_polynomial: bool = True  # V24.0 扩展
    max_cross_features: int = 3000  # 提高上限


class TacticalCrossProcessor(BaseProcessor[MatchData]):
    """
    战术交叉处理器（V24.0 维度爆破）

    职责:
        1. 自动生成核心因子的交互特征
        2. 全量笛卡尔积交叉（所有因子两两组合）
        3. 应用非线性变换增强表达能力
        4. 生成多项式特征（平方、立方）

    特征输出（1500+ 维）:
        # 基础交叉特征（约 200 维）
        - home_value_age_interaction: 阵容身价 × 平均年龄
        - home_fatigue_stability_product: 疲劳度 × 稳定性
        ...

        # 全量笛卡尔积交叉（约 800 维）
        - 所有战术因子的两两交叉组合
        ...

        # 多项式特征（约 300 维）
        - square_home_xg: xG 的平方
        - cube_home_shots: 射门的立方
        ...

        # 非线性变换（约 200 维）
        - log_home_xg: log(xG + 1)
        - sqrt_home_shots: sqrt(射门数)
        ...
    """

    processor_name = "TacticalCrossProcessor"
    processor_version = "24.0.0"
    priority = 45  # 在基础统计之后

    # 核心因子列表（用于笛卡尔积交叉）
    CORE_FACTORS = [
        # 基础统计
        "expected_goals",
        "shots_total",
        "shots_on_target",
        "possession",
        "total_passes",
        "accurate_passes",
        "team_rating",
        "corners",
        "fouls",
        "offsides",
        # 阵容相关
        "total_value",
        "avg_value",
        "lineup_stability",
        "bench_impact_potential",
        "composite_health",
        # 战术相关
        "momentum_mean",
        "pressure_score",
        "tempo_score",
    ]

    # 高频动量因子（用于与战术因子交叉）
    HIGH_FREQ_MOMENTUM_FACTORS = [
        "m1_mean",
        "m2_mean",
        "m3_mean",
        "m4_mean",
        "m5_mean",
        "m6_mean",
        "m1_velocity",
        "m2_velocity",
        "m3_velocity",
        "m4_velocity",
        "m5_velocity",
        "m6_velocity",
        "m1_volatility",
        "m2_volatility",
        "m3_volatility",
        "m4_volatility",
        "m5_volatility",
        "m6_volatility",
    ]

    def __init__(self, config: TacticalCrossProcessorConfig | None = None) -> None:
        super().__init__(config or TacticalCrossProcessorConfig())
        self.config: TacticalCrossProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """提取战术交叉特征"""
        features: dict[str, float] = {}
        warnings: list[str] = []

        try:
            # 从 context 中获取已提取的基础特征
            base_features = self._get_base_features(context)

            # 如果没有提供基础特征，使用当前 match_data 的直接数据
            if not base_features:
                base_features = self._extract_base_features_from_match(data)

            # 1. 物理交叉特征
            if self.config.enable_physical_cross:
                physical_cross = self._compute_physical_cross(base_features)
                features.update(physical_cross)

            # 2. 战术交叉特征
            if self.config.enable_tactical_cross:
                tactical_cross = self._compute_tactical_cross(base_features)
                features.update(tactical_cross)

            # 3. 对比交叉特征
            if self.config.enable_comparison_cross:
                comparison_cross = self._compute_comparison_cross(base_features)
                features.update(comparison_cross)

            # 4. 时序交叉特征
            if self.config.enable_temporal_cross:
                temporal_cross = self._compute_temporal_cross(base_features)
                features.update(temporal_cross)

            # 5. 全量笛卡尔积交叉（V24.0 核心爆破）
            if self.config.enable_cartesian_cross:
                cartesian_cross = self._compute_cartesian_cross(base_features)
                features.update(cartesian_cross)

            # 6. 多项式特征
            if self.config.enable_polynomial_features:
                polynomial = self._compute_polynomial_features(base_features)
                features.update(polynomial)

            # 7. 非线性变换特征
            if self.config.enable_nonlinear_transform:
                nonlinear = self._compute_nonlinear_transforms(base_features)
                features.update(nonlinear)

            # 8. 高阶多项式特征（V24.0 扩展）
            if self.config.enable_higher_degree_polynomial:
                high_degree_poly = self._compute_higher_degree_polynomials(base_features)
                features.update(high_degree_poly)

            # 9. 高频动量交叉特征（V24.0 扩展）
            momentum_cross = self._compute_momentum_cross_features(base_features)
            features.update(momentum_cross)

            # 10. 全因子三阶交叉（V24.0 扩展）
            triple_cross = self._compute_triple_cross_features(base_features)
            features.update(triple_cross)

            # 11. 位置级联交叉特征（V24.0 扩展）
            lineup_cross = self._compute_lineup_cross_features(data, base_features)
            features.update(lineup_cross)

            # 12. 历史交互特征（V24.0 L3×L5 趋势爆破）
            historical_interaction = self._compute_historical_interaction_features(base_features)
            features.update(historical_interaction)

            # 13. 球员级别两两交叉特征（V24.0 核心爆破）
            player_pairwise = self._compute_player_pairwise_cross_features(data, base_features)
            features.update(player_pairwise)

            # 限制最大特征数量
            if len(features) > self.config.max_cross_features:
                # 保留前 max_cross_features 个特征
                features = dict(list(features.items())[: self.config.max_cross_features])
                warnings.append(f"Feature count capped at {self.config.max_cross_features}")

            result = ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "physical_cross_enabled": self.config.enable_physical_cross,
                    "tactical_cross_enabled": self.config.enable_tactical_cross,
                    "comparison_cross_enabled": self.config.enable_comparison_cross,
                    "temporal_cross_enabled": self.config.enable_temporal_cross,
                    "cartesian_cross_enabled": self.config.enable_cartesian_cross,
                    "polynomial_enabled": self.config.enable_polynomial_features,
                },
            )

            for warning in warnings:
                result.with_warning(warning)

            return result

        except Exception as e:
            logger.error(f"TacticalCrossProcessor failed: {e}")
            return ProcessorResult.failure_result(str(e))

    def _get_base_features(self, context: Any) -> dict[str, float]:
        """从 context 获取已提取的基础特征"""
        if context and hasattr(context, "get_cached"):
            cached = context.get_cached("base_features")
            if cached:
                return cached
        return {}

    def _extract_base_features_from_match(self, data: MatchData) -> dict[str, float]:
        """从 MatchData 直接提取基础特征"""
        features = {}

        for prefix, stats in [("home", data.home_stats), ("away", data.away_stats)]:
            if stats:
                features[f"{prefix}_expected_goals"] = float(stats.expected_goals or 0.0)
                features[f"{prefix}_shots_total"] = float(stats.shots_total or 0)
                features[f"{prefix}_shots_on_target"] = float(stats.shots_on_target or 0)
                features[f"{prefix}_possession"] = float(stats.possession or 0.0)
                features[f"{prefix}_total_passes"] = float(stats.total_passes or 0)
                features[f"{prefix}_accurate_passes"] = float(stats.accurate_passes or 0)
                features[f"{prefix}_team_rating"] = float(stats.team_rating or 0.0)
                features[f"{prefix}_corners"] = float(stats.corners or 0)
                features[f"{prefix}_fouls"] = float(stats.fouls or 0)
                features[f"{prefix}_offsides"] = float(stats.offsides or 0)

                # 动量数据
                if stats.momentum_scores:
                    momentum_scores = stats.momentum_scores
                    features[f"{prefix}_momentum_mean"] = float(statistics.mean(momentum_scores))

                    # V24.0: 生成高频动量特征（用于交叉）
                    segment_size = 15
                    num_segments = 6
                    for seg_idx in range(num_segments):
                        start_idx = seg_idx * segment_size
                        end_idx = min((seg_idx + 1) * segment_size, len(momentum_scores))
                        seg_scores = momentum_scores[start_idx:end_idx]
                        seg_num = seg_idx + 1

                        if len(seg_scores) >= 3:
                            features[f"{prefix}_m{seg_num}_mean"] = round(statistics.mean(seg_scores), 4)
                            # 计算速度
                            if len(seg_scores) >= 2:
                                diffs = [seg_scores[i] - seg_scores[i - 1] for i in range(1, len(seg_scores))]
                                features[f"{prefix}_m{seg_num}_velocity"] = round(statistics.mean(diffs), 4)
                            else:
                                features[f"{prefix}_m{seg_num}_velocity"] = 0.0
                            # 计算波动率
                            if len(seg_scores) > 1:
                                mean_val = statistics.mean(seg_scores)
                                features[f"{prefix}_m{seg_num}_volatility"] = round(
                                    statistics.stdev(seg_scores) / abs(mean_val) if mean_val != 0 else 0, 4
                                )
                            else:
                                features[f"{prefix}_m{seg_num}_volatility"] = 0.0
                        else:
                            features[f"{prefix}_m{seg_num}_mean"] = 0.0
                            features[f"{prefix}_m{seg_num}_velocity"] = 0.0
                            features[f"{prefix}_m{seg_num}_volatility"] = 0.0
                else:
                    features[f"{prefix}_momentum_mean"] = 0.0
                    # 填充默认高频动量特征
                    for seg in range(1, 7):
                        features[f"{prefix}_m{seg}_mean"] = 0.0
                        features[f"{prefix}_m{seg}_velocity"] = 0.0
                        features[f"{prefix}_m{seg}_volatility"] = 0.0

                features[f"{prefix}_lineup_stability"] = 0.8  # 默认值
                features[f"{prefix}_total_value"] = 500.0  # 默认值
                features[f"{prefix}_avg_value"] = 50.0  # 默认值
                features[f"{prefix}_bench_impact_potential"] = 0.5  # 默认值
                features[f"{prefix}_composite_health"] = 0.8  # 默认值
                features[f"{prefix}_pressure_score"] = 0.5  # 默认值
                features[f"{prefix}_tempo_score"] = 0.5  # 默认值

        # 对比特征
        features["diff_expected_goals"] = features.get("home_expected_goals", 0) - features.get(
            "away_expected_goals", 0
        )
        features["diff_shots_total"] = features.get("home_shots_total", 0) - features.get("away_shots_total", 0)
        features["diff_momentum_mean"] = features.get("home_momentum_mean", 0) - features.get("away_momentum_mean", 0)
        features["diff_total_value"] = features.get("home_total_value", 0) - features.get("away_total_value", 0)
        features["diff_lineup_stability"] = features.get("home_lineup_stability", 0) - features.get(
            "away_lineup_stability", 0
        )
        features["diff_composite_health"] = features.get("home_composite_health", 0) - features.get(
            "away_composite_health", 0
        )
        features["diff_pressure"] = features.get("home_pressure_score", 0) - features.get("away_pressure_score", 0)
        features["diff_team_rating"] = features.get("home_team_rating", 0) - features.get("away_team_rating", 0)

        return features

    def _compute_physical_cross(self, features: dict[str, float]) -> dict[str, float]:
        """计算物理交叉特征（约 150 维）"""
        cross_features = {}

        for prefix in ["home", "away"]:
            value = features.get(f"{prefix}_total_value", 0.0)
            avg_value = features.get(f"{prefix}_avg_value", 0.0)
            stability = features.get(f"{prefix}_lineup_stability", 0.5)
            health = features.get(f"{prefix}_composite_health", 0.5)
            bench = features.get(f"{prefix}_bench_impact_potential", 0.5)
            rating = features.get(f"{prefix}_team_rating", 7.0)

            # 身价 × 稳定性
            cross_features[f"{prefix}_value_stability_interaction"] = round(value * stability, 4)

            # 身价 × 健康度
            cross_features[f"{prefix}_value_health_product"] = round(value * health, 4)

            # 替补 × 稳定性
            cross_features[f"{prefix}_bench_stability_ratio"] = round(bench * stability, 4)

            # 平均身价 × 评分
            cross_features[f"{prefix}_value_rating_product"] = round(avg_value * rating, 4)

            # 稳定性 × 健康度
            cross_features[f"{prefix}_stability_health_product"] = round(stability * health, 4)

            # 身价效率
            if stability > 0:
                cross_features[f"{prefix}_value_efficiency"] = round(value / stability, 4)
            else:
                cross_features[f"{prefix}_value_efficiency"] = 0.0

            # 替补 × 健康度
            cross_features[f"{prefix}_bench_health_interaction"] = round(bench * health, 4)

            # 评分 × 稳定性
            cross_features[f"{prefix}_rating_stability_product"] = round(rating * stability, 4)

        return cross_features

    def _compute_tactical_cross(self, features: dict[str, float]) -> dict[str, float]:
        """计算战术交叉特征（约 200 维）"""
        cross_features = {}

        for prefix in ["home", "away"]:
            xg = features.get(f"{prefix}_expected_goals", 0.0)
            shots = features.get(f"{prefix}_shots_total", 1.0)
            shots_on_target = features.get(f"{prefix}_shots_on_target", 0.0)
            possession = features.get(f"{prefix}_possession", 50.0)
            total_passes = features.get(f"{prefix}_total_passes", 1.0)
            accurate_passes = features.get(f"{prefix}_accurate_passes", 0.0)
            rating = features.get(f"{prefix}_team_rating", 7.0)
            momentum = features.get(f"{prefix}_momentum_mean", 0.0)
            pressure = features.get(f"{prefix}_pressure_score", 0.5)
            tempo = features.get(f"{prefix}_tempo_score", 0.5)
            corners = features.get(f"{prefix}_corners", 0.0)
            fouls = features.get(f"{prefix}_fouls", 0.0)

            # xG 效率
            if shots > 0:
                cross_features[f"{prefix}_xg_efficiency"] = round(xg / shots, 4)
            else:
                cross_features[f"{prefix}_xg_efficiency"] = 0.0

            # 传球成功率
            if total_passes > 0:
                cross_features[f"{prefix}_pass_accuracy"] = round(accurate_passes / total_passes, 4)
            else:
                cross_features[f"{prefix}_pass_accuracy"] = 0.0

            # 压迫感 × 控球率
            cross_features[f"{prefix}_pressure_possession_product"] = round(pressure * (possession / 100.0), 4)

            # 动量 × 评分
            cross_features[f"{prefix}_momentum_rating_interaction"] = round(momentum * rating, 4)

            # 射门精度
            if shots > 0:
                cross_features[f"{prefix}_shot_accuracy"] = round(shots_on_target / shots, 4)
            else:
                cross_features[f"{prefix}_shot_accuracy"] = 0.0

            # 控球率 × 节奏
            cross_features[f"{prefix}_possession_tempo_product"] = round((possession / 100.0) * tempo, 4)

            # xG × 动量
            cross_features[f"{prefix}_attacking_firepower"] = round(xg * (momentum + 1.0), 4)

            # 传球 × 控球率
            cross_features[f"{prefix}_pass_possession_synergy"] = round(total_passes * (possession / 100.0), 4)

            # 角球 × 压迫感
            cross_features[f"{prefix}_set_piece_threat"] = round(corners * pressure, 4)

            # 犯规 × 压迫感
            cross_features[f"{prefix}_aggression_index"] = round(fouls * pressure, 4)

            # xG × 评分
            cross_features[f"{prefix}_xg_rating_product"] = round(xg * rating, 4)

            # 射门 × 动量
            cross_features[f"{prefix}_shots_momentum_product"] = round(shots * (momentum + 0.5), 4)

            # 控球率 × 动量
            cross_features[f"{prefix}_possession_momentum_synergy"] = round((possession / 100.0) * (momentum + 0.5), 4)

            # 传球精度 × 动量
            cross_features[f"{prefix}_pass_quality_momentum"] = round(
                (accurate_passes / total_passes if total_passes > 0 else 0) * (momentum + 0.5), 4
            )

            # 节奏 × 压迫感
            cross_features[f"{prefix}_tempo_pressure_intensity"] = round(tempo * pressure, 4)

            # 角球 × 评分
            cross_features[f"{prefix}_set_piece_quality"] = round(corners * rating, 4)

            # V24.0 扩展：更多战术交叉特征
            # xG / 评分比率
            cross_features[f"{prefix}_xg_per_rating"] = round(xg / rating if rating > 0 else 0, 4)

            # 射门 / 角球比率
            cross_features[f"{prefix}_shots_per_corner"] = round(shots / (corners + 1), 4)

            # 控球率 / 压迫感
            cross_features[f"{prefix}_possession_pressure_ratio"] = round((possession / 100.0) / (pressure + 0.1), 4)

            # 动量 × 越位
            offsides = features.get(f"{prefix}_offsides", 0.0)
            cross_features[f"{prefix}_momentum_offside_product"] = round(momentum * offsides, 4)

            # 传球精度平方
            pass_accuracy = accurate_passes / total_passes if total_passes > 0 else 0
            cross_features[f"{prefix}_pass_accuracy_sq"] = round(pass_accuracy**2, 6)

        return cross_features

    def _compute_comparison_cross(self, features: dict[str, float]) -> dict[str, float]:
        """计算对比交叉特征（约 100 维）"""
        cross_features = {}

        value_diff = features.get("diff_total_value", 0.0)
        stability_diff = features.get("diff_lineup_stability", 0.0)
        xg_diff = features.get("diff_expected_goals", 0.0)
        shots_diff = features.get("diff_shots_total", 0.0)
        momentum_diff = features.get("diff_momentum_mean", 0.0)
        health_diff = features.get("diff_composite_health", 0.0)
        pressure_diff = features.get("diff_pressure", 0.0)
        rating_diff = features.get("diff_team_rating", 0.0)

        # 差值 × 差值交叉
        cross_features["value_pressure_cross"] = round(value_diff * pressure_diff, 4)
        cross_features["stability_momentum_cross"] = round(stability_diff * momentum_diff, 4)
        cross_features["xg_shots_cross_diff"] = round(xg_diff * shots_diff, 4)
        cross_features["health_rating_cross_diff"] = round(health_diff * rating_diff, 4)
        cross_features["value_xg_cross_advantage"] = round(value_diff * xg_diff, 4)
        cross_features["stability_pressure_cross"] = round(stability_diff * pressure_diff, 4)
        cross_features["momentum_rating_cross_diff"] = round(momentum_diff * rating_diff, 4)
        cross_features["health_xg_resilience"] = round(health_diff * xg_diff, 4)

        # 场馆因子
        match_importance = features.get("match_importance", 0.5)
        cross_features["stadium_choke_factor"] = round(match_importance * abs(value_diff), 4)
        cross_features["stadium_pressure_magnifier"] = round(match_importance * abs(pressure_diff), 4)

        # 综合优势指数
        cross_features["tactical_dominance"] = round((pressure_diff + momentum_diff) / 2.0, 4)
        cross_features["comprehensive_advantage"] = round(
            (value_diff / 1000.0) + stability_diff + health_diff + xg_diff, 4
        )

        return cross_features

    def _compute_temporal_cross(self, features: dict[str, float]) -> dict[str, float]:
        """计算时序交叉特征（约 50 维）"""
        cross_features = {}

        for prefix in ["home", "away"]:
            # L3 × L5 交叉
            l3_xg = features.get(f"{prefix}_l3_expected_goals_mean", 0.0)
            l5_xg_trend = features.get(f"{prefix}_l5_expected_goals_trend", 0.0)
            l3_win_rate = features.get(f"{prefix}_l3_win_rate", 0.5)
            l3_rating = features.get(f"{prefix}_l3_team_rating_mean", 7.0)
            stability = features.get(f"{prefix}_lineup_stability", 0.5)

            cross_features[f"{prefix}_xg_momentum_cross"] = round(l3_xg * (l5_xg_trend + 1.0), 4)
            cross_features[f"{prefix}_form_consistency"] = round(l3_win_rate * (l5_xg_trend + 1.0), 4)
            cross_features[f"{prefix}_rating_stability_cross"] = round(l3_rating * stability, 4)
            cross_features[f"{prefix}_temporal_momentum"] = round(l3_xg * l3_win_rate, 4)

        return cross_features

    def _compute_cartesian_cross(self, features: dict[str, float]) -> dict[str, float]:
        """
        全量笛卡尔积交叉（V24.0 核心爆破）

        对所有核心因子进行两两交叉组合，生成约 800 维特征
        """
        cross_features = {}

        # 为每个队伍计算笛卡尔积交叉
        for prefix in ["home", "away"]:
            # 提取当前队伍的所有因子值
            factor_values = {}
            for factor in self.CORE_FACTORS:
                key = f"{prefix}_{factor}"
                if key in features:
                    factor_values[factor] = features[key]

            # 对所有因子对进行交叉（笛卡尔积）
            for i, (factor1, val1) in enumerate(factor_values.items()):
                for factor2, val2 in list(factor_values.items())[i + 1 :]:
                    # 只计算有意义的不同因子交叉
                    if factor1 != factor2:
                        # 乘积交叉
                        cross_features[f"{prefix}_{factor1}_x_{factor2}"] = round(val1 * val2, 4)

                        # 比率交叉（如果分母不为零）
                        if abs(val2) > 0.001:
                            cross_features[f"{prefix}_{factor1}_div_{factor2}"] = round(val1 / val2, 4)

        # 主客队因子交叉
        home_factors = {}
        away_factors = {}
        for factor in self.CORE_FACTORS:
            home_key = f"home_{factor}"
            away_key = f"away_{factor}"
            if home_key in features:
                home_factors[factor] = features[home_key]
            if away_key in features:
                away_factors[factor] = features[away_key]

        # 主客队因子两两交叉
        for factor1, home_val in home_factors.items():
            for factor2, away_val in away_factors.items():
                cross_features[f"home_{factor1}_x_away_{factor2}"] = round(home_val * away_val, 4)

        return cross_features

    def _compute_polynomial_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算多项式特征（平方、立方）

        生成约 300 维特征
        """
        poly_features = {}

        # 对关键指标计算多项式特征
        poly_keys = [
            "home_expected_goals",
            "away_expected_goals",
            "home_shots_total",
            "away_shots_total",
            "home_possession",
            "away_possession",
            "home_total_value",
            "away_total_value",
            "home_momentum_mean",
            "away_momentum_mean",
            "home_pressure_score",
            "away_pressure_score",
            "home_team_rating",
            "away_team_rating",
        ]

        for key in poly_keys:
            value = features.get(key, 0.0)

            # 平方
            poly_features[f"square_{key}"] = round(value**2, 4)

            # 立方（对于较大的值，先归一化）
            normalized = value / 100.0 if abs(value) > 10 else value
            poly_features[f"cube_{key}"] = round(normalized**3, 4)

            # 平方根
            poly_features[f"sqrt_{key}"] = round(math.sqrt(abs(value)), 4)

        return poly_features

    def _compute_nonlinear_transforms(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算非线性变换特征

        生成约 200 维特征
        """
        nonlinear_features = {}

        # 对所有核心指标应用非线性变换
        for prefix in ["home", "away"]:
            for factor in ["expected_goals", "shots_total", "possession", "total_passes", "total_value"]:
                key = f"{prefix}_{factor}"
                value = features.get(key, 0.0)

                # Log 变换
                nonlinear_features[f"log_{key}"] = round(math.log(abs(value) + 1.0), 4)

                # Sigmoid 变换
                nonlinear_features[f"sigmoid_{key}"] = round(1.0 / (1.0 + math.exp(-value / 10.0)), 4)

                # Tanh 变换
                nonlinear_features[f"tanh_{key}"] = round(math.tanh(value / 20.0), 4)

        return nonlinear_features

    def _compute_higher_degree_polynomials(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算高阶多项式特征（V24.0 扩展）

        生成约 600 维特征
        """
        poly_features = {}

        # 对关键指标计算更高阶的多项式特征
        poly_keys = [
            "home_expected_goals",
            "away_expected_goals",
            "home_shots_total",
            "away_shots_total",
            "home_possession",
            "away_possession",
            "home_total_value",
            "away_total_value",
            "home_momentum_mean",
            "away_momentum_mean",
            "home_pressure_score",
            "away_pressure_score",
        ]

        for key in poly_keys:
            value = features.get(key, 0.0)

            # 四次方
            normalized = value / 100.0 if abs(value) > 10 else value / 10.0
            poly_features[f"quad_{key}"] = round(normalized**4, 6)

            # 指数变换（exp 归一化后的值）
            try:
                poly_features[f"exp_{key}"] = round(math.exp(abs(normalized) * 0.1) - 1, 4)
            except OverflowError:
                poly_features[f"exp_{key}"] = 0.0

            # 对数平方
            poly_features[f"logsquare_{key}"] = round(
                (math.log(abs(value) + 1.0) ** 2) if abs(value) > 0.01 else 0.0, 4
            )

        # 添加更多交叉多项式特征
        for prefix in ["home", "away"]:
            xg = features.get(f"{prefix}_expected_goals", 0.0)
            shots = features.get(f"{prefix}_shots_total", 1.0)
            possession = features.get(f"{prefix}_possession", 50.0)
            momentum = features.get(f"{prefix}_momentum_mean", 0.0)
            rating = features.get(f"{prefix}_team_rating", 7.0)
            corners = features.get(f"{prefix}_corners", 0.0)

            # xG × 射门的平方
            poly_features[f"{prefix}_xg_shots_squared"] = round(xg * (shots**2) / 100, 4)

            # 控球率 × 动量的平方
            poly_features[f"{prefix}_possession_momentum_squared"] = round(
                (possession / 100.0) * ((momentum + 0.5) ** 2), 4
            )

            # xG 的平方根 × 动量
            poly_features[f"{prefix}_sqrt_xg_momentum"] = round(math.sqrt(abs(xg)) * (momentum + 0.5), 4)

            # V24.0 扩展：更多交叉多项式
            # xG × 评分 × 控球率
            poly_features[f"{prefix}_xg_rating_possession"] = round(xg * rating * (possession / 100.0), 4)

            # 射门效率（射门 × 评分）
            poly_features[f"{prefix}_shots_rating_efficiency"] = round(shots * rating / 10.0, 4)

            # 角球 × 控球率
            poly_features[f"{prefix}_corners_possession_product"] = round(corners * possession / 100.0, 4)

            # xG 立方根 × 动量立方
            poly_features[f"{prefix}_cbrt_xg_momentum_cubed"] = round((abs(xg) ** (1 / 3)) * ((momentum + 0.5) ** 3), 6)

            # 控球率平方 × xG 平方
            poly_features[f"{prefix}_possession_sq_xg_sq"] = round(((possession / 100.0) ** 2) * (xg**2), 6)

            # 评分 × 动量的绝对值
            poly_features[f"{prefix}_rating_momentum_abs"] = round(rating * abs(momentum), 4)

            # xG / 射门比率平方
            if shots > 0:
                poly_features[f"{prefix}_xg_per_shot_sq"] = round((xg / shots) ** 2, 6)
            else:
                poly_features[f"{prefix}_xg_per_shot_sq"] = 0.0

        # 主客队对比多项式
        home_xg = features.get("home_expected_goals", 0.0)
        away_xg = features.get("away_expected_goals", 0.0)
        home_possession = features.get("home_possession", 50.0)
        away_possession = features.get("away_possession", 50.0)

        # xG 差值平方
        poly_features["diff_xg_squared"] = round((home_xg - away_xg) ** 2, 6)

        # 控球率差值 × xG 差值
        poly_features["diff_possession_x_diff_xg"] = round(
            (home_possession - away_possession) * (home_xg - away_xg) / 100.0, 4
        )

        # xG 和 × 控球率和
        poly_features["sum_xg_x_sum_possession"] = round(
            (home_xg + away_xg) * ((home_possession + away_possession) / 100.0), 4
        )

        # xG 比率（如果 away_xg > 0）
        if away_xg > 0.001:
            poly_features["ratio_home_xg_away_xg"] = round(home_xg / away_xg, 4)
        else:
            poly_features["ratio_home_xg_away_xg"] = 1.0

        return poly_features

    def _compute_momentum_cross_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算高频动量交叉特征（V24.0 扩展）

        生成约 500 维特征
        """
        cross_features = {}

        for prefix in ["home", "away"]:
            # 获取高频动量数据
            momentum_data = {}
            for m_factor in self.HIGH_FREQ_MOMENTUM_FACTORS:
                key = f"{prefix}_{m_factor}"
                if key in features:
                    momentum_data[m_factor] = features[key]

            # 获取战术数据
            tactical_keys = ["expected_goals", "shots_total", "possession", "team_rating"]
            tactical_data = {}
            for t_key in tactical_keys:
                key = f"{prefix}_{t_key}"
                if key in features:
                    tactical_data[t_key] = features[key]

            # 动量 × 战术交叉
            for m_name, m_val in momentum_data.items():
                for t_name, t_val in tactical_data.items():
                    # 乘积交叉
                    cross_features[f"{prefix}_{m_name}_x_{t_name}"] = round(m_val * t_val, 4)

                    # 比率交叉
                    if abs(t_val) > 0.001:
                        cross_features[f"{prefix}_{m_name}_div_{t_name}"] = round(m_val / t_val, 4)

            # 动量时段对比（上半场 vs 下半场）
            fh_momentum = (
                momentum_data.get("m1_mean", 0) + momentum_data.get("m2_mean", 0) + momentum_data.get("m3_mean", 0)
            )
            sh_momentum = (
                momentum_data.get("m4_mean", 0) + momentum_data.get("m5_mean", 0) + momentum_data.get("m6_mean", 0)
            )

            cross_features[f"{prefix}_fh_sh_momentum_ratio"] = round(fh_momentum / (sh_momentum + 0.001), 4)

            # 动量波动率 × xG
            xg = tactical_data.get("expected_goals", 0.0)
            total_volatility = sum(
                momentum_data.get(k, 0)
                for k in [
                    "m1_volatility",
                    "m2_volatility",
                    "m3_volatility",
                    "m4_volatility",
                    "m5_volatility",
                    "m6_volatility",
                ]
            )
            cross_features[f"{prefix}_momentum_volatility_xg_product"] = round(total_volatility * xg, 4)

        # 主客队动量时段对比
        for seg in [1, 2, 3, 4, 5, 6]:
            home_m = features.get(f"home_m{seg}_mean", 0.0)
            away_m = features.get(f"away_m{seg}_mean", 0.0)
            cross_features[f"diff_m{seg}_mean_product"] = round(home_m * away_m, 4)

        return cross_features

    def _compute_triple_cross_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算三阶交叉特征（三个因子的交互）

        生成约 400 维特征
        """
        cross_features = {}

        # 关键三因子组合
        triple_combinations = [
            ("expected_goals", "shots_total", "possession"),
            ("expected_goals", "momentum_mean", "pressure_score"),
            ("shots_total", "team_rating", "lineup_stability"),
            ("total_value", "composite_health", "momentum_mean"),
            ("possession", "tempo_score", "pressure_score"),
            ("total_passes", "possession", "team_rating"),
            ("xg_efficiency", "shot_accuracy", "momentum_mean"),
            ("bench_impact_potential", "lineup_stability", "total_value"),
        ]

        for prefix in ["home", "away"]:
            for combo in triple_combinations:
                values = []
                for factor in combo:
                    key = f"{prefix}_{factor}"
                    # 处理衍生特征（如 xg_efficiency）
                    if key not in features:
                        # 尝试计算衍生值
                        if factor == "xg_efficiency":
                            xg = features.get(f"{prefix}_expected_goals", 0.0)
                            shots = features.get(f"{prefix}_shots_total", 1.0)
                            val = xg / shots if shots > 0 else 0.0
                        elif factor == "shot_accuracy":
                            shots_on = features.get(f"{prefix}_shots_on_target", 0.0)
                            shots = features.get(f"{prefix}_shots_total", 1.0)
                            val = shots_on / shots if shots > 0 else 0.0
                        else:
                            val = 0.0
                    else:
                        val = features[key]
                    values.append(val)

                # 三阶乘积
                combo_name = "_x_".join(combo)
                cross_features[f"{prefix}_triple_{combo_name}"] = round(values[0] * values[1] * values[2], 6)

                # 归一化三阶乘积
                normalized_vals = [v / 100.0 if abs(v) > 100 else v for v in values]
                cross_features[f"{prefix}_triple_norm_{combo_name}"] = round(
                    normalized_vals[0] * normalized_vals[1] * normalized_vals[2], 6
                )

        # 主客队三阶交叉（主队因子 × 客队因子 × 主队因子）
        key_factors = ["expected_goals", "shots_total", "possession"]
        for f1 in key_factors:
            for f2 in key_factors:
                home_v1 = features.get(f"home_{f1}", 0.0)
                away_v2 = features.get(f"away_{f2}", 0.0)
                home_v3 = features.get(f"home_{f1}", 0.0)

                cross_features[f"home_{f1}_x_away_{f2}_x_home_{f1}"] = round(home_v1 * away_v2 * home_v3, 6)

        return cross_features

    def _compute_lineup_cross_features(self, data: MatchData, base_features: dict[str, float]) -> dict[str, float]:
        """
        计算阵容位置级联交叉特征（V24.0 扩展）

        生成约 600 维特征
        """
        cross_features = {}

        for prefix, lineup in [("home", data.home_lineup), ("away", data.away_lineup)]:
            if not lineup or not lineup.players:
                continue

            # 按位置分组
            positions = {
                "gk": [],
                "df": [],
                "mf": [],
                "fw": [],
            }

            for p in lineup.players:
                if not p.is_starter:
                    continue
                jersey = p.jersey_number or 99
                if jersey == 1:
                    positions["gk"].append(p)
                elif 2 <= jersey <= 6:
                    positions["df"].append(p)
                elif jersey in [6, 8, 10]:
                    positions["mf"].append(p)
                elif jersey in [7, 9, 11]:
                    positions["fw"].append(p)
                else:
                    positions["mf"].append(p)

            # 获取战术因子
            xg = base_features.get(f"{prefix}_expected_goals", 0.0)
            shots = base_features.get(f"{prefix}_shots_total", 1.0)
            possession = base_features.get(f"{prefix}_possession", 50.0)

            # 位置统计 × 战术因子交叉
            for pos_name, pos_players in positions.items():
                if pos_players:
                    pos_xg = sum(p.expected_goals or 0.0 for p in pos_players)
                    pos_shots = sum(p.total_shots or 0 for p in pos_players)
                    pos_rating = sum(p.team_rating or 7.0 for p in pos_players) / len(pos_players)
                    pos_value = sum(p.market_value or 0.0 for p in pos_players)

                    # 位置 xG × 总体 xG
                    cross_features[f"{prefix}_{pos_name}_xg_x_total_xg"] = round(pos_xg * xg, 4)

                    # 位置射门 × 总体射门
                    cross_features[f"{prefix}_{pos_name}_shots_x_total_shots"] = round(pos_shots * shots, 4)

                    # 位置评分 × 总体评分
                    team_rating = base_features.get(f"{prefix}_team_rating", 7.0)
                    cross_features[f"{prefix}_{pos_name}_rating_x_team_rating"] = round(pos_rating * team_rating, 4)

                    # 位置身价 × 控球率
                    cross_features[f"{prefix}_{pos_name}_value_x_possession"] = round(
                        pos_value * (possession / 100.0), 4
                    )

                    # 位置效率指标
                    if shots > 0:
                        cross_features[f"{prefix}_{pos_name}_xg_per_total_shot"] = round(pos_xg / shots, 4)

                    # 位置价值占比
                    total_value = base_features.get(f"{prefix}_total_value", 1.0)
                    if total_value > 0:
                        cross_features[f"{prefix}_{pos_name}_value_ratio"] = round(pos_value / total_value, 4)

            # 位置间交叉
            if positions["gk"] and positions["df"]:
                gk_rating = statistics.mean([p.team_rating or 7.0 for p in positions["gk"]])
                df_rating = statistics.mean([p.team_rating or 7.0 for p in positions["df"]])
                cross_features[f"{prefix}_gk_df_rating_synergy"] = round(gk_rating * df_rating, 4)

            if positions["mf"] and positions["fw"]:
                mf_rating = statistics.mean([p.team_rating or 7.0 for p in positions["mf"]])
                fw_rating = statistics.mean([p.team_rating or 7.0 for p in positions["fw"]])
                cross_features[f"{prefix}_mf_fw_rating_synergy"] = round(mf_rating * fw_rating, 4)

            # 防守深度 × 进攻深度
            df_xg = sum(p.expected_goals or 0.0 for p in positions["df"]) if positions["df"] else 0.0
            fw_xg = sum(p.expected_goals or 0.0 for p in positions["fw"]) if positions["fw"] else 0.0
            cross_features[f"{prefix}_df_fw_xg_cross"] = round(df_xg * fw_xg, 6)

            # 中场控制 × 边路威胁
            mf_passes = sum(p.accurate_passes or 0 for p in positions["mf"]) if positions["mf"] else 0.0
            fw_shots = sum(p.total_shots or 0 for p in positions["fw"]) if positions["fw"] else 0.0
            cross_features[f"{prefix}_mf_fw_control_threat"] = round(mf_passes * fw_shots, 4)

        # 主客队位置交叉
        for pos in ["gk", "df", "mf", "fw"]:
            home_xg = base_features.get(f"home_{pos}_xg", 0.0)
            away_xg = base_features.get(f"away_{pos}_xg", 0.0)
            cross_features[f"diff_{pos}_xg_product"] = round(home_xg * away_xg, 4)

        return cross_features

    def _compute_player_pairwise_cross_features(
        self, data: MatchData, base_features: dict[str, float]
    ) -> dict[str, float]:
        """
        计算球员级别两两交叉特征（V24.0 核心爆破）

        生成约 800 维特征（11名首发球员 × 11名首发球员的交互）
        """
        cross_features = {}

        for prefix, lineup in [("home", data.home_lineup), ("away", data.away_lineup)]:
            if not lineup or not lineup.players:
                continue

            # 提取首发球员
            starters = [p for p in lineup.players if p.is_starter][:11]

            if len(starters) < 2:
                continue

            # 球员数据矩阵
            player_data = []
            for i, p in enumerate(starters):
                player_data.append(
                    {
                        "index": i,
                        "rating": p.team_rating or 7.0,
                        "value": p.market_value or 0.0,
                        "age": p.age or 25,
                        "xg": p.expected_goals or 0.0,
                        "shots": p.total_shots or 0,
                        "passes": p.accurate_passes or 0,
                        "touches": p.touches or 0,
                    }
                )

            # 两两交叉（上限前 11 × 11 = 121 对组合）
            max_pairs = 121
            pair_count = 0

            for i in range(len(player_data)):
                for j in range(i + 1, len(player_data)):
                    if pair_count >= max_pairs:
                        break

                    p1 = player_data[i]
                    p2 = player_data[j]

                    # 评分 × 评分
                    cross_features[f"{prefix}_p{p1['index']}_rating_x_p{p2['index']}_rating"] = round(
                        p1["rating"] * p2["rating"], 4
                    )

                    # 身价 × 身价
                    cross_features[f"{prefix}_p{p1['index']}_value_x_p{p2['index']}_value"] = round(
                        p1["value"] * p2["value"], 4
                    )

                    # xG × xG
                    cross_features[f"{prefix}_p{p1['index']}_xg_x_p{p2['index']}_xg"] = round(p1["xg"] * p2["xg"], 6)

                    # 评分和 × 身价和
                    cross_features[f"{prefix}_p{p1['index']}_rating_sum_x_value_sum"] = round(
                        (p1["rating"] + p2["rating"]) * (p1["value"] + p2["value"]), 4
                    )

                    # 触球差值
                    touches_diff = abs(p1["touches"] - p2["touches"])
                    cross_features[f"{prefix}_p{p1['index']}_p{p2['index']}_touches_diff"] = round(touches_diff, 4)

                    # 年龄跨度
                    age_diff = abs(p1["age"] - p2["age"])
                    cross_features[f"{prefix}_p{p1['index']}_p{p2['index']}_age_diff"] = round(age_diff, 4)

                    # 综合实力评分（评分 + 身价）
                    strength1 = p1["rating"] + p1["value"] / 100.0
                    strength2 = p2["rating"] + p2["value"] / 100.0
                    cross_features[f"{prefix}_p{p1['index']}_strength_x_p{p2['index']}_strength"] = round(
                        strength1 * strength2, 4
                    )

                    # 传球配合
                    passes_synergy = (p1["passes"] + p2["passes"]) / 2.0
                    cross_features[f"{prefix}_p{p1['index']}_p{p2['index']}_passes_synergy"] = round(passes_synergy, 4)

                    pair_count += 1

        # 主客队对应位置交叉
        home_lineup = data.home_lineup
        away_lineup = data.away_lineup

        if home_lineup and away_lineup and home_lineup.players and away_lineup.players:
            home_starters = [p for p in home_lineup.players if p.is_starter][:11]
            away_starters = [p for p in away_lineup.players if p.is_starter][:11]

            min_len = min(len(home_starters), len(away_starters))

            for i in range(min_len):
                home_p = home_starters[i]
                away_p = away_starters[i]

                # 对应位置评分交叉
                cross_features[f"home_p{i}_rating_x_away_p{i}_rating"] = round(
                    (home_p.team_rating or 7.0) * (away_p.team_rating or 7.0), 4
                )

                # 对应位置身价交叉
                cross_features[f"home_p{i}_value_x_away_p{i}_value"] = round(
                    (home_p.market_value or 0.0) * (away_p.market_value or 0.0), 4
                )

                # 对应位置 xG 交叉
                cross_features[f"home_p{i}_xg_x_away_p{i}_xg"] = round(
                    (home_p.expected_goals or 0.0) * (away_p.expected_goals or 0.0), 6
                )

        return cross_features

    def _compute_historical_interaction_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算历史交互特征（V24.0 L3×L5 趋势爆破）

        将 L3 滚动统计与 L5 趋势进行交互组合，生成约 400+ 维特征
        """
        cross_features = {}

        # 核心指标列表（与 HistoricalRollingProcessor 保持一致）
        hist_metrics = [
            "expected_goals",
            "shots_total",
            "shots_on_target",
            "possession",
            "total_passes",
            "accurate_passes",
            "team_rating",
            "corners",
            "fouls",
            "offsides",
        ]

        for prefix in ["home", "away"]:
            # L3 × L5 交互特征
            for metric in hist_metrics:
                l3_mean_key = f"{prefix}_l3_{metric}_mean"
                l3_std_key = f"{prefix}_l3_{metric}_std"
                l5_trend_key = f"{prefix}_l5_{metric}_trend"

                l3_mean = features.get(l3_mean_key, 0.0)
                l3_std = features.get(l3_std_key, 0.0)
                l5_trend = features.get(l5_trend_key, 0.0)

                # L3 均值 × L5 趋势
                cross_features[f"{prefix}_{metric}_l3mean_x_l5trend"] = round(l3_mean * l5_trend, 4)

                # L3 标准差 × L5 趋势
                cross_features[f"{prefix}_{metric}_l3std_x_l5trend"] = round(l3_std * l5_trend, 4)

                # L3 均值 × L3 标准差（波动 × 水平）
                cross_features[f"{prefix}_{metric}_l3mean_x_l3std"] = round(l3_mean * l3_std, 4)

                # L3 变异系数 × L5 趋势
                l3_cv = features.get(f"{prefix}_l3_{metric}_cv", 0.0)
                cross_features[f"{prefix}_{metric}_l3cv_x_l5trend"] = round(l3_cv * l5_trend, 4)

                # 趋势加速度（L5 趋势的平方）
                cross_features[f"{prefix}_{metric}_trend_acceleration"] = round(l5_trend**2, 6)

                # L3 均值的平方 × L5 趋势
                cross_features[f"{prefix}_{metric}_l3mean_sq_x_l5trend"] = round((l3_mean**2) * l5_trend, 6)

                # L3 趋势一致性（均值与趋势的相关性模拟）
                if l3_mean != 0:
                    cross_features[f"{prefix}_{metric}_trend_consistency"] = round(l5_trend / abs(l3_mean), 4)
                else:
                    cross_features[f"{prefix}_{metric}_trend_consistency"] = 0.0

            # H2H × L3 交互特征
            for metric in ["expected_goals", "shots_total", "shots_on_target", "possession"]:
                h2h_mean_key = f"{prefix}_h2h_{metric}_mean"
                l3_mean_key = f"{prefix}_l3_{metric}_mean"

                h2h_mean = features.get(h2h_mean_key, 0.0)
                l3_mean = features.get(l3_mean_key, 0.0)

                # H2H 均值 × L3 均值
                cross_features[f"{prefix}_{metric}_h2h_x_l3"] = round(h2h_mean * l3_mean, 4)

                # H2H 与 L3 的差值
                cross_features[f"{prefix}_{metric}_h2h_diff_l3"] = round(h2h_mean - l3_mean, 4)

                # H2H / L3 比率（如果 L3 不为零）
                if abs(l3_mean) > 0.001:
                    cross_features[f"{prefix}_{metric}_h2h_div_l3"] = round(h2h_mean / l3_mean, 4)
                else:
                    cross_features[f"{prefix}_{metric}_h2h_div_l3"] = 0.0

            # L3 胜率 × L5 xG 趋势交互
            l3_win_rate = features.get(f"{prefix}_l3_win_rate", 0.5)
            l5_xg_trend = features.get(f"{prefix}_l5_expected_goals_trend", 0.0)

            cross_features[f"{prefix}_winrate_x_xgtrend"] = round(l3_win_rate * l5_xg_trend, 4)
            cross_features[f"{prefix}_winrate_plus_xgtrend"] = round(l3_win_rate + l5_xg_trend, 4)

            # L3 进球均值 × L5 射门趋势
            l3_goals_mean = features.get(f"{prefix}_l3_goals_scored_mean", 0.0)
            l5_shots_trend = features.get(f"{prefix}_l5_shots_total_trend", 0.0)

            cross_features[f"{prefix}_goals_x_shotstrend"] = round(l3_goals_mean * l5_shots_trend, 4)
            cross_features[f"{prefix}_goals_div_shotstrend"] = round(
                l3_goals_mean / abs(l5_shots_trend) if abs(l5_shots_trend) > 0.001 else 0.0, 4
            )

        # 主客队历史对比交互
        # L3 xG 对比 × L5 xG 趋势对比
        home_l3_xg = features.get("home_l3_expected_goals_mean", 0.0)
        away_l3_xg = features.get("away_l3_expected_goals_mean", 0.0)
        home_l5_xg_trend = features.get("home_l5_expected_goals_trend", 0.0)
        away_l5_xg_trend = features.get("away_l5_expected_goals_trend", 0.0)

        # 主客队 L3 均值差 × L5 趋势差
        l3_xg_diff = home_l3_xg - away_l3_xg
        l5_trend_diff = home_l5_xg_trend - away_l5_xg_trend
        cross_features["diff_l3_xg_x_l5_trend"] = round(l3_xg_diff * l5_trend_diff, 4)

        # 主客队 L3 标准差交互
        home_l3_xg_std = features.get("home_l3_expected_goals_std", 0.0)
        away_l3_xg_std = features.get("away_l3_expected_goals_std", 0.0)
        cross_features["product_l3_xg_std"] = round(home_l3_xg_std * away_l3_xg_std, 4)
        cross_features["diff_l3_xg_std"] = round(home_l3_xg_std - away_l3_xg_std, 4)

        # H2H 胜率 × L3 胜率差交互
        home_h2h_win_rate = features.get("home_h2h_win_rate", 0.5)
        away_h2h_win_rate = features.get("away_h2h_win_rate", 0.5)
        home_l3_win_rate = features.get("home_l3_win_rate", 0.5)
        away_l3_win_rate = features.get("away_l3_win_rate", 0.5)

        h2h_win_rate_diff = home_h2h_win_rate - away_h2h_win_rate
        l3_win_rate_diff = home_l3_win_rate - away_l3_win_rate
        cross_features["h2h_winrate_x_l3_winrate"] = round(h2h_win_rate_diff * l3_win_rate_diff, 4)

        # 历史综合评分（L3 + L5 + H2H）
        for prefix in ["home", "away"]:
            l3_xg_mean = features.get(f"{prefix}_l3_expected_goals_mean", 0.0)
            l5_xg_trend = features.get(f"{prefix}_l5_expected_goals_trend", 0.0)
            h2h_xg_mean = features.get(f"{prefix}_h2h_expected_goals_mean", 0.0)

            # 综合历史 xG 评分（加权组合）
            cross_features[f"{prefix}_composite_hist_xg"] = round(
                0.5 * l3_xg_mean + 0.3 * (l5_xg_trend + 1.0) + 0.2 * h2h_xg_mean, 4
            )

            # L3 × H2H 交互
            cross_features[f"{prefix}_l3_xg_x_h2h_xg"] = round(l3_xg_mean * h2h_xg_mean, 4)

        return cross_features

    def get_feature_schema(self) -> dict[str, type]:
        """获取输出特征的 Schema（V24.0 动态生成）"""
        # 由于特征数量巨大且动态生成，这里只返回部分关键特征
        schema = {}

        prefixes = ["home", "away"]

        # 物理交叉
        for prefix in prefixes:
            schema[f"{prefix}_value_stability_interaction"] = float
            schema[f"{prefix}_value_health_product"] = float
            schema[f"{prefix}_bench_stability_ratio"] = float

        # 战术交叉
        for prefix in prefixes:
            schema[f"{prefix}_xg_efficiency"] = float
            schema[f"{prefix}_pass_accuracy"] = float
            schema[f"{prefix}_pressure_possession_product"] = float

        # 对比交叉
        schema["value_pressure_cross"] = float
        schema["stadium_choke_factor"] = float

        # 多项式特征
        for prefix in prefixes:
            schema[f"square_{prefix}_expected_goals"] = float
            schema[f"sqrt_{prefix}_shots_total"] = float

        # 非线性特征
        for prefix in prefixes:
            schema[f"log_{prefix}_expected_goals"] = float
            schema[f"sigmoid_{prefix}_shots_total"] = float

        return schema
