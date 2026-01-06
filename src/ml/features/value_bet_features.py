#!/usr/bin/env python3
"""
V51.2 价值投注特征计算器 (Expected Value Calculator)
=====================================================

功能:
1. 计算价值投注指标 (Expected Value)
2. Kelly Criterion 最优下注比例
3. Bankroll Growth 期望值

公式:
- EV = (Model_Probability × Market_Odds) - 1
- Kelly = (Model_Prob × Market_Odds - 1) / (Market_Odds - 1)

Author: Senior Quant Architect
Version: V51.2
Date: 2025-12-31
"""

from dataclasses import dataclass
from enum import Enum
import logging
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================
# 枚举类型
# ============================================================


class BetOutcome(Enum):
    """投注结果类型"""
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"


class ValueBetLevel(Enum):
    """价值投注等级"""
    NEGATIVE = "negative"      # EV < 0: 负价值，不建议投注
    LOW = "low"               # 0% <= EV < 2%: 低价值
    MODERATE = "moderate"     # 2% <= EV < 5%: 中等价值
    HIGH = "high"             # 5% <= EV < 10%: 高价值
    EXCELLENT = "excellent"   # EV >= 10%: 极高价值


# ============================================================
# 数据模型
# ============================================================


@dataclass
class ValueBetMetrics:
    """价值投注指标"""

    # 基础输入
    model_prob_home: float      # 模型预测主胜概率
    model_prob_draw: float      # 模型预测平局概率
    model_prob_away: float      # 模型预测客胜概率
    market_odds_home: float     # 市场主胜赔率
    market_odds_draw: float     # 市场平局赔率
    market_odds_away: float     # 市场客胜赔率

    # 价值指标 (3维)
    ev_home: float | None = None       # 主胜期望收益
    ev_draw: float | None = None       # 平局期望收益
    ev_away: float | None = None       # 客胜期望收益

    # Kelly Criterion (3维)
    kelly_home: float | None = None    # 主胜 Kelly 比例
    kelly_draw: float | None = None    # 平局 Kelly 比例
    kelly_away: float | None = None    # 客胜 Kelly 比例

    # 推荐结果
    recommended_bet: BetOutcome | None = None
    value_level: ValueBetLevel | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_probs": {
                "home": self.model_prob_home,
                "draw": self.model_prob_draw,
                "away": self.model_prob_away,
            },
            "market_odds": {
                "home": self.market_odds_home,
                "draw": self.market_odds_draw,
                "away": self.market_odds_away,
            },
            "ev": {
                "home": self.ev_home,
                "draw": self.ev_draw,
                "away": self.ev_away,
            },
            "kelly": {
                "home": self.kelly_home,
                "draw": self.kelly_draw,
                "away": self.kelly_away,
            },
            "recommendation": {
                "bet_outcome": self.recommended_bet.value if self.recommended_bet else None,
                "value_level": self.value_level.value if self.value_level else None,
            },
        }


# ============================================================
# 价值计算器
# ============================================================


