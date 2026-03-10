#!/usr/bin/env python3
"""
H2H 智能补位引擎
================

V4.46.8 重构：从 predict_pipeline.py 剥离的 H2H 估算逻辑。

当真实 H2H 数据缺失时，基于 Elo 差值进行线性推演：
- h2h_avg_goal_diff = elo_diff / 100 * 0.5
- h2h_home_win_ratio = 基于 expected_home_win 的平滑值
- h2h_draw_ratio = 联赛平局基准

@module src.ml.feature_engine.h2h_estimator
@version V4.46.8
@updated 2026-03-11
"""

import logging
from typing import Dict

from src.constants.model_config import (
    get_league_home_win_baseline,
    get_league_draw_baseline,
)

logger = logging.getLogger(__name__)


class H2HEstimator:
    """
    H2H 智能补位引擎

    当真实 H2H 数据缺失时，基于 Elo 差值进行线性推演:
    - h2h_avg_goal_diff = elo_diff * ELO_TO_GOAL_COEFF
    - h2h_home_win_ratio = 基于 expected_home_win 的平滑值
    - h2h_draw_ratio = 联赛平局基准

    使用示例:
        >>> h2h_data = {}
        >>> if H2HEstimator.needs_estimation(h2h_data):
        ...     estimated = H2HEstimator.estimate_from_elo(
        ...         elo_diff=50.0,
        ...         expected_home_win=0.55,
        ...         league_name="Premier League"
        ...     )
    """

    # Elo 差值到净胜球的转换系数 (每 100 分 Elo 差 ≈ 0.5 球)
    ELO_TO_GOAL_COEFF = 0.005

    # 主场胜率平滑参数
    HOME_WIN_SMOOTH_FACTOR = 0.85

    @classmethod
    def estimate_from_elo(
        cls,
        elo_diff: float,
        expected_home_win: float,
        league_name: str = None,
    ) -> Dict[str, float]:
        """
        基于 Elo 数据估算 H2H 特征

        Args:
            elo_diff: 主队 Elo - 客队 Elo
            expected_home_win: Elo 期望主胜率
            league_name: 联赛名称 (用于获取基准值)

        Returns:
            估算的 H2H 特征字典，包含:
            - h2h_avg_goal_diff: 历史平均净胜球
            - h2h_home_win_ratio: 主胜率
            - h2h_draw_ratio: 平局率
            - estimated: True (标记为估算值)
        """
        # 1. 估算历史净胜球差 (线性映射)
        # Elo 差 +200 → 预期 +1 球优势
        h2h_avg_goal_diff = elo_diff * cls.ELO_TO_GOAL_COEFF

        # 2. 估算主胜率 (基于 Elo 期望值平滑)
        # 使用加权平均: 85% Elo期望 + 15% 联赛基准
        league_baseline = get_league_home_win_baseline(league_name)
        h2h_home_win_ratio = (
            expected_home_win * cls.HOME_WIN_SMOOTH_FACTOR
            + league_baseline * (1 - cls.HOME_WIN_SMOOTH_FACTOR)
        )

        # 3. 估算平局率 (使用联赛基准)
        h2h_draw_ratio = get_league_draw_baseline(league_name)

        return {
            "h2h_avg_goal_diff": round(h2h_avg_goal_diff, 3),
            "h2h_home_win_ratio": round(h2h_home_win_ratio, 3),
            "h2h_draw_ratio": round(h2h_draw_ratio, 3),
            "estimated": True,
        }

    @classmethod
    def needs_estimation(cls, h2h_data: Dict) -> bool:
        """
        判断 H2H 数据是否需要补位

        触发条件:
        1. h2h_data 为空
        2. h2h_avg_goal_diff 为 0 或缺失
        3. h2h_home_win_ratio 为 0 或缺失

        Args:
            h2h_data: H2H 数据字典

        Returns:
            是否需要估算补位
        """
        if not h2h_data:
            return True

        avg_gd = h2h_data.get("h2h_avg_goal_diff", h2h_data.get("avg_goal_diff", 0))
        win_ratio = h2h_data.get("h2h_home_win_ratio", h2h_data.get("home_win_ratio", 0))

        # 如果两个关键特征都为 0，认为数据缺失
        return (avg_gd == 0 and win_ratio == 0) or (avg_gd is None and win_ratio is None)


__all__ = ["H2HEstimator"]
