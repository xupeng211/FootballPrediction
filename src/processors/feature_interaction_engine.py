"""
V41.430 Feature Interaction Engine - 特征交叉工程
================================================

非线性特征交叉：
- discipline_adjusted_value = (1 / 红牌数) * 总身价
- value_per_injury = 身价 / 伤病数
- momentum_xg = 评分加速度 * xG 均值

Author: V41.430 ML Team
Version: V41.430 "Non-linear Breakthrough"
Date: 2026-01-21
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)


class FeatureInteractionEngine:
    """
    V41.430 特征交叉引擎

    创建高阶交互特征，捕捉非线性关系
    """

    def __init__(self, epsilon: float = 1e-6):
        """
        初始化交叉引擎

        Args:
            epsilon: 防止除零的小常数
        """
        self.epsilon = epsilon
        logger.info("V41.430: Feature Interaction Engine initialized")

    def create_discipline_adjusted_value(
        self,
        features: dict[str, Any]
    ) -> dict[str, float]:
        """
        创建纪律调整身价特征

        discipline_adjusted_value = (1 / 红牌数) * 总身价

        逻辑：身价高但红牌多的球队，实际战斗力会被打折
        """
        result = {}

        # 主队纪律调整身价
        home_mv = features.get("home_market_value_total", 0)
        home_red = features.get("home_red_cards", self.epsilon)  # 防止除零

        if home_mv > 0:
            result["home_discipline_adjusted_value"] = home_mv / max(home_red, self.epsilon)
            result["home_discipline_ratio"] = max(home_red, self.epsilon) / max(home_mv / 1_000_000, self.epsilon)  # 归一化

        # 客队纪律调整身价
        away_mv = features.get("away_market_value_total", 0)
        away_red = features.get("away_red_cards", self.epsilon)

        if away_mv > 0:
            result["away_discipline_adjusted_value"] = away_mv / max(away_red, self.epsilon)
            result["away_discipline_ratio"] = max(away_red, self.epsilon) / max(away_mv / 1_000_000, self.epsilon)

        # 纪律调整身价差值
        if "home_discipline_adjusted_value" in result and "away_discipline_adjusted_value" in result:
            result["diff_discipline_adjusted_value"] = (
                result["home_discipline_adjusted_value"] - result["away_discipline_adjusted_value"]
            )
            result["ratio_discipline_adjusted_value"] = (
                result["home_discipline_adjusted_value"] / max(result["away_discipline_adjusted_value"], self.epsilon)
            )

        return result

    def create_value_per_injury(
        self,
        features: dict[str, Any]
    ) -> dict[str, float]:
        """
        创建单位伤病身价损失特征

        value_per_injury = 总身价 / (伤病数 + 1)

        逻辑：核心球员伤缺对高身价球队影响更大
        """
        result = {}

        # 主队
        home_mv = features.get("home_market_value_total", 0)
        home_injury = features.get("home_injury_count", 0)

        if home_mv > 0:
            result["home_value_per_injury"] = home_mv / max(home_injury + 1, 1)
            result["home_injury_impact_ratio"] = max(home_injury, 0) / max(home_mv / 10_000_000, 1)

        # 客队
        away_mv = features.get("away_market_value_total", 0)
        away_injury = features.get("away_injury_count", 0)

        if away_mv > 0:
            result["away_value_per_injury"] = away_mv / max(away_injury + 1, 1)
            result["away_injury_impact_ratio"] = max(away_injury, 0) / max(away_mv / 10_000_000, 1)

        # 差值
        if "home_value_per_injury" in result and "away_value_per_injury" in result:
            result["diff_value_per_injury"] = (
                result["home_value_per_injury"] - result["away_value_per_injury"]
            )

        return result

    def create_momentum_xg(
        self,
        features: dict[str, Any]
    ) -> dict[str, float]:
        """
        创建动量 xG 特征

        momentum_xg = 评分加速度 * xG 均值

        逻辑：状态上升且创造机会能力强的球队更危险
        """
        result = {}

        # 主队
        home_xg = features.get("home_rolling_avg_xg_5", 0)
        home_rating_accel = features.get("home_rating_acceleration", 0)

        result["home_momentum_xg"] = home_xg * max(home_rating_accel + 1, 0.5)  # 避免负值
        result["home_xg_efficiency"] = (
            home_xg / max(abs(home_rating_accel) + 0.1, self.epsilon)
        )

        # 客队
        away_xg = features.get("away_rolling_avg_xg_5", 0)
        away_rating_accel = features.get("away_rating_acceleration", 0)

        result["away_momentum_xg"] = away_xg * max(away_rating_accel + 1, 0.5)
        result["away_xg_efficiency"] = (
            away_xg / max(abs(away_rating_accel) + 0.1, self.epsilon)
        )

        # 差值
        result["diff_momentum_xg"] = result["home_momentum_xg"] - result["away_momentum_xg"]

        return result

    def create_power_interaction(
        self,
        features: dict[str, Any]
    ) -> dict[str, float]:
        """
        创建战力交互特征

        综合身价、评分、红牌的交叉特征
        """
        result = {}

        # 主队战力指数
        home_mv = features.get("home_market_value_total", 1)
        home_rating = features.get("home_rolling_avg_rating_5", 6.0)
        home_red = features.get("home_red_cards", 0)

        # 归一化身价 (以 100M 为基准)
        home_mv_norm = home_mv / 100_000_000

        # 战力 = 评分 * (1 / 红牌惩罚) * 身价系数
        home_red_penalty = 1.0 / max(home_red + 1, 1)
        result["home_power_index"] = (
            home_rating * home_red_penalty * (1 + home_mv_norm)
        )

        # 客队战力指数
        away_mv = features.get("away_market_value_total", 1)
        away_rating = features.get("away_rolling_avg_rating_5", 6.0)
        away_red = features.get("away_red_cards", 0)

        away_mv_norm = away_mv / 100_000_000
        away_red_penalty = 1.0 / max(away_red + 1, 1)
        result["away_power_index"] = (
            away_rating * away_red_penalty * (1 + away_mv_norm)
        )

        # 战力差值
        result["diff_power_index"] = result["home_power_index"] - result["away_power_index"]
        result["ratio_power_index"] = (
            result["home_power_index"] / max(result["away_power_index"], self.epsilon)
        )

        return result

    def create_form_consistency(
        self,
        features: dict[str, Any]
    ) -> dict[str, float]:
        """
        创建状态一致性特征

        form_consistency = (评分 - 评分均值) / 评分标准差
        """
        result = {}

        home_rating = features.get("home_rolling_avg_rating_5", 6.0)
        home_rating_std = features.get("home_rating_std", 1.0)

        away_rating = features.get("away_rolling_avg_rating_5", 6.0)
        away_rating_std = features.get("away_rating_std", 1.0)

        # 状态稳定性 (假设基准评分 6.5)
        home_form_stability = abs(home_rating - 6.5) / max(home_rating_std, 0.1)
        away_form_stability = abs(away_rating - 6.5) / max(away_rating_std, 0.1)

        result["home_form_stability"] = home_form_stability
        result["away_form_stability"] = away_form_stability
        result["diff_form_stability"] = home_form_stability - away_form_stability

        return result

    def create_all_interactions(
        self,
        features: dict[str, Any]
    ) -> dict[str, float]:
        """
        创建所有交叉特征

        Args:
            features: 原始特征字典

        Returns:
            交叉特征字典
        """
        interactions = {}

        # 1. 纪律调整身价
        interactions.update(self.create_discipline_adjusted_value(features))

        # 2. 单位伤病身价
        interactions.update(self.create_value_per_injury(features))

        # 3. 动量 xG
        interactions.update(self.create_momentum_xg(features))

        # 4. 战力交互
        interactions.update(self.create_power_interaction(features))

        # 5. 状态一致性
        interactions.update(self.create_form_consistency(features))

        logger.debug(f"Created {len(interactions)} interaction features")

        return interactions


# =============================================================================
# Power Ranking Delta - 战力阶梯
# =============================================================================

class PowerRankingDelta:
    """
    V41.430 战力阶梯计算器

    计算评分加速度：识别球队走势（上坡/下坡）
    """

    def __init__(self, window_short: int = 3, window_long: int = 5):
        self.window_short = window_short  # 近期窗口
        self.window_long = window_long    # 长期窗口

    def calculate_rating_acceleration(
        self,
        rating_history: list[float]
    ) -> dict[str, float]:
        """
        计算评分加速度

        acceleration = 近3场均值 - 近5场均值

        正值 = 走势向上
        负值 = 走势向下
        """
        result = {}

        if not rating_history:
            result["rating_acceleration"] = 0.0
            result["rating_momentum"] = 0.0
            result["rating_volatility"] = 0.0
            return result

        # 近期均值
        recent_avg = np.mean(rating_history[:self.window_short])

        # 长期均值
        long_avg = np.mean(rating_history[:self.window_long]) if len(rating_history) >= self.window_long else recent_avg

        # 加速度
        acceleration = recent_avg - long_avg
        result["rating_acceleration"] = float(acceleration)

        # 动量 (符号化的加速度)
        result["rating_momentum"] = float(np.sign(acceleration))

        # 波动率 (标准差)
        if len(rating_history) >= 2:
            result["rating_volatility"] = float(np.std(rating_history))
        else:
            result["rating_volatility"] = 0.0

        return result


# =============================================================================
# Batch Processing
# =============================================================================

def create_interaction_features_for_match(
    features: dict[str, Any]
) -> dict[str, float]:
    """
    为单场比赛创建所有交互特征

    Args:
        features: 原始特征字典

    Returns:
        交互特征字典
    """
    engine = FeatureInteractionEngine()
    return engine.create_all_interactions(features)


def add_rating_acceleration_features(
    features: dict[str, Any],
    home_rating_history: list[float],
    away_rating_history: list[float]
) -> dict[str, float]:
    """
    添加评分加速度特征

    Args:
        features: 原始特征字典
        home_rating_history: 主队历史评分
        away_rating_history: 客队历史评分

    Returns:
        新增特征字典
    """
    calculator = PowerRankingDelta()
    result = {}

    home_accel = calculator.calculate_rating_acceleration(home_rating_history)
    for k, v in home_accel.items():
        result[f"home_{k}"] = v

    away_accel = calculator.calculate_rating_acceleration(away_rating_history)
    for k, v in away_accel.items():
        result[f"away_{k}"] = v

    # 差值特征
    if "home_rating_acceleration" in result and "away_rating_acceleration" in result:
        result["diff_rating_acceleration"] = (
            result["home_rating_acceleration"] - result["away_rating_acceleration"]
        )

    return result


if __name__ == "__main__":
    # 测试
    logging.basicConfig(level=logging.DEBUG)

    sample_features = {
        "home_market_value_total": 150_000_000,
        "away_market_value_total": 120_000_000,
        "home_red_cards": 2,
        "away_red_cards": 1,
        "home_injury_count": 1,
        "away_injury_count": 2,
        "home_rolling_avg_xg_5": 1.2,
        "away_rolling_avg_xg_5": 1.0,
        "home_rolling_avg_rating_5": 6.8,
        "away_rolling_avg_rating_5": 6.5,
    }

    engine = FeatureInteractionEngine()
    interactions = engine.create_all_interactions(sample_features)

    print("=" * 70)
    print("V41.430 交互特征示例:")
    print("=" * 70)
    for key, value in sorted(interactions.items()):
        if isinstance(value, float):
            print(f"  {key:40s} = {value:.4f}")
        else:
            print(f"  {key:40s} = {value}")
