"""
TacticalProcessor - 战术聚合处理器（V23.0 高频化版）
====================================================

负责提取战术层面特征，包括:
    - 动量分析（速度、加速度、波动率）
    - 射门位置聚合（半场/全场合成）
    - 高级战术指标（压迫感、节奏）
    - **V23.0 新增**: 战术动量高频化（6时段 × 10维 × 2队 = 120维）

设计模式:
    - 聚合模式: 从多个数据源聚合战术指标
    - 时序分析: 分析比赛过程中的动态变化
    - 分段统计: 将全场分为 6 个时段独立分析（V23.0）
    - 维度合成: 将半场数据合成为全场指标

作者: FootballPrediction Architecture Team
版本: V23.0-final
"""

import logging
import statistics
from typing import Any

from src.ml.feature_engine.base import BaseProcessor, ProcessorConfig, ProcessorResult
from src.ml.feature_engine.models import MatchData, TeamStats

logger = logging.getLogger(__name__)


class TacticalProcessorConfig(ProcessorConfig):
    """
    TacticalProcessor 配置

    Attributes:
        enable_momentum_analysis: 是否启用动量分析
        enable_shot_aggregation: 是否启用射门聚合
        enable_highfreq_momentum: 是否启用高频动量分析（V23.0）
        volatility_window: 动量波动率计算窗口
        min_momentum_samples: 最小动量样本数
        time_segments: 时间分段数量（V23.0）
    """

    enable_momentum_analysis: bool = True
    enable_shot_aggregation: bool = True
    enable_highfreq_momentum: bool = True  # V23.0 新增
    volatility_window: int = 5
    min_momentum_samples: int = 3
    time_segments: int = 6  # 将 90 分钟分为 6 个时段（每 15 分钟）


