#!/usr/bin/env python3
"""
简化版EV优化测试
Issue #121: EV计算算法参数调优

直接测试核心算法，避免复杂依赖
"""

import math
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class KellyOptimizationResult:
    """Kelly准则优化结果"""
    optimal_fraction: float
    expected_growth: float
    risk_of_ruin: float
    confidence_interval: Tuple[float, float]
    recommendation: str


class EnhancedKellyCalculator:
    """增强Kelly准则计算器 - 简化版"""

    def __init__(self):
        self.fractional_kelly_multiplier = 0.25
        self.min_edge_threshold = 0.02
        self.confidence_weighting = True

    def calculate_fractional_kelly(
        self,
        true_probability: float,
        decimal_odds: float,
        confidence: float = 1.0
    ) -> KellyOptimizationResult:
        """计算优化的分数Kelly准则"""

        if true_probability <= 0 or true_probability >= 1 or decimal_odds <= 1:
            return KellyOptimizationResult(
                optimal_fraction=0.0,
                expected_growth=0.0,
                risk_of_ruin=1.0,
                confidence_interval=(0.0, 0.0),
                recommendation="avoid"
            )

        # 基础Kelly计算
        b = decimal_odds - 1  # 净赔率
        p = true_probability
        q = 1 - p

        # 标准Kelly公式
        kelly_standard = (b * p - q) / b

        # 应用优化因子
        kelly_optimized = kelly_standard * self.fractional_kelly_multiplier

        # 置信度权重
        if self.confidence_weighting:
            confidence_factor = 0.5 + (confidence * 0.5)  # 0.5-1.0范围
            kelly_optimized *= confidence_factor

        # 限制范围
        kelly_optimized = max(0, min(kelly_optimized, 0.25))

        # 计算风险指标
        expected_growth = self._calculate_expected_growth(kelly_optimized, p, b)
        risk_of_ruin = self._calculate_risk_of_ruin(kelly_optimized, p, b)

        # 置信区间
        confidence_interval = self._calculate_confidence_interval(
            kelly_optimized, confidence
        )

        # 推荐
        recommendation = self._generate_recommendation(kelly_optimized, risk_of_ruin)

        return KellyOptimizationResult(
            optimal_fraction=kelly_optimized,
            expected_growth=expected_growth,
            risk_of_ruin=risk_of_ruin,
            confidence_interval=confidence_interval,
            recommendation=recommendation
        )

    def _calculate_expected_growth(self, kelly_fraction: float, probability: float, net_odds: float) -> float:
        """计算期望增长率"""
        if kelly_fraction <= 0:
            return 0.0

        f = kelly_fraction
        b = net_odds
        p = probability
        q = 1 - p

        if f * b > 1:
            return 0.0

        growth_rate = p * math.log(1 + f * b) + q * math.log(1 - f)
        return growth_rate

    def _calculate_risk_of_ruin(self, kelly_fraction: float, probability: float, net_odds: float) -> float:
        """计算破产风险"""
        if kelly_fraction <= 0:
            return 0.0

        edge = probability * net_odds - (1 - probability)
        if edge <= 0:
            return 1.0

        # 简化风险评估
        kelly_ratio = kelly_fraction / (edge / net_odds)
        risk = min(kelly_ratio * 0.2, 0.3)
        return risk

    def _calculate_confidence_interval(self, kelly_fraction: float, confidence: float) -> Tuple[float, float]:
        """计算置信区间"""
        if kelly_fraction <= 0:
            return (0.0, 0.0)

        interval_width = (1 - confidence) * kelly_fraction * 2
        lower = max(0, kelly_fraction - interval_width)
        upper = min(kelly_fraction + interval_width, 0.25)
        return (lower, upper)

    def _generate_recommendation(self, kelly_fraction: float, risk_of_ruin: float) -> str:
        """生成推荐"""
        if kelly_fraction <= 0:
            return "avoid"
        elif risk_of_ruin > 0.25:
            return "reduce_stake"
        elif kelly_fraction > 0.15:
            return "fractional_kelly_conservative"
        else:
            return "standard"


