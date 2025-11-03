
"""
期望值(Expected Value)计算器
EV Calculator
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class EVCalculationResult:
    """EV计算结果"""
    bet_type: str
    odds: float
    probability: float
    ev_value: float
    recommendation: str
    confidence: float


class EVCalculator:
    """期望值计算器"""

    def __init__(self):
        """初始化EV计算器"""
        self.commission_rate = 0.02  # 2%佣金率

    def calculate_ev(self, odds: float, probability: float, stake: float = 100.0) -> EVCalculationResult:
        """
        计算期望值

        Args:
            odds: 赔率
            probability: 胜率概率 (0-1)
            stake: 投注金额

        Returns:
            EV计算结果
        """
        # EV = (概率 * 赔率 * 投注额) - 投注额
        potential_win = odds * stake
        expected_return = probability * potential_win
        ev_value = expected_return - stake

        # 考虑佣金
        ev_value_after_commission = ev_value * (1 - self.commission_rate)

        # 生成推荐
        if ev_value_after_commission > 0:
            recommendation = "bet"
            confidence = min(abs(ev_value_after_commission) / stake, 1.0)
        else:
            recommendation = "no_bet"
            confidence = min(abs(ev_value_after_commission) / stake, 1.0)

        return EVCalculationResult(
            bet_type="single",
            odds=odds,
            probability=probability,
            ev_value=ev_value_after_commission,
            recommendation=recommendation,
            confidence=confidence
        )

    def analyze_betting_opportunity(self, odds: float, model_probability: float,
                                   market_probability: float = None) -> Dict[str, Any]:
        """
        分析投注机会

        Args:
            odds: 赔率
            model_probability: 模型预测概率
            market_probability: 市场隐含概率

        Returns:
            分析结果
        """
        # 计算市场隐含概率
        if market_probability is None:
            market_probability = 1.0 / odds if odds > 0 else 0.0

        # 计算价值
        value_edge = model_probability - market_probability

        result = {
            "odds": odds,
            "model_probability": model_probability,
            "market_probability": market_probability,
            "value_edge": value_edge,
            "ev_calculation": self.calculate_ev(odds, model_probability),
            "recommendation": "value_bet" if value_edge > 0.05 else "no_value"
        }

        return result