class ExpectedValueCalculator:
    """
    期望值计算器

    核心功能:
    1. 计算 EV (Expected Value)
    2. 计算 Kelly Criterion 最优下注比例
    3. 生成投注建议
    """

    # 阈值配置
    EV_THRESHOLD_NEGATIVE = 0.0
    EV_THRESHOLD_LOW = 0.02
    EV_THRESHOLD_MODERATE = 0.05
    EV_THRESHOLD_HIGH = 0.10

    def __init__(self, kelly_fraction: float = 0.25):
        """
        初始化计算器

        Args:
            kelly_fraction: Kelly 分数 (保守策略，通常为 0.25 - 0.5)
        """
        self.kelly_fraction = kelly_fraction
        logger.info(f"EV Calculator 初始化: Kelly Fraction = {kelly_fraction}")

    def calculate_ev(self, model_prob: float, market_odds: float) -> float:
        """
        计算期望值 (Expected Value)

        公式: EV = (Model_Prob × Market_Odds) - 1

        Args:
            model_prob: 模型预测概率 (0-1)
            market_odds: 市场赔率 (小数格式，如 2.50)

        Returns:
            期望值 (百分比，如 0.05 表示 5%)
        """
        if model_prob <= 0 or market_odds <= 1:
            return -1.0  # 无效输入，返回 -100% EV

        ev = (model_prob * market_odds) - 1.0
        return ev

    def calculate_kelly(self, model_prob: float, market_odds: float) -> float:
        """
        计算 Kelly Criterion 最优下注比例

        公式: Kelly = (Model_Prob × Odds - 1) / (Odds - 1)

        Args:
            model_prob: 模型预测概率 (0-1)
            market_odds: 市场赔率

        Returns:
            Kelly 比例 (0-1，如 0.05 表示下注 5% 的资金)
        """
        if market_odds <= 1.0:
            return 0.0

        ev = self.calculate_ev(model_prob, market_odds)

        # Kelly 公式
        kelly = ev / (market_odds - 1.0)

        # 应用保守分数
        kelly_conservative = kelly * self.kelly_fraction

        # 限制在 [0, 1] 范围内
        return max(0.0, min(1.0, kelly_conservative))

    def get_value_level(self, ev: float) -> ValueBetLevel:
        """
        根据期望值确定价值等级

        Args:
            ev: 期望值

        Returns:
            ValueBetLevel
        """
        if ev < self.EV_THRESHOLD_NEGATIVE:
            return ValueBetLevel.NEGATIVE
        if ev < self.EV_THRESHOLD_LOW:
            return ValueBetLevel.LOW
        if ev < self.EV_THRESHOLD_MODERATE:
            return ValueBetLevel.MODERATE
        if ev < self.EV_THRESHOLD_HIGH:
            return ValueBetLevel.HIGH
        return ValueBetLevel.EXCELLENT

    def calculate_value_metrics(
        self,
        model_probs: dict[str, float],  # {"home": 0.5, "draw": 0.3, "away": 0.2}
        market_odds: dict[str, float],  # {"home": 2.0, "draw": 3.2, "away": 4.0}
    ) -> ValueBetMetrics:
        """
        计算所有价值指标

        Args:
            model_probs: 模型预测概率
            market_odds: 市场赔率

        Returns:
            ValueBetMetrics
        """
        # 创建基础对象
        metrics = ValueBetMetrics(
            model_prob_home=model_probs.get("home", 0.0),
            model_prob_draw=model_probs.get("draw", 0.0),
            model_prob_away=model_probs.get("away", 0.0),
            market_odds_home=market_odds.get("home", 1.0),
            market_odds_draw=market_odds.get("draw", 1.0),
            market_odds_away=market_odds.get("away", 1.0),
        )

        # 计算 EV
        metrics.ev_home = self.calculate_ev(metrics.model_prob_home, metrics.market_odds_home)
        metrics.ev_draw = self.calculate_ev(metrics.model_prob_draw, metrics.market_odds_draw)
        metrics.ev_away = self.calculate_ev(metrics.model_prob_away, metrics.market_odds_away)

        # 计算 Kelly
        metrics.kelly_home = self.calculate_kelly(metrics.model_prob_home, metrics.market_odds_home)
        metrics.kelly_draw = self.calculate_kelly(metrics.model_prob_draw, metrics.market_odds_draw)
        metrics.kelly_away = self.calculate_kelly(metrics.model_prob_away, metrics.market_odds_away)

        # 确定推荐投注
        ev_dict = {
            BetOutcome.HOME_WIN: metrics.ev_home,
            BetOutcome.DRAW: metrics.ev_draw,
            BetOutcome.AWAY_WIN: metrics.ev_away,
        }

        # 找到最大 EV
        best_outcome = max(ev_dict, key=ev_dict.get)
        best_ev = ev_dict[best_outcome]

        if best_ev > 0:
            metrics.recommended_bet = best_outcome
            metrics.value_level = self.get_value_level(best_ev)
        else:
            metrics.recommended_bet = None
            metrics.value_level = ValueBetLevel.NEGATIVE

        return metrics

    def calculate_roi_potential(
        self,
        metrics: ValueBetMetrics,
        num_bets: int = 100,
        avg_stake: float = 100.0,
    ) -> dict[str, float]:
        """
        计算潜在 ROI

        Args:
            metrics: 价值投注指标
            num_bets: 投注次数
            avg_stake: 平均投注金额

        Returns:
            ROI 预测数据
        """
        if metrics.recommended_bet is None:
            return {
                "expected_roi": -0.05,
                "expected_profit": -avg_stake * num_bets * 0.05,
                "win_probability": 0.0,
            }

        # 获取推荐结果的概率和 EV
        if metrics.recommended_bet == BetOutcome.HOME_WIN:
            prob = metrics.model_prob_home
            ev = metrics.ev_home
            kelly = metrics.kelly_home
            odds = metrics.market_odds_home
        elif metrics.recommended_bet == BetOutcome.DRAW:
            prob = metrics.model_prob_draw
            ev = metrics.ev_draw
            kelly = metrics.kelly_draw
            odds = metrics.market_odds_draw
        else:  # AWAY_WIN
            prob = metrics.model_prob_away
            ev = metrics.ev_away
            kelly = metrics.kelly_away
            odds = metrics.market_odds_away

        # 使用 Kelly 比例作为投注金额比例
        stake_ratio = kelly
        actual_stake = avg_stake * stake_ratio

        # 计算期望收益
        # EV = (Win_Profit × Win_Prob) - (Stake × Lose_Prob)
        # Win_Profit = Stake × (Odds - 1)
        expected_profit_per_bet = actual_stake * ev
        total_expected_profit = expected_profit_per_bet * num_bets

        # 计算期望 ROI (考虑投注金额比例)
        total_investment = actual_stake * num_bets
        expected_roi = total_expected_profit / total_investment if total_investment > 0 else 0

        return {
            "expected_roi": expected_roi,
            "expected_profit": total_expected_profit,
            "total_investment": total_investment,
            "win_probability": prob,
            "kelly_stake_ratio": stake_ratio,
            "recommended_stake": actual_stake,
        }