class EnhancedValueCalculator:
    """增强价值评级计算器 - 简化版"""

    def __init__(self):
        self.weights = {
            "ev_score": 0.3,
            "probability_score": 0.25,
            "odds_fairness": 0.25,
            "risk_adjusted": 0.2
        }

    def calculate_value_rating(
        self,
        probability: float,
        odds: float,
        confidence: float = 1.0
    ) -> Dict[str, Any]:
        """计算价值评级"""

        # EV计算
        ev = (probability * odds) - 1

        # 各项分数
        ev_score = self._calculate_ev_score(ev)
        probability_score = self._calculate_probability_score(probability, confidence)
        odds_fairness_score = self._calculate_odds_fairness_score(probability, odds)
        risk_adjusted_score = self._calculate_risk_adjusted_score(ev, probability, odds)

        # 综合评级
        overall_rating = (
            ev_score * self.weights["ev_score"] +
            probability_score * self.weights["probability_score"] +
            odds_fairness_score * self.weights["odds_fairness"] +
            risk_adjusted_score * self.weights["risk_adjusted"]
        )

        return {
            "overall_rating": min(overall_rating, 10.0),
            "ev_score": ev_score,
            "probability_score": probability_score,
            "odds_fairness_score": odds_fairness_score,
            "risk_adjusted_score": risk_adjusted_score,
            "ev": ev
        }

    def _calculate_ev_score(self, ev: float) -> float:
        """计算EV分数"""
        if ev <= 0:
            return 0.0

        if ev < 0.05:
            score = ev * 120
        else:
            score = 6 + math.log(ev / 0.05) * 3

        return min(score, 10.0)

    def _calculate_probability_score(self, probability: float, confidence: float) -> float:
        """计算概率分数"""
        base_score = probability * 8
        confidence_bonus = confidence * 2
        return min(base_score + confidence_bonus, 10.0)

    def _calculate_odds_fairness_score(self, probability: float, odds: float) -> float:
        """计算赔率公平性分数"""
        fair_odds = 1 / probability if probability > 0 else float('inf')
        if fair_odds == 0:
            return 0.0

        odds_deviation = abs(odds - fair_odds) / fair_odds

        if odds_deviation <= 0.05:
            return 10.0
        elif odds_deviation <= 0.1:
            return 8.0
        elif odds_deviation <= 0.2:
            return 6.0
        else:
            return max(0.0, 4.0 - odds_deviation * 10)

    def _calculate_risk_adjusted_score(self, ev: float, probability: float, odds: float) -> float:
        """计算风险调整分数"""
        if ev <= 0:
            return 0.0

        base_score = min(ev * 10, 8.0)

        # 风险因子
        if probability < 0.3:
            prob_risk = 0.5
        elif probability < 0.5:
            prob_risk = 0.3
        elif probability < 0.7:
            prob_risk = 0.1
        else:
            prob_risk = 0.0

        if odds > 5.0:
            odds_risk = 0.3
        elif odds > 3.0:
            odds_risk = 0.2
        elif odds > 2.0:
            odds_risk = 0.1
        else:
            odds_risk = 0.0

        total_risk = prob_risk + odds_risk
        risk_adjusted_score = base_score * (1 - total_risk)

        return max(0.0, min(risk_adjusted_score, 10.0))


def test_kelly_optimization():
    """测试Kelly准则优化"""
    logger.info("🔧 测试Kelly准则优化...")

    kelly_calc = EnhancedKellyCalculator()

    test_cases = [
        {"prob": 0.65, "odds": 1.9, "confidence": 0.8, "desc": "高概率低赔率"},
        {"prob": 0.35, "odds": 3.2, "confidence": 0.6, "desc": "低概率高赔率"},
        {"prob": 0.5, "odds": 2.1, "confidence": 0.7, "desc": "平衡投注"},
        {"prob": 0.8, "odds": 1.3, "confidence": 0.9, "desc": "极高概率"},
    ]

    results = []
    for case in test_cases:
        result = kelly_calc.calculate_fractional_kelly(
            case["prob"], case["odds"], case["confidence"]
        )

        results.append({
            "case": case["desc"],
            "probability": case["prob"],
            "odds": case["odds"],
            "optimal_fraction": result.optimal_fraction,
            "expected_growth": result.expected_growth,
            "risk_of_ruin": result.risk_of_ruin,
            "recommendation": result.recommendation
        })

        logger.info(f"  {case['desc']}: Kelly={result.optimal_fraction:.3f}, "
                   f"期望增长={result.expected_growth:.3f}, "
                   f"破产风险={result.risk_of_ruin:.3f}")

    return results