class TacticalProcessor(BaseProcessor[MatchData]):
    """
    战术聚合处理器（V23.0 高频化版）

    职责:
        1. 分析球队动量（速度、加速度）
        2. 聚合半场射门数据
        3. 计算战术压迫感指标
        4. 评估比赛节奏
        5. **V23.0**: 高频动量分析（6 个时段独立展开）

    特征输出（150+ 维）:
        # 聚合维度（约 30 维）
        - home_momentum_mean, away_momentum_mean: 平均动量
        - home_momentum_velocity, away_momentum_velocity: 动量速度
        - home_momentum_volatility, away_momentum_volatility: 动量波动率
        ...

        # V23.0 高频动量维度（120 维）
        - home_m1_mean, home_m1_velocity, home_m1_volatility, ... (时段 1)
        - home_m2_mean, home_m2_velocity, home_m2_volatility, ... (时段 2)
        ...
        - home_m6_mean, home_m6_velocity, home_m6_volatility, ... (时段 6)
        - (away 队同样 6 个时段)

        每个时段的 10 个动量因子:
            1. mean: 平均动量
            2. std: 标准差
            3. max: 最大动量
            4. min: 最小动量
            5. velocity: 动量速度
            6. acceleration: 动量加速度
            7. volatility: 波动率
            8. neg_velocity: 负向速度
            9. trend: 线性趋势
            10. dominance: 支配度（正值占比）

        时段划分:
            - m1: 0-15 分钟
            - m2: 15-30 分钟
            - m3: 30-45 分钟
            - m4: 45-60 分钟
            - m5: 60-75 分钟
            - m6: 75-90 分钟
    """

    processor_name = "TacticalProcessor"
    processor_version = "23.0.0"
    priority = 20

    def __init__(self, config: TacticalProcessorConfig | None = None) -> None:
        super().__init__(config or TacticalProcessorConfig())
        self.config: TacticalProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """提取战术聚合特征"""
        features: dict[str, float] = {}
        warnings: list[str] = []

        try:
            # 1. 传统聚合动量分析（向后兼容）
            if self.config.enable_momentum_analysis:
                home_momentum = self._analyze_momentum(data.home_stats)
                away_momentum = self._analyze_momentum(data.away_stats)

                if home_momentum:
                    features.update({f"home_{k}": v for k, v in home_momentum.items()})
                else:
                    warnings.append("home_momentum_data_insufficient")

                if away_momentum:
                    features.update({f"away_{k}": v for k, v in away_momentum.items()})
                else:
                    warnings.append("away_momentum_data_insufficient")

            # 2. 射门聚合
            if self.config.enable_shot_aggregation:
                agg_features = self._aggregate_shot_data(data)
                features.update(agg_features)

            # 3. V23.0: 高频动量分析（分段统计）
            if self.config.enable_highfreq_momentum:
                home_hf = self._analyze_highfreq_momentum(data.home_stats, "home")
                away_hf = self._analyze_highfreq_momentum(data.away_stats, "away")
                features.update(home_hf)
                features.update(away_hf)

            # 4. 战术压迫感评分
            pressure_features = self._compute_pressure_scores(features)
            features.update(pressure_features)

            # 5. 比赛节奏指标
            tempo_features = self._compute_tempo_metrics(features)
            features.update(tempo_features)

            # 6. V23.0: 高频动量交叉特征
            if self.config.enable_highfreq_momentum:
                hf_cross = self._compute_highfreq_cross_features(features)
                features.update(hf_cross)

            result = ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "momentum_enabled": self.config.enable_momentum_analysis,
                    "highfreq_enabled": self.config.enable_highfreq_momentum,
                },
            )

            for warning in warnings:
                result.with_warning(warning)

            return result

        except Exception as e:
            logger.exception(f"TacticalProcessor failed: {e}")
            return ProcessorResult.failure_result(str(e))

    def _analyze_momentum(self, stats: TeamStats | None) -> dict[str, float] | None:
        """分析球队动量（聚合维度）"""
        if stats is None or not stats.momentum_scores:
            return None

        momentum_scores = stats.momentum_scores

        if len(momentum_scores) < self.config.min_momentum_samples:
            return None

        features = {}
        features["momentum_mean"] = round(statistics.mean(momentum_scores), 4)
        features["momentum_std"] = round(
            statistics.stdev(momentum_scores) if len(momentum_scores) > 1 else 0.0, 4
        )
        features["momentum_max"] = round(max(momentum_scores), 4)
        features["momentum_min"] = round(min(momentum_scores), 4)
        features["momentum_velocity_mean"] = round(self._compute_velocity(momentum_scores), 4)
        features["momentum_acceleration_mean"] = round(
            self._compute_acceleration(momentum_scores), 4
        )
        features["momentum_volatility"] = round(self._compute_volatility(momentum_scores), 4)

        negative_momentum = [m for m in momentum_scores if m < 0]
        if negative_momentum:
            features["momentum_neg_velocity_mean"] = round(
                self._compute_velocity(negative_momentum), 4
            )
            features["momentum_neg_acceleration_mean"] = round(
                self._compute_acceleration(negative_momentum), 4
            )
        else:
            features["momentum_neg_velocity_mean"] = 0.0
            features["momentum_neg_acceleration_mean"] = 0.0

        return features

    def _analyze_highfreq_momentum(self, stats: TeamStats | None, prefix: str) -> dict[str, float]:
        """
        高频动量分析（V23.0 核心爆破）

        将 90 分钟分为 6 个时段，每个时段独立计算 10 个动量因子

        Args:
            stats: 球队统计数据
            prefix: 特征前缀

        Returns:
            高频动量特征字典（6 时段 × 10 维 = 60 维）
        """
        features = {}

        if stats is None or not stats.momentum_scores:
            # 无数据，填充默认值
            for seg in range(1, 7):
                for metric in [
                    "mean",
                    "std",
                    "max",
                    "min",
                    "velocity",
                    "acceleration",
                    "volatility",
                    "neg_velocity",
                    "trend",
                    "dominance",
                ]:
                    features[f"{prefix}_m{seg}_{metric}"] = 0.0
            return features

        momentum_scores = stats.momentum_scores

        # 假设 momentum_scores 是每分钟一个采样点（共 90 个）
        # 将其分为 6 个时段（每 15 分钟）
        segment_size = 15
        num_segments = 6

        for seg_idx in range(num_segments):
            start_idx = seg_idx * segment_size
            end_idx = min((seg_idx + 1) * segment_size, len(momentum_scores))

            segment_scores = momentum_scores[start_idx:end_idx]
            seg_num = seg_idx + 1  # m1, m2, ... m6

            if len(segment_scores) >= 3:  # 至少 3 个采样点
                # 1. 平均动量
                features[f"{prefix}_m{seg_num}_mean"] = round(statistics.mean(segment_scores), 4)

                # 2. 标准差
                if len(segment_scores) > 1:
                    features[f"{prefix}_m{seg_num}_std"] = round(
                        statistics.stdev(segment_scores), 4
                    )
                else:
                    features[f"{prefix}_m{seg_num}_std"] = 0.0

                # 3. 最大动量
                features[f"{prefix}_m{seg_num}_max"] = round(max(segment_scores), 4)

                # 4. 最小动量
                features[f"{prefix}_m{seg_num}_min"] = round(min(segment_scores), 4)

                # 5. 动量速度
                features[f"{prefix}_m{seg_num}_velocity"] = round(
                    self._compute_velocity(segment_scores), 4
                )

                # 6. 动量加速度
                features[f"{prefix}_m{seg_num}_acceleration"] = round(
                    self._compute_acceleration(segment_scores), 4
                )

                # 7. 波动率
                features[f"{prefix}_m{seg_num}_volatility"] = round(
                    self._compute_volatility(segment_scores), 4
                )

                # 8. 负向速度
                neg_scores = [s for s in segment_scores if s < 0]
                if neg_scores:
                    features[f"{prefix}_m{seg_num}_neg_velocity"] = round(
                        self._compute_velocity(neg_scores), 4
                    )
                else:
                    features[f"{prefix}_m{seg_num}_neg_velocity"] = 0.0

                # 9. 线性趋势（简单线性回归斜率）
                features[f"{prefix}_m{seg_num}_trend"] = round(
                    self._compute_linear_trend(segment_scores), 4
                )

                # 10. 支配度（正值占比）
                positive_count = sum(1 for s in segment_scores if s > 0)
                features[f"{prefix}_m{seg_num}_dominance"] = round(
                    positive_count / len(segment_scores), 4
                )

            else:
                # 数据不足，填充默认值
                for metric in [
                    "mean",
                    "std",
                    "max",
                    "min",
                    "velocity",
                    "acceleration",
                    "volatility",
                    "neg_velocity",
                    "trend",
                    "dominance",
                ]:
                    features[f"{prefix}_m{seg_num}_{metric}"] = 0.0

        return features

    def _compute_highfreq_cross_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算高频动量交叉特征（V23.0 扩展）

        包括:
            - 上半场 vs 下半场对比
            - 开局 vs 收尾对比
            - 动量稳定性评分
        """
        cross_features = {}

        for prefix in ["home", "away"]:
            # 上半场时段（m1-m3）vs 下半场时段（m4-m6）
            first_half = []
            second_half = []
            for seg in [1, 2, 3]:
                first_half.append(features.get(f"{prefix}_m{seg}_mean", 0))
            for seg in [4, 5, 6]:
                second_half.append(features.get(f"{prefix}_m{seg}_mean", 0))

            if first_half and second_half:
                fh_mean = statistics.mean(first_half)
                sh_mean = statistics.mean(second_half)
                cross_features[f"{prefix}_fh_sh_momentum_diff"] = round(fh_mean - sh_mean, 4)

                # 上半场/下半场动量比
                if sh_mean != 0:
                    cross_features[f"{prefix}_fh_sh_momentum_ratio"] = round(fh_mean / sh_mean, 4)
                else:
                    cross_features[f"{prefix}_fh_sh_momentum_ratio"] = 1.0

            # 开局（m1）vs 收尾（m6）
            m1_mean = features.get(f"{prefix}_m1_mean", 0)
            m6_mean = features.get(f"{prefix}_m6_mean", 0)
            cross_features[f"{prefix}_opening_closing_momentum_diff"] = round(m1_mean - m6_mean, 4)

            # 动量稳定性（各时段方差）
            all_segs = []
            for seg in range(1, 7):
                all_segs.append(features.get(f"{prefix}_m{seg}_mean", 0))
            if all_segs:
                mean_val = statistics.mean(all_segs)
                variance = sum((x - mean_val) ** 2 for x in all_segs) / len(all_segs)
                cross_features[f"{prefix}_momentum_stability"] = round(variance, 4)

            # 关键时刻爆发力（m2, m5 的最大值）
            m2_max = features.get(f"{prefix}_m2_max", 0)
            m5_max = features.get(f"{prefix}_m5_max", 0)
            cross_features[f"{prefix}_critical_peak_momentum"] = round(max(m2_max, m5_max), 4)

        # 主客队对比
        cross_features["diff_fh_sh_momentum"] = round(
            features.get("home_fh_sh_momentum_diff", 0)
            - features.get("away_fh_sh_momentum_diff", 0),
            4,
        )
        cross_features["diff_opening_momentum"] = round(
            features.get("home_m1_mean", 0) - features.get("away_m1_mean", 0), 4
        )
        cross_features["diff_closing_momentum"] = round(
            features.get("home_m6_mean", 0) - features.get("away_m6_mean", 0), 4
        )

        return cross_features

    def _compute_velocity(self, values: list[float]) -> float:
        """计算速度（一阶差分均值）"""
        if len(values) < 2:
            return 0.0
        diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
        return statistics.mean(diffs) if diffs else 0.0

    def _compute_acceleration(self, values: list[float]) -> float:
        """计算加速度（二阶差分均值）"""
        if len(values) < 3:
            return 0.0
        diffs = [values[i] - values[i - 1] for i in range(1, len(values))]
        accels = [diffs[i] - diffs[i - 1] for i in range(1, len(diffs))]
        return statistics.mean(accels) if accels else 0.0

    def _compute_volatility(self, values: list[float]) -> float:
        """计算波动率（标准差 / 均值）"""
        if len(values) < 2:
            return 0.0
        mean_val = statistics.mean(values)
        if mean_val == 0:
            return 0.0
        return statistics.stdev(values) / abs(mean_val)

    def _compute_linear_trend(self, values: list[float]) -> float:
        """计算线性趋势（简单线性回归斜率）"""
        if len(values) < 2:
            return 0.0
        n = len(values)
        x = list(range(n))
        y = values

        sum_x = sum(x)
        sum_y = sum(y)
        sum_xy = sum(xi * yi for xi, yi in zip(x, y, strict=False))
        sum_x2 = sum(xi * xi for xi in x)

        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0

        return (n * sum_xy - sum_x * sum_y) / denominator

    def _aggregate_shot_data(self, data: MatchData) -> dict[str, float]:
        """聚合射门数据"""
        features = {}

        if data.home_stats:
            features["home_synth_total_shots"] = float(data.home_stats.shots_total or 0)
            features["home_synth_xg"] = float(data.home_stats.expected_goals or 0.0)

        if data.away_stats:
            features["away_synth_total_shots"] = float(data.away_stats.shots_total or 0)
            features["away_synth_xg"] = float(data.away_stats.expected_goals or 0.0)

        if "home_synth_xg" in features and "away_synth_xg" in features:
            total_xg = features["home_synth_xg"] + features["away_synth_xg"]
            if total_xg > 0:
                features["home_xg_ratio"] = round(features["home_synth_xg"] / total_xg, 4)
            else:
                features["home_xg_ratio"] = 0.5

        return features

    def _compute_pressure_scores(self, features: dict[str, float]) -> dict[str, float]:
        """计算战术压迫感评分"""
        pressure_scores = {}

        for prefix in ["home", "away"]:
            shots = features.get(f"{prefix}_synth_total_shots", 0)
            possession = features.get(f"{prefix}_possession", 50)
            passes = features.get(f"{prefix}_total_passes", 0)

            shot_pressure = min(shots / 30.0, 1.0)
            possession_pressure = possession / 100.0
            pass_pressure = min(passes / 800.0, 1.0)

            pressure_scores[f"{prefix}_pressure_score"] = round(
                0.4 * shot_pressure + 0.3 * possession_pressure + 0.3 * pass_pressure, 4
            )

        pressure_scores["diff_pressure"] = round(
            pressure_scores["home_pressure_score"] - pressure_scores["away_pressure_score"], 4
        )

        return pressure_scores

    def _compute_tempo_metrics(self, features: dict[str, float]) -> dict[str, float]:
        """计算比赛节奏指标"""
        tempo_metrics = {}

        total_shots = features.get("home_synth_total_shots", 0) + features.get(
            "away_synth_total_shots", 0
        )
        total_passes = features.get("home_total_passes", 0) + features.get("away_total_passes", 0)

        tempo_metrics["tempo_total_shots"] = float(total_shots)
        tempo_metrics["tempo_total_passes"] = float(total_passes)

        shot_tempo = min(total_shots / 50.0, 1.0)
        pass_tempo = min(total_passes / 1500.0, 1.0)
        tempo_metrics["tempo_score"] = round(0.5 * shot_tempo + 0.5 * pass_tempo, 4)

        if tempo_metrics["tempo_score"] > 0.66:
            tempo_metrics["tempo_category"] = 2
        elif tempo_metrics["tempo_score"] > 0.33:
            tempo_metrics["tempo_category"] = 1
        else:
            tempo_metrics["tempo_category"] = 0

        return tempo_metrics

    def get_feature_schema(self) -> dict[str, type]:
        """
        获取输出特征的 Schema（V23.0 动态生成）

        使用 Python 循环动态生成 150+ 维特征的定义
        """
        schema = {
            # 聚合特征
            "home_momentum_mean": float,
            "away_momentum_mean": float,
            "home_momentum_velocity": float,
            "home_momentum_volatility": float,
            "home_synth_total_shots": float,
            "home_synth_xg": float,
            "home_xg_ratio": float,
            "home_pressure_score": float,
            "diff_pressure": float,
            "tempo_total_shots": float,
            "tempo_score": float,
            "tempo_category": int,
        }

        # V23.0: 动态生成高频动量特征 Schema（120 维）
        for prefix in ["home", "away"]:
            for seg in range(1, 7):  # m1 到 m6
                for metric in [
                    "mean",
                    "std",
                    "max",
                    "min",
                    "velocity",
                    "acceleration",
                    "volatility",
                    "neg_velocity",
                    "trend",
                    "dominance",
                ]:
                    schema[f"{prefix}_m{seg}_{metric}"] = float

        # 高频交叉特征
        for prefix in ["home", "away"]:
            schema[f"{prefix}_fh_sh_momentum_diff"] = float
            schema[f"{prefix}_fh_sh_momentum_ratio"] = float
            schema[f"{prefix}_opening_closing_momentum_diff"] = float
            schema[f"{prefix}_momentum_stability"] = float
            schema[f"{prefix}_critical_peak_momentum"] = float

        schema["diff_fh_sh_momentum"] = float
        schema["diff_opening_momentum"] = float
        schema["diff_closing_momentum"] = float

        return schema
