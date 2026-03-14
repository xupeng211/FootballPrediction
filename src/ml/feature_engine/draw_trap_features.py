#!/usr/bin/env python3
"""
TITAN 平局陷阱特征实验室
========================

🎯 目标: 提升平局 (Draw) 召回率从 26.8% 到 20%+

策略: 开发"拉锯战"特征集 (Tug-of-War Features)
- 特征 A: xG_Balance_Index - 进攻火力平衡度
- 特征 B: Double_Wall_Score - 双强防守指数
- 特征 C: Scoreless_Momentum - 低比分动量

@module src.ml.feature_engine.draw_trap_features
@version lab/draw-trap-v1
@created 2026-03-11
@branch lab/draw-trap-v1
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
class DrawFeatureResult:
    """
    平局特征计算结果

    Attributes:
        xg_balance_index: xG 平衡指数
        double_wall_score: 双强防守指数
        scoreless_momentum: 低比分动量
        combined_draw_probability: 综合平局概率
        metadata: 元数据
        warnings: 警告信息
    """

    xg_balance_index: float = 0.0
    double_wall_score: float = 0.0
    scoreless_momentum: float = 0.0
    combined_draw_probability: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "xg_balance_index": self.xg_balance_index,
            "double_wall_score": self.double_wall_score,
            "scoreless_momentum": self.scoreless_momentum,
            "combined_draw_probability": self.combined_draw_probability,
            "metadata": self.metadata,
            "warnings": self.warnings,
        }


# ============================================================================
# 平局特征计算器
# ============================================================================


class DrawTrapFeatures:
    """
    平局陷阱特征计算器

    ⚠️ 实验室模块 - 仅用于 lab/draw-trap-v1 分支

    核心理念:
        平局往往发生在"势均力敌"的比赛中：
        1. 两队进攻火力接近 → 难以打破僵局
        2. 两队防守都很强 → 互交白卷
        3. 近期频繁低比分 → 状态延续

    Example:
        >>> calc = DrawTrapFeatures()
        >>> result = calc.calculate(
        ...     home_xg_l5=[1.2, 0.8, 1.5, 1.0, 1.3],
        ...     away_xg_l5=[1.1, 1.0, 1.2, 0.9, 1.1],
        ...     home_def_rating=7.2,
        ...     away_def_rating=6.8,
        ...     home_recent_scores=[[1,1], [0,0], [2,1]],
        ...     away_recent_scores=[[0,0], [1,1], [1,2]],
        ... )
    """

    # 特征权重配置
    FEATURE_WEIGHTS = {
        "xg_balance": 0.35,      # xG 平衡度权重
        "double_wall": 0.35,     # 双强防守权重
        "scoreless": 0.30,       # 低比分动量权重
    }

    def __init__(self) -> None:
        """初始化平局特征计算器"""
        logger.info("🎯 平局陷阱特征计算器初始化 | 分支: lab/draw-trap-v1")

    # ========================================================================
    # 特征 A: xG 平衡指数 (xG_Balance_Index)
    # ========================================================================

    def calculate_xg_balance_index(
        self,
        home_xg_l5: List[float],
        away_xg_l5: List[float],
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算 xG 平衡指数

        ═══════════════════════════════════════════════════════════════════════
        算法原理:
        ═══════════════════════════════════════════════════════════════════════

        当两队进攻火力接近时，比赛更容易陷入僵局。

        公式:
            xg_diff = |mean(home_xg) - mean(away_xg)|
            balance_index = 1 / (xg_diff + 0.1)

        其中:
            - 0.1 是平滑因子，防止除零
            - xg_diff 越小，balance_index 越高
            - balance_index 范围: (0, 10]

        ═══════════════════════════════════════════════════════════════════════

        Args:
            home_xg_l5: 主队近 5 场 xG 值列表
            away_xg_l5: 客队近 5 场 xG 值列表

        Returns:
            (balance_index, metadata)
        """
        # 计算平均 xG
        home_xg_mean = np.mean(home_xg_l5) if home_xg_l5 else 1.0
        away_xg_mean = np.mean(away_xg_l5) if away_xg_l5 else 1.0

        # 计算差异
        xg_diff = abs(home_xg_mean - away_xg_mean)

        # 计算平衡指数 (使用平滑因子 0.1)
        balance_index = 1.0 / (xg_diff + 0.1)

        # 归一化到 [0, 1] 范围
        # 当 xg_diff = 0 时，balance_index = 10，归一化后为 1.0
        # 当 xg_diff = 0.9 时，balance_index = 1，归一化后为 0.1
        normalized_index = min(1.0, balance_index / 10.0)

        metadata = {
            "home_xg_mean": float(home_xg_mean),
            "away_xg_mean": float(away_xg_mean),
            "xg_diff": float(xg_diff),
            "raw_balance_index": float(balance_index),
        }

        return float(normalized_index), metadata

    # ========================================================================
    # 特征 B: 双强防守指数 (Double_Wall_Score)
    # ========================================================================

    def calculate_double_wall_score(
        self,
        home_def_rating: float,
        away_def_rating: float,
        max_rating: float = 10.0,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算双强防守指数

        ═══════════════════════════════════════════════════════════════════════
        算法原理:
        ═══════════════════════════════════════════════════════════════════════

        当两队防守都很强时，比赛更容易以低比分结束。

        公式:
            double_wall = (home_def + away_def) / 2 / max_rating

        其中:
            - 防守评级范围通常是 [0, 10]
            - 双强防守指数范围: [0, 1]

        例子:
            - 两队防守都是 8/10 → double_wall = 0.80 (高平局概率)
            - 两队防守都是 4/10 → double_wall = 0.40 (低平局概率)

        ═══════════════════════════════════════════════════════════════════════

        Args:
            home_def_rating: 主队防守评级 (0-10)
            away_def_rating: 客队防守评级 (0-10)
            max_rating: 最大评级值 (默认 10)

        Returns:
            (double_wall_score, metadata)
        """
        # 计算平均防守强度
        avg_defense = (home_def_rating + away_def_rating) / 2.0

        # 归一化
        double_wall = avg_defense / max_rating

        # 应用非线性变换增强高分区域
        # 使用 sigmoid-like 变换：高防守评分被进一步放大
        enhanced_wall = double_wall ** 1.2  # 指数 > 1 增强高值

        metadata = {
            "home_def_rating": float(home_def_rating),
            "away_def_rating": float(away_def_rating),
            "avg_defense": float(avg_defense),
            "raw_score": float(double_wall),
            "enhanced_score": float(enhanced_wall),
        }

        return float(min(1.0, enhanced_wall)), metadata

    # ========================================================================
    # 特征 C: 低比分动量 (Scoreless_Momentum)
    # ========================================================================

    def calculate_scoreless_momentum(
        self,
        home_recent_scores: List[List[int]],
        away_recent_scores: List[List[int]],
        low_score_threshold: int = 2,
    ) -> Tuple[float, Dict[str, Any]]:
        """
        计算低比分动量

        ═══════════════════════════════════════════════════════════════════════
        算法原理:
        ═══════════════════════════════════════════════════════════════════════

        统计两队近 3 场比赛中出现低比分 (总进球 <= 2) 的频率。

        低比分定义:
            - 0-0 (互交白卷)
            - 1-0 / 0-1 (小胜)
            - 1-1 (低比分平局)

        公式:
            low_score_count = count(total_goals <= 2)
            momentum = low_score_count / total_matches

        范围: [0, 1]

        ═══════════════════════════════════════════════════════════════════════

        Args:
            home_recent_scores: 主队近 3 场比分 [[home, away], ...]
            away_recent_scores: 客队近 3 场比分 [[home, away], ...]
            low_score_threshold: 低比分阈值 (默认 2 球)

        Returns:
            (scoreless_momentum, metadata)
        """
        all_scores = home_recent_scores + away_recent_scores

        if not all_scores:
            return 0.5, {"status": "no_data", "default": 0.5}

        low_score_count = 0
        for score in all_scores:
            if len(score) >= 2:
                total_goals = score[0] + score[1]
                if total_goals <= low_score_threshold:
                    low_score_count += 1

        momentum = low_score_count / len(all_scores)

        metadata = {
            "total_matches": len(all_scores),
            "low_score_count": low_score_count,
            "low_score_threshold": low_score_threshold,
            "home_matches": len(home_recent_scores),
            "away_matches": len(away_recent_scores),
        }

        return float(momentum), metadata

    # ========================================================================
    # 综合计算
    # ========================================================================

    def calculate(
        self,
        home_xg_l5: List[float],
        away_xg_l5: List[float],
        home_def_rating: float,
        away_def_rating: float,
        home_recent_scores: List[List[int]],
        away_recent_scores: List[List[int]],
    ) -> DrawFeatureResult:
        """
        综合计算所有平局特征

        Args:
            home_xg_l5: 主队近 5 场 xG
            away_xg_l5: 客队近 5 场 xG
            home_def_rating: 主队防守评级
            away_def_rating: 客队防守评级
            home_recent_scores: 主队近 3 场比分
            away_recent_scores: 客队近 3 场比分

        Returns:
            DrawFeatureResult: 所有特征计算结果
        """
        # 计算各个特征
        xg_balance, xg_meta = self.calculate_xg_balance_index(home_xg_l5, away_xg_l5)
        double_wall, wall_meta = self.calculate_double_wall_score(
            home_def_rating, away_def_rating
        )
        scoreless, score_meta = self.calculate_scoreless_momentum(
            home_recent_scores, away_recent_scores
        )

        # 计算综合平局概率 (加权平均)
        combined_prob = (
            xg_balance * self.FEATURE_WEIGHTS["xg_balance"]
            + double_wall * self.FEATURE_WEIGHTS["double_wall"]
            + scoreless * self.FEATURE_WEIGHTS["scoreless"]
        )

        metadata = {
            "xg_balance": xg_meta,
            "double_wall": wall_meta,
            "scoreless": score_meta,
            "weights": self.FEATURE_WEIGHTS,
        }

        warnings = []
        if combined_prob > 0.7:
            warnings.append(f"高平局概率: {combined_prob:.2%}")
        if xg_balance > 0.8:
            warnings.append("两队进攻火力非常接近")
        if double_wall > 0.8:
            warnings.append("双强防守格局")

        return DrawFeatureResult(
            xg_balance_index=xg_balance,
            double_wall_score=double_wall,
            scoreless_momentum=scoreless,
            combined_draw_probability=float(combined_prob),
            metadata=metadata,
            warnings=warnings,
        )


# ============================================================================
# 模块级导出
# ============================================================================

__all__ = [
    "DrawTrapFeatures",
    "DrawFeatureResult",
]


# ============================================================================
# 单元测试
# ============================================================================