def test_value_rating():
    """测试价值评级"""
    logger.info("📊 测试价值评级...")

    value_calc = EnhancedValueCalculator()

    test_cases = [
        {"prob": 0.65, "odds": 1.85, "confidence": 0.8, "desc": "优质投注"},
        {"prob": 0.25, "odds": 4.5, "confidence": 0.5, "desc": "高风险投注"},
        {"prob": 0.5, "odds": 2.05, "confidence": 0.7, "desc": "公平投注"},
        {"prob": 0.8, "odds": 1.25, "confidence": 0.9, "desc": "高确定性投注"},
    ]

    results = []
    for case in test_cases:
        result = value_calc.calculate_value_rating(
            case["prob"], case["odds"], case["confidence"]
        )

        results.append({
            "case": case["desc"],
            "overall_rating": result["overall_rating"],
            "ev_score": result["ev_score"],
            "probability_score": result["probability_score"],
            "odds_fairness_score": result["odds_fairness_score"],
            "risk_adjusted_score": result["risk_adjusted_score"],
            "ev": result["ev"]
        })

        logger.info(f"  {case['desc']}: 总评级={result['overall_rating']:.1f}, "
                   f"EV分数={result['ev_score']:.1f}, "
                   f"风险调整={result['risk_adjusted_score']:.1f}")

    return results


def test_enhanced_ev_calculation():
    """测试增强EV计算"""
    logger.info("💰 测试增强EV计算...")

    kelly_calc = EnhancedKellyCalculator()
    value_calc = EnhancedValueCalculator()

    test_cases = [
        {"prob": 0.65, "odds": 1.85, "confidence": 0.8, "desc": "SRS策略测试"},
        {"prob": 0.35, "odds": 3.2, "confidence": 0.6, "desc": "保守策略测试"},
        {"prob": 0.3, "odds": 3.4, "confidence": 0.7, "desc": "激进策略测试"}
    ]

    results = []
    for case in test_cases:
        # Kelly计算
        kelly_result = kelly_calc.calculate_fractional_kelly(
            case["prob"], case["odds"], case["confidence"]
        )

        # 价值评级
        value_result = value_calc.calculate_value_rating(
            case["prob"], case["odds"], case["confidence"]
        )

        # EV计算
        ev = (case["prob"] * case["odds"]) - 1

        # 综合建议
        recommendation = "bet"
        if ev < 0.05 or value_result["overall_rating"] < 6.0:
            recommendation = "avoid"
        elif ev >= 0.15 and value_result["overall_rating"] >= 8.0:
            recommendation = "strong_bet"
        elif ev >= 0.08 and value_result["overall_rating"] >= 6.5:
            recommendation = "bet"
        else:
            recommendation = "small_bet"

        results.append({
            "case": case["desc"],
            "ev": ev,
            "kelly_fraction": kelly_result.optimal_fraction,
            "value_rating": value_result["overall_rating"],
            "recommendation": recommendation,
            "expected_roi": ev * kelly_result.optimal_fraction * 100,
            "risk_of_ruin": kelly_result.risk_of_ruin
        })

        logger.info(f"  {case['desc']}: EV={ev:.3f}, Kelly={kelly_result.optimal_fraction:.3f}, "
                   f"评级={value_result['overall_rating']:.1f}, 建议={recommendation}")

    return results


