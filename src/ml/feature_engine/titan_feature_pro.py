#!/usr/bin/env python3
"""
TITAN FeaturePro - 生产级特征工程模块
=====================================

整合所有实验验证通过的特征:
- Momentum Features (动量特征)
- Draw Trap Features (平局陷阱特征)

设计原则:
- 单一入口点: TitanFeaturePro.calculate_all_features()
- 完整的日志记录
- 标准化的错误处理
- 幂等性保证

@module src.ml.feature_engine.titan_feature_pro
@version V4.47.0
@created 2026-03-11
"""

from dataclasses import dataclass, field
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# 数据结构定义
# ============================================================================


@dataclass
class FeatureResult:
    """
    特征计算结果

    Attributes:
        features: 特征字典 {feature_name: value}
        success: 计算是否成功
        errors: 错误信息列表
        warnings: 警告信息列表
        metadata: 元数据
    """

    features: Dict[str, float] = field(default_factory=dict)
    success: bool = True
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# 核心特征计算器
# ============================================================================


class TitanFeaturePro:
    """
    TITAN 生产级特征计算器

    整合所有经过验证的特征:
    - 基础特征 (11 维): Elo + 身价 + H2H
    - 动量特征 (2 维): momentum_home, momentum_away
    - 平局陷阱特征 (3 维): xg_balance, double_wall, scoreless_momentum

    总计: 16 维特征向量

    Example:
        >>> pro = TitanFeaturePro()
        >>> result = pro.calculate_all_features(
        ...     home_recent_matches=[...],
        ...     away_recent_matches=[...],
        ...     home_xg_l5=[...],
        ...     away_xg_l5=[...],
        ...     home_def_rating=7.5,
        ...     away_def_rating=6.8,
        ... )
    """

    VERSION = "V4.47.0"

    # 结果到实际得分的映射
    RESULT_TO_SCORE = {"W": 1.0, "D": 0.5, "L": 0.0}

    # 默认动量参数
    DEFAULT_DECAY_ALPHA = 0.8
    DEFAULT_WINDOW_SIZE = 5
    DEFAULT_TANH_K = 3.0

    def __init__(self) -> None:
        """初始化特征计算器"""
        logger.info(f"TITAN FeaturePro 初始化 | 版本: {self.VERSION}")

    # ========================================================================
    # 动量特征计算 (Momentum Features)
    # ========================================================================

    def calculate_momentum(
        self,
        recent_matches: List[Dict[str, Any]],
        decay_alpha: float = DEFAULT_DECAY_ALPHA,
        tanh_k: float = DEFAULT_TANH_K,
    ) -> float:
        """
        计算动量评分

        基于表现残差 (实际得分 - 期望得分) 的加权平均

        Args:
            recent_matches: 近期比赛列表，每个元素包含:
                - result: "W" | "D" | "L"
                - expected_score: Elo 期望得分 (0-1)
            decay_alpha: 衰减系数 (默认 0.8)
            tanh_k: Tanh 放大系数 (默认 3.0)

        Returns:
            归一化动量评分 (-1, 1)
        """
        if not recent_matches:
            return 0.0

        n_matches = len(recent_matches)
        actual_scores = []
        expected_scores = []

        for match in recent_matches:
            result_code = match.get("result", "D").upper()
            actual = self.RESULT_TO_SCORE.get(result_code, 0.5)
            expected = float(match.get("expected_score", 0.45))

            actual_scores.append(actual)
            expected_scores.append(expected)

        # NumPy 向量化计算
        actual_arr = np.array(actual_scores, dtype=np.float64)
        expected_arr = np.array(expected_scores, dtype=np.float64)

        # 计算残差
        residuals = actual_arr - expected_arr

        # 计算权重向量 (指数衰减)
        indices = np.arange(len(residuals))
        weights = np.power(decay_alpha, indices)

        # 加权平均残差
        weighted_sum = np.sum(weights * residuals)
        weight_total = np.sum(weights)
        raw_momentum = weighted_sum / weight_total if weight_total > 0 else 0.0

        # Tanh 归一化
        normalized = np.tanh(tanh_k * raw_momentum)

        return float(normalized)

    # ========================================================================
    # 平局陷阱特征计算 (Draw Trap Features)
    # ========================================================================

    def calculate_xg_balance(
        self,
        home_xg_l5: List[float],
        away_xg_l5: List[float],
    ) -> float:
        """
        计算 xG 平衡指数

        两队进攻火力越接近，平局概率越高

        Args:
            home_xg_l5: 主队近 5 场 xG 列表
            away_xg_l5: 客队近 5 场 xG 列表

        Returns:
            xG 平衡指数 (0-1)
        """
        try:
            home_mean = np.mean(home_xg_l5) if home_xg_l5 else 1.0
            away_mean = np.mean(away_xg_l5) if away_xg_l5 else 1.0

            xg_diff = abs(home_mean - away_mean)
            balance = 1.0 / (xg_diff + 0.1)

            # 归一化到 [0, 1]
            return float(min(1.0, balance / 10.0))

        except Exception as e:
            logger.warning(f"xG 平衡计算失败: {e}")
            return 0.5

    def calculate_double_wall(
        self,
        home_def_rating: float,
        away_def_rating: float,
        max_rating: float = 10.0,
    ) -> float:
        """
        计算双强防守指数

        双强防守是平局的温床

        Args:
            home_def_rating: 主队防守评级 (0-10)
            away_def_rating: 客队防守评级 (0-10)
            max_rating: 最大评级值

        Returns:
            双强防守指数 (0-1)
        """
        try:
            avg_defense = (home_def_rating + away_def_rating) / 2.0
            normalized = avg_defense / max_rating
            enhanced = normalized ** 1.2

            return float(min(1.0, enhanced))

        except Exception as e:
            logger.warning(f"双强防守计算失败: {e}")
            return 0.5

    def calculate_scoreless_momentum(
        self,
        home_recent_scores: List[List[int]],
        away_recent_scores: List[List[int]],
        low_score_threshold: int = 2,
    ) -> float:
        """
        计算低比分动量

        统计近期低比分比赛的频率

        Args:
            home_recent_scores: 主队近期比分 [[home, away], ...]
            away_recent_scores: 客队近期比分 [[home, away], ...]
            low_score_threshold: 低比分阈值 (默认 2)

        Returns:
            低比分动量 (0-1)
        """
        all_scores = home_recent_scores + away_recent_scores

        if not all_scores:
            return 0.5

        low_score_count = 0
        for score in all_scores:
            if len(score) >= 2:
                total_goals = score[0] + score[1]
                if total_goals <= low_score_threshold:
                    low_score_count += 1

        momentum = low_score_count / len(all_scores)
        return float(momentum)

    # ========================================================================
    # 综合特征计算
    # ========================================================================

    def calculate_all_features(
        self,
        home_recent_matches: List[Dict[str, Any]],
        away_recent_matches: List[Dict[str, Any]],
        home_xg_l5: Optional[List[float]] = None,
        away_xg_l5: Optional[List[float]] = None,
        home_def_rating: float = 6.0,
        away_def_rating: float = 6.0,
        home_recent_scores: Optional[List[List[int]]] = None,
        away_recent_scores: Optional[List[List[int]]] = None,
    ) -> FeatureResult:
        """
        计算所有特征

        Args:
            home_recent_matches: 主队近期比赛数据
            away_recent_matches: 客队近期比赛数据
            home_xg_l5: 主队近 5 场 xG
            away_xg_l5: 客队近 5 场 xG
            home_def_rating: 主队防守评级
            away_def_rating: 客队防守评级
            home_recent_scores: 主队近期比分
            away_recent_scores: 客队近期比分

        Returns:
            FeatureResult: 包含所有特征的结果
        """
        features = {}
        warnings = []

        try:
            # 1. 动量特征
            home_momentum = self.calculate_momentum(home_recent_matches)
            away_momentum = self.calculate_momentum(away_recent_matches)
            features["momentum_home"] = home_momentum
            features["momentum_away"] = away_momentum

            if abs(home_momentum) > 0.8:
                warnings.append(f"主队极端动量: {home_momentum:.2f}")
            if abs(away_momentum) > 0.8:
                warnings.append(f"客队极端动量: {away_momentum:.2f}")

            # 2. 平局陷阱特征
            if home_xg_l5 and away_xg_l5:
                xg_balance = self.calculate_xg_balance(home_xg_l5, away_xg_l5)
                features["xg_balance_index"] = xg_balance
            else:
                features["xg_balance_index"] = 0.5
                warnings.append("xG 数据缺失，使用默认值")

            double_wall = self.calculate_double_wall(home_def_rating, away_def_rating)
            features["double_wall_score"] = double_wall

            if home_recent_scores and away_recent_scores:
                scoreless = self.calculate_scoreless_momentum(
                    home_recent_scores, away_recent_scores
                )
                features["scoreless_momentum"] = scoreless
            else:
                features["scoreless_momentum"] = 0.5
                warnings.append("比分数据缺失，使用默认值")

            # 3. 综合平局概率
            draw_prob = (
                features["xg_balance_index"] * 0.35
                + features["double_wall_score"] * 0.35
                + features["scoreless_momentum"] * 0.30
            )
            features["combined_draw_probability"] = draw_prob

            if draw_prob > 0.7:
                warnings.append(f"高平局概率: {draw_prob:.2%}")

            logger.debug(
                f"特征计算完成 | momentum=({home_momentum:.2f}, {away_momentum:.2f}) | "
                f"draw_prob={draw_prob:.2%}"
            )

            return FeatureResult(
                features=features,
                success=True,
                warnings=warnings,
                metadata={
                    "version": self.VERSION,
                    "feature_count": len(features),
                },
            )

        except Exception as e:
            logger.error(f"特征计算失败: {e}", exc_info=True)
            return FeatureResult(
                features={},
                success=False,
                errors=[str(e)],
                metadata={"version": self.VERSION},
            )

    def get_feature_names(self) -> List[str]:
        """获取所有特征名称"""
        return [
            "momentum_home",
            "momentum_away",
            "xg_balance_index",
            "double_wall_score",
            "scoreless_momentum",
            "combined_draw_probability",
        ]


# ============================================================================
# 模块级导出
# ============================================================================

__all__ = [
    "TitanFeaturePro",
    "FeatureResult",
]
