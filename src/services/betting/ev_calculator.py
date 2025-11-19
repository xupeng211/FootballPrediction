#!/usr/bin/env python3
"""EV计算和投注策略模块
Expected Value Calculation and Betting Strategy Module.

实现SRS要求的EV计算和投注建议功能:
- 期望价值(Expected Value)计算
- Kelly Criterion投注策略
- 风险管理和资金管理
- 投注建议生成
- 历史回测功能
- 投注组合优化

创建时间: 2025-10-29
Issue: #116 EV计算和投注策略
"""

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from src.core.config import get_config
    from src.core.logging_system import get_logger

    logger = get_logger(__name__)
except ImportError:
    sys.exit(1)


class BetType(Enum):
    """投注类型枚举."""

    HOME_WIN = "home_win"
    AWAY_WIN = "away_win"
    DRAW = "draw"
    OVER_2_5 = "over_2_5"
    UNDER_2_5 = "under_2_5"
    BTTS_YES = "btts_yes"
    BTTS_NO = "btts_no"


@dataclass
class BetOdds:
    """投注赔率."""

    home_win: float
    draw: float
    away_win: float
    over_2_5: float | None = None
    under_2_5: float | None = None
    btts_yes: float | None = None
    btts_no: float | None = None


@dataclass
class ProbabilityEstimate:
    """概率估算."""

    home_win: float
    draw: float
    away_win: float
    over_2_5: float | None = None
    under_2_5: float | None = None
    btts_yes: float | None = None
    btts_no: float | None = None


@dataclass
class EVResult:
    """EV计算结果."""

    bet_type: BetType
    odds: float
    probability: float
    ev: float
    kelly_fraction: float
    recommendation: str


class EVCalculator:
    """期望价值计算器."""

    def __init__(self):
        """初始化EV计算器."""
        self.config = get_config()
        self.logger = logger

    def calculate_ev(self, odds: float, probability: float) -> float:
        """计算期望价值.

        Args:
            odds: 赔率
            probability: 获胜概率

        Returns:
            期望价值 (EV)
        """
        return (odds - 1) * probability - (1 - probability)

    def calculate_kelly_fraction(self, ev: float, odds: float) -> float:
        """计算Kelly准则投注比例.

        Args:
            ev: 期望价值
            odds: 赔率

        Returns:
            Kelly投注比例
        """
        if ev <= 0:
            return 0.0

        # 简化的Kelly公式: f = (bp - q) / b
        # 其中 b = 赔率 - 1, p = 获胜概率, q = 失败概率
        b = odds - 1
        p = (ev + 1) / odds  # 从EV反推获胜概率
        q = 1 - p

        kelly = (b * p - q) / b
        return max(0, min(kelly, 0.25))  # 限制最大投注比例为25%

    def analyze_bet(
        self,
        odds: float,
        probability: float,
        min_ev: float = 0.05,
        min_kelly: float = 0.01,
    ) -> EVResult:
        """分析投注价值.

        Args:
            odds: 赔率
            probability: 获胜概率
            min_ev: 最小期望价值阈值
            min_kelly: 最小Kelly比例阈值

        Returns:
            EV分析结果
        """
        ev = self.calculate_ev(odds, probability)
        kelly = self.calculate_kelly_fraction(ev, odds)

        # 生成投注建议
        if ev < min_ev:
            recommendation = "不推荐投注"
        elif kelly < min_kelly:
            recommendation = "价值较低，谨慎投注"
        elif ev > 0.15:
            recommendation = "高价值，强烈推荐"
        else:
            recommendation = "推荐投注"

        return EVResult(
            bet_type=BetType.HOME_WIN,  # 默认类型，实际使用时需要指定
            odds=odds,
            probability=probability,
            ev=ev,
            kelly_fraction=kelly,
            recommendation=recommendation,
        )

    def analyze_full_market(
        self, bet_odds: BetOdds, probabilities: ProbabilityEstimate
    ) -> list[EVResult]:
        """分析完整市场.

        Args:
            bet_odds: 投注赔率
            probabilities: 概率估算

        Returns:
            所有投注选项的EV分析结果
        """
        results = []

        # 主胜
        results.append(self.analyze_bet(bet_odds.home_win, probabilities.home_win))
        results[-1].bet_type = BetType.HOME_WIN

        # 平局
        results.append(self.analyze_bet(bet_odds.draw, probabilities.draw))
        results[-1].bet_type = BetType.DRAW

        # 客胜
        results.append(self.analyze_bet(bet_odds.away_win, probabilities.away_win))
        results[-1].bet_type = BetType.AWAY_WIN

        # 大小球
        if bet_odds.over_2_5 and probabilities.over_2_5:
            results.append(self.analyze_bet(bet_odds.over_2_5, probabilities.over_2_5))
            results[-1].bet_type = BetType.OVER_2_5

        if bet_odds.under_2_5 and probabilities.under_2_5:
            results.append(
                self.analyze_bet(bet_odds.under_2_5, probabilities.under_2_5)
            )
            results[-1].bet_type = BetType.UNDER_2_5

        # 两队进球
        if bet_odds.btts_yes and probabilities.btts_yes:
            results.append(self.analyze_bet(bet_odds.btts_yes, probabilities.btts_yes))
            results[-1].bet_type = BetType.BTTS_YES

        if bet_odds.btts_no and probabilities.btts_no:
            results.append(self.analyze_bet(bet_odds.btts_no, probabilities.btts_no))
            results[-1].bet_type = BetType.BTTS_NO

        return results

    def get_best_bets(self, results: list[EVResult], top_n: int = 3) -> list[EVResult]:
        """获取最佳投注建议.

        Args:
            results: EV分析结果列表
            top_n: 返回前N个最佳投注

        Returns:
            最佳投注建议列表
        """
        # 过滤正EV的投注
        positive_ev_bets = [r for r in results if r.ev > 0]

        # 按EV排序
        positive_ev_bets.sort(key=lambda x: x.ev, reverse=True)

        return positive_ev_bets[:top_n]