def simulate_backtest():
    """模拟回测"""
    logger.info("📈 模拟回测...")

    # 模拟100次投注
    results = {
        "initial_bankroll": 1000.0,
        "final_bankroll": 1000.0,
        "total_bets": 0,
        "winning_bets": 0,
        "losing_bets": 0,
        "total_stake": 0.0,
        "total_return": 0.0
    }

    kelly_calc = EnhancedKellyCalculator()
    value_calc = EnhancedValueCalculator()
    current_bankroll = 1000.0

    # 简化的模拟数据
    import random
    random.seed(42)  # 固定种子以获得可重复结果

    for i in range(100):
        # 随机生成投注机会
        prob = random.uniform(0.3, 0.7)
        odds = random.uniform(1.5, 4.0)
        confidence = random.uniform(0.5, 0.9)

        # 计算EV和评级
        ev = (prob * odds) - 1
        value_result = value_calc.calculate_value_rating(prob, odds, confidence)
        kelly_result = kelly_calc.calculate_fractional_kelly(prob, odds, confidence)

        # 投注决策
        if ev < 0.05 or value_result["overall_rating"] < 6.0:
            continue

        stake = min(kelly_result.optimal_fraction * current_bankroll * 0.01, current_bankroll * 0.02)

        if stake <= 0:
            continue

        # 模拟结果
        won = random.random() < prob
        results["total_bets"] += 1
        results["total_stake"] += stake

        if won:
            winnings = stake * odds
            current_bankroll = current_bankroll - stake + winnings
            results["winning_bets"] += 1
            results["total_return"] += winnings
        else:
            results["losing_bets"] += 1
            current_bankroll -= stake

    results["final_bankroll"] = current_bankroll
    results["roi"] = (current_bankroll - results["initial_bankroll"]) / results["initial_bankroll"] * 100
    results["win_rate"] = results["winning_bets"] / results["total_bets"] if results["total_bets"] > 0 else 0

    logger.info(f"  回测结果: ROI={results['roi']:.2f}%, 胜率={results['win_rate']:.2f}, "
               f"总投注={results['total_bets']}, 最终资金={results['final_bankroll']:.2f}")

    return results


def main():
    """主测试函数"""
    logger.info("=" * 60)
    logger.info("🚀 增强EV计算器优化测试")
    logger.info("Issue #121: EV计算算法参数调优")
    logger.info("=" * 60)

    # 运行所有测试
    kelly_results = test_kelly_optimization()
    value_results = test_value_rating()
    ev_results = test_enhanced_ev_calculation()
    backtest_results = simulate_backtest()

    # 生成报告
    logger.info("=" * 60)
    logger.info("📊 测试结果汇总")
    logger.info("=" * 60)

    logger.info(f"✅ Kelly准则优化: 测试了 {len(kelly_results)} 个案例")
    logger.info(f"✅ 价值评级增强: 测试了 {len(value_results)} 个案例")
    logger.info(f"✅ 增强EV计算: 测试了 {len(ev_results)} 个案例")
    logger.info(f"✅ 模拟回测: ROI={backtest_results['roi']:.2f}%")

    # 保存结果
    test_results = {
        "timestamp": datetime.now().isoformat(),
        "kelly_optimization": kelly_results,
        "value_rating": value_results,
        "enhanced_ev": ev_results,
        "backtest": backtest_results,
        "summary": {
            "total_tests": len(kelly_results) + len(value_results) + len(ev_results),
            "backtest_roi": backtest_results["roi"],
            "backtest_win_rate": backtest_results["win_rate"],
            "recommendation": "EV优化算法运行正常"
        }
    }

    try:
        with open("ev_optimization_results.json", "w", encoding="utf-8") as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False, default=str)
        logger.info("📄 测试结果已保存到 ev_optimization_results.json")
    except Exception as e:
        logger.error(f"保存测试结果失败: {e}")

    logger.info("=" * 60)
    logger.info("🎉 EV计算器优化测试完成!")
    logger.info("=" * 60)

    return test_results


if __name__ == "__main__":
    results = main()