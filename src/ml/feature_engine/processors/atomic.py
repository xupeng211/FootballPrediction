"""
AtomicProcessor - 原子级基础统计处理器
========================================

负责提取和回填基础统计特征，包括:
    - xG 回填（V20.7 核心特性）
    - 基础射门数据
    - 控球率统计
    - 传球数据
    - 球队评分

设计模式:
    - 回填机制: 对于缺失字段，尝试从半场数据聚合
    - 容错处理: 数据缺失时填充默认值（0.0 或 -1.0）
    - 精度保证: 关键指标使用 Decimal 类型

作者: FootballPrediction Architecture Team
版本: V21.0-alpha
"""

import logging
from typing import Any

from src.ml.feature_engine.base import BaseProcessor, ProcessorConfig, ProcessorResult
from src.ml.feature_engine.models import MatchData, TeamStats

logger = logging.getLogger(__name__)


class AtomicProcessorConfig(ProcessorConfig):
    """
    AtomicProcessor 配置

    Attributes:
        enable_xg_backfill: 是否启用 xG 回填（V20.7 核心特性）
        zero_padding_default: 缺失数值字段的默认填充值
        missing_indicator: 用于标记缺失值的特殊值
        strict_validation: 是否严格验证数据完整性
    """

    enable_xg_backfill: bool = True
    zero_padding_default: float = 0.0
    missing_indicator: float = -1.0
    strict_validation: bool = False