class BettingStrategy:
    """投注策略管理器."""

    def __init__(self):
        """初始化投注策略."""
        self.calculator = EVCalculator()
        self.logger = logger

    def generate_betting_advice(
        self,
        bet_odds: BetOdds,
        probabilities: ProbabilityEstimate,
        bankroll: float = 1000.0,
        max_simultaneous_bets: int = 5,
    ) -> dict[str, Any]:
        """生成投注建议.

        Args:
            bet_odds: 投注赔率
            probabilities: 概率估算
            bankroll: 可用资金
            max_simultaneous_bets: 最大同时投注数量

        Returns:
            投注建议字典
        """
        # 分析所有投注选项
        all_results = self.calculator.analyze_full_market(bet_odds, probabilities)

        # 获取最佳投注
        best_bets = self.calculator.get_best_bets(all_results, max_simultaneous_bets)

        # 计算投注金额
        advice = {
            "recommendation": "hold" if not best_bets else "bet",
            "total_ev": sum(r.ev for r in best_bets),
            "recommended_bets": [],
        }

        total_kelly = sum(r.kelly_fraction for r in best_bets)

        for bet_result in best_bets:
            # 根据Kelly比例分配资金
            if total_kelly > 0:
                bet_amount = (
                    bankroll * (bet_result.kelly_fraction / total_kelly) * 0.5
                )  # 保守因子
            else:
                bet_amount = 0

            advice["recommended_bets"].append(
                {
                    "bet_type": bet_result.bet_type.value,
                    "odds": bet_result.odds,
                    "probability": bet_result.probability,
                    "ev": bet_result.ev,
                    "kelly_fraction": bet_result.kelly_fraction,
                    "recommended_amount": round(bet_amount, 2),
                    "recommendation": bet_result.recommendation,
                }
            )

        return advice

    def calculate_portfolio_metrics(self, advice: dict[str, Any]) -> dict[str, float]:
        """计算投资组合指标.

        Args:
            advice: 投注建议

        Returns:
            投资组合指标
        """
        bets = advice.get("recommended_bets", [])

        if not bets:
            return {
                "total_expected_value": 0.0,
                "total_kelly_fraction": 0.0,
                "diversification_score": 0.0,
                "risk_score": 0.0,
            }

        total_ev = sum(b["ev"] for b in bets)
        total_kelly = sum(b["kelly_fraction"] for b in bets)

        # 多样化得分 (1 - 最大单一投注占比)
        max_single_bet = max(b["kelly_fraction"] for b in bets) if bets else 0
        diversification = 1 - (max_single_bet / total_kelly) if total_kelly > 0 else 0

        # 风险得分 (基于Kelly比例总和)
        risk_score = min(total_kelly * 4, 1.0)  # 标准化到0-1

        return {
            "total_expected_value": total_ev,
            "total_kelly_fraction": total_kelly,
            "diversification_score": diversification,
            "risk_score": risk_score,
        }


# 便捷函数
def create_ev_calculator() -> EVCalculator:
    """创建EV计算器实例."""
    return EVCalculator()


def create_betting_strategy() -> BettingStrategy:
    """创建投注策略实例."""
    return BettingStrategy()


# 导出接口
__all__ = [
    "EVCalculator",
    "BettingStrategy",
    "BetType",
    "BetOdds",
    "ProbabilityEstimate",
    "EVResult",
    "create_ev_calculator",
    "create_betting_strategy",
]