# ============================================================
# 集成到特征引擎
# ============================================================


def calculate_value_gap(
    model_probs: dict[str, float],
    market_odds: dict[str, float],
    kelly_fraction: float = 0.25,
) -> dict[str, float]:
    """
    计算价值缺口 (集成接口)

    Args:
        model_probs: 模型预测概率 {"home": 0.5, "draw": 0.3, "away": 0.2}
        market_odds: 市场赔率 {"home": 2.0, "draw": 3.2, "away": 4.0}
        kelly_fraction: Kelly 分数

    Returns:
        价值特征字典
    """
    calculator = ExpectedValueCalculator(kelly_fraction=kelly_fraction)
    metrics = calculator.calculate_value_metrics(model_probs, market_odds)

    return {
        # EV 特征 (3维)
        "ev_home": metrics.ev_home or 0.0,
        "ev_draw": metrics.ev_draw or 0.0,
        "ev_away": metrics.ev_away or 0.0,
        "ev_max": max(metrics.ev_home or 0, metrics.ev_draw or 0, metrics.ev_away or 0),
        "ev_gap": (
            max(metrics.ev_home or 0, metrics.ev_draw or 0, metrics.ev_away or 0)
            - min(metrics.ev_home or 0, metrics.ev_draw or 0, metrics.ev_away or 0)
        ),
        # Kelly 特征 (3维)
        "kelly_home": metrics.kelly_home or 0.0,
        "kelly_draw": metrics.kelly_draw or 0.0,
        "kelly_away": metrics.kelly_away or 0.0,
        "kelly_max": max(metrics.kelly_home or 0, metrics.kelly_draw or 0, metrics.kelly_away or 0),
        # 推荐特征
        "recommended_bet_code": {
            None: 0,
            BetOutcome.HOME_WIN: 1,
            BetOutcome.DRAW: 2,
            BetOutcome.AWAY_WIN: 3,
        }.get(metrics.recommended_bet, 0),
        "value_level_code": {
            ValueBetLevel.NEGATIVE: 0,
            ValueBetLevel.LOW: 1,
            ValueBetLevel.MODERATE: 2,
            ValueBetLevel.HIGH: 3,
            ValueBetLevel.EXCELLENT: 4,
        }.get(metrics.value_level, 0),
    }


# ============================================================
# 批量处理
# ============================================================


def batch_calculate_value_features(
    predictions: list[dict[str, Any]],
    odds_data: list[dict[str, Any]],
    kelly_fraction: float = 0.25,
) -> list[dict[str, Any]]:
    """
    批量计算价值投注特征

    Args:
        predictions: 模型预测列表 [{"match_id": "...", "probs": {...}}, ...]
        odds_data: 赔率数据列表 [{"match_id": "...", "odds": {...}}, ...]
        kelly_fraction: Kelly 分数

    Returns:
        增强后的预测列表 (包含价值特征)
    """
    # 构建 match_id -> odds 的映射
    odds_map = {o["match_id"]: o["odds"] for o in odds_data}

    calculator = ExpectedValueCalculator(kelly_fraction=kelly_fraction)
    results = []

    for pred in predictions:
        match_id = pred.get("match_id")
        model_probs = pred.get("probs", {})
        market_odds = odds_map.get(match_id, {})

        if not market_odds:
            # 没有赔率数据，跳过
            continue

        # 计算价值指标
        metrics = calculator.calculate_value_metrics(model_probs, market_odds)

        # 合并到预测数据
        enriched_pred = {**pred, "value_metrics": metrics.to_dict()}
        results.append(enriched_pred)

    return results


if __name__ == "__main__":
    # 测试代码
    logging.basicConfig(level=logging.INFO)

    # 示例 1: 高价值投注
    model_probs_1 = {"home": 0.55, "draw": 0.25, "away": 0.20}
    market_odds_1 = {"home": 2.20, "draw": 3.40, "away": 3.80}

    value_features_1 = calculate_value_gap(model_probs_1, market_odds_1)
    print("示例 1 - 高价值投注:")
    print(f"  EV 主胜: {value_features_1['ev_home']:.2%}")
    print(f"  EV 最大: {value_features_1['ev_max']:.2%}")
    print(f"  推荐投注: {value_features_1['recommended_bet_code']}")
    print(f"  价值等级: {value_features_1['value_level_code']}")
    print()

    # 示例 2: 低价值投注
    model_probs_2 = {"home": 0.45, "draw": 0.30, "away": 0.25}
    market_odds_2 = {"home": 2.10, "draw": 3.30, "away": 3.50}

    value_features_2 = calculate_value_gap(model_probs_2, market_odds_2)
    print("示例 2 - 低价值投注:")
    print(f"  EV 主胜: {value_features_2['ev_home']:.2%}")
    print(f"  EV 最大: {value_features_2['ev_max']:.2%}")
    print(f"  推荐投注: {value_features_2['recommended_bet_code']}")
    print(f"  价值等级: {value_features_2['value_level_code']}")