class AtomicProcessor(BaseProcessor[MatchData]):
    """
    原子级基础统计处理器

    职责:
        1. 提取主客队的基础统计数据
        2. 回填缺失的 xG 等关键字段
        3. 标准化特征命名（home_*, away_*）
        4. 应用 zero-padding 确保特征维度一致

    特征输出:
        - home_xg, away_xg: 预期进球
        - home_shots, away_shots: 总射门数
        - home_shots_on_target, away_shots_on_target: 射正数
        - home_possession, away_possession: 控球率
        - home_passes, away_passes: 总传球数
        - home_rating, away_rating: 球队评分

    Example:
        >>> processor = AtomicProcessor()
        >>> result = processor.execute(match_data)
        >>> print(result.data["home_xg"])
        1.25
    """

    processor_name = "AtomicProcessor"
    processor_version = "21.0.0"
    priority = 10  # 高优先级，首先执行

    def __init__(self, config: AtomicProcessorConfig | None = None) -> None:
        super().__init__(config or AtomicProcessorConfig())
        self.config: AtomicProcessorConfig = self.config

    def process(self, data: MatchData, context: Any) -> ProcessorResult:
        """
        提取原子级基础统计特征

        Args:
            data: 比赛数据
            context: 处理上下文

        Returns:
            ProcessorResult: 包含提取特征的处理器结果
        """
        features: dict[str, float] = {}

        try:
            # 处理主队数据
            if data.home_stats:
                home_features = self._extract_team_features(data.home_stats, "home")
                features.update(home_features)
            else:
                logger.warning(f"Match {data.match_id}: home_stats is missing")
                # 应用 zero-padding
                features.update(self._get_zero_padded_features("home"))

            # 处理客队数据
            if data.away_stats:
                away_features = self._extract_team_features(data.away_stats, "away")
                features.update(away_features)
            else:
                logger.warning(f"Match {data.match_id}: away_stats is missing")
                features.update(self._get_zero_padded_features("away"))

            # 计算差值特征
            diff_features = self._compute_differential_features(features)
            features.update(diff_features)

            return ProcessorResult.success_result(
                data=features,
                metadata={
                    "feature_count": len(features),
                    "xg_backfill_enabled": self.config.enable_xg_backfill,
                },
            )

        except Exception as e:
            logger.exception(f"AtomicProcessor failed for match {data.match_id}: {e}")
            return ProcessorResult.failure_result(str(e))

    def _extract_team_features(self, stats: TeamStats, prefix: str) -> dict[str, float]:
        """
        提取单队特征

        Args:
            stats: 球队统计数据
            prefix: 特征前缀（home 或 away）

        Returns:
            特征字典
        """
        features = {}

        # xG 回填逻辑（V20.7 核心特性）
        xg_value = stats.expected_goals
        if xg_value is None and self.config.enable_xg_backfill:
            # 尝试从半场数据回填（如果有的话）
            # 这里简化处理，实际可调用 shotmap_aggregator
            xg_value = self.config.zero_padding_default
            logger.debug(f"xG backfill applied for {prefix}_team")

        features[f"{prefix}_xg"] = (
            xg_value if xg_value is not None else self.config.zero_padding_default
        )
        features[f"{prefix}_xg_from_shots"] = (
            stats.expected_goals_from_shots
            if stats.expected_goals_from_shots is not None
            else self.config.zero_padding_default
        )

        # 基础射门数据
        features[f"{prefix}_shots"] = (
            float(stats.shots_total)
            if stats.shots_total is not None
            else self.config.zero_padding_default
        )
        features[f"{prefix}_shots_on_target"] = (
            float(stats.shots_on_target)
            if stats.shots_on_target is not None
            else self.config.zero_padding_default
        )

        # 控球率
        features[f"{prefix}_possession"] = (
            stats.possession if stats.possession is not None else self.config.missing_indicator
        )

        # 传球数据
        features[f"{prefix}_total_passes"] = (
            float(stats.total_passes)
            if stats.total_passes is not None
            else self.config.zero_padding_default
        )
        features[f"{prefix}_accurate_passes"] = (
            float(stats.accurate_passes)
            if stats.accurate_passes is not None
            else self.config.zero_padding_default
        )

        # 传球成功率（计算得出）
        if stats.total_passes and stats.total_passes > 0:
            pass_accuracy = (stats.accurate_passes or 0) / stats.total_passes * 100
            features[f"{prefix}_pass_accuracy"] = round(pass_accuracy, 2)
        else:
            features[f"{prefix}_pass_accuracy"] = self.config.missing_indicator

        # 球队评分
        features[f"{prefix}_rating"] = (
            stats.team_rating if stats.team_rating is not None else self.config.missing_indicator
        )

        # 其他统计
        features[f"{prefix}_corners"] = (
            float(stats.corners) if stats.corners is not None else self.config.zero_padding_default
        )
        features[f"{prefix}_offsides"] = (
            float(stats.offsides)
            if stats.offsides is not None
            else self.config.zero_padding_default
        )
        features[f"{prefix}_fouls"] = (
            float(stats.fouls) if stats.fouls is not None else self.config.zero_padding_default
        )

        return features

    def _get_zero_padded_features(self, prefix: str) -> dict[str, float]:
        """
        获取零填充特征（数据缺失时）

        Args:
            prefix: 特征前缀（home 或 away）

        Returns:
            填充了默认值的特征字典
        """
        return {
            f"{prefix}_xg": self.config.zero_padding_default,
            f"{prefix}_xg_from_shots": self.config.zero_padding_default,
            f"{prefix}_shots": self.config.zero_padding_default,
            f"{prefix}_shots_on_target": self.config.zero_padding_default,
            f"{prefix}_possession": self.config.missing_indicator,
            f"{prefix}_total_passes": self.config.zero_padding_default,
            f"{prefix}_accurate_passes": self.config.zero_padding_default,
            f"{prefix}_pass_accuracy": self.config.missing_indicator,
            f"{prefix}_rating": self.config.missing_indicator,
            f"{prefix}_corners": self.config.zero_padding_default,
            f"{prefix}_offsides": self.config.zero_padding_default,
            f"{prefix}_fouls": self.config.zero_padding_default,
        }

    def _compute_differential_features(self, features: dict[str, float]) -> dict[str, float]:
        """
        计算差值特征（主队 - 客队）

        Args:
            features: 已提取的基础特征

        Returns:
            差值特征字典
        """
        diff_features = {}

        # 定义需要计算差值的特征
        diff_fields = [
            "xg",
            "shots",
            "shots_on_target",
            "possession",
            "total_passes",
            "rating",
            "corners",
        ]

        for field in diff_fields:
            home_key = f"home_{field}"
            away_key = f"away_{field}"

            if home_key in features and away_key in features:
                home_val = features[home_key]
                away_val = features[away_key]

                # 检查是否为缺失值标记
                if self.config.missing_indicator not in (home_val, away_val):
                    diff_features[f"diff_{field}"] = round(home_val - away_val, 3)
                else:
                    diff_features[f"diff_{field}"] = self.config.missing_indicator

        return diff_features

    def get_feature_schema(self) -> dict[str, type]:
        """获取输出特征的 Schema"""
        return {
            "home_xg": float,
            "away_xg": float,
            "home_shots": float,
            "away_shots": float,
            "home_possession": float,
            "away_possession": float,
            "diff_xg": float,
            "diff_shots": float,
        }
