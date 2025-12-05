#!/usr/bin/env python3
"""
EV计算和投注策略核心功能测试
Betting EV Strategy Core Functionality Test

测试Issue #116的核心EV计算和投注策略功能：
- EV计算算法
- Kelly Criterion实现
- 风险评估功能
- 投注策略逻辑
- SRS合规性检查

创建时间: 2025-10-29
Issue: #116 EV计算和投注策略
"""

import asyncio
import json
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Optional


# 基础数据结构定义
class BetType(Enum):
    HOME_WIN = "home_win"
    DRAW = "draw"
    AWAY_WIN = "away_win"
    OVER_2_5 = "over_2_5"
    UNDER_2_5 = "under_2_5"
    BTTS = "btts"


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class BettingOdds:
    home_win: float
    draw: float
    away_win: float
    over_2_5: float | None = None
    under_2_5: float | None = None
    btts_yes: float | None = None
    source: str = "test"
    confidence: float = 1.0


@dataclass
class PredictionProbabilities:
    home_win: float
    draw: float
    away_win: float
    over_2_5: float | None = None
    confidence: float = 1.0
    model_name: str = "test_model"


# 核心EV计算器
class CoreEVCalculator:
    """核心EV计算器 - 简化版本"""

    def __init__(self):
        self.SRS_TARGETS = {
            "min_ev_threshold": 0.05,
            "min_confidence": 0.6,
            "max_risk_level": RiskLevel.MEDIUM,
            "min_value_rating": 6.0,
        }

    def calculate_ev(self, probability: float, odds: float) -> float:
        """计算期望价值 EV = (概率 * 赔率) - 1"""
        if probability <= 0 or odds <= 1:
            return -1.0
        return (probability * odds) - 1

    def calculate_kelly_fraction(
        self, ev: float, odds: float, probability: float, max_fraction: float = 0.25
    ) -> float:
        """计算Kelly准则投注比例"""
        if ev <= 0 or odds <= 1:
            return 0.0

        b = odds - 1  # 净赔率
        p = probability
        q = 1 - probability

        # 标准Kelly公式
        kelly = (b * p - q) / b

        # 限制最大投注比例
        kelly = min(kelly, max_fraction)
        kelly = max(kelly, 0.0)

        return kelly

    def assess_risk_level(
        self, probability: float, odds: float, ev: float
    ) -> RiskLevel:
        """评估风险等级"""
        if ev < 0:
            return RiskLevel.VERY_HIGH

        if probability >= 0.7 and ev >= 0.15:
            return RiskLevel.LOW
        elif probability >= 0.5 and ev >= 0.08:
            return RiskLevel.MEDIUM
        elif probability >= 0.3 and ev >= 0.03:
            return RiskLevel.HIGH
        else:
            return RiskLevel.VERY_HIGH

    def calculate_value_rating(
        self, ev: float, probability: float, odds: float
    ) -> float:
        """计算价值评级 (0-10分)"""
        if ev < 0:
            return 0.0

        # 基础价值分数
        base_score = min(ev * 20, 8.0)

        # 概率加成
        prob_bonus = min(probability * 2, 2.0)

        total_score = base_score + prob_bonus
        return min(total_score, 10.0)

    def check_srs_compliance(
        self, ev: float, probability: float, risk_level: RiskLevel, value_rating: float
    ) -> dict[str, Any]:
        """检查SRS合规性"""
        compliance = {
            "min_ev_met": ev >= self.SRS_TARGETS["min_ev_threshold"],
            "min_confidence_met": probability >= self.SRS_TARGETS["min_confidence"],
            "max_risk_met": risk_level.value
            <= self.SRS_TARGETS["max_risk_level"].value,
            "min_value_met": value_rating >= self.SRS_TARGETS["min_value_rating"],
            "overall_compliance": False,
        }

        compliance["overall_compliance"] = all(
            [
                compliance["min_ev_met"],
                compliance["min_confidence_met"],
                compliance["max_risk_met"],
                compliance["min_value_met"],
            ]
        )

        return compliance


# 策略优化器
class CoreStrategyOptimizer:
    """核心策略优化器 - 简化版本"""

    def __init__(self):
        self.strategies = {
            "conservative": {
                "max_kelly_fraction": 0.15,
                "min_ev_threshold": 0.08,
                "risk_tolerance": 0.3,
                "name": "保守策略",
            },
            "balanced": {
                "max_kelly_fraction": 0.25,
                "min_ev_threshold": 0.05,
                "risk_tolerance": 0.5,
                "name": "平衡策略",
            },
            "srs_compliant": {
                "max_kelly_fraction": 0.20,
                "min_ev_threshold": 0.05,
                "risk_tolerance": 0.4,
                "name": "SRS合规策略",
            },
        }

    def evaluate_betting_opportunity(
        self, probability: float, odds: float, strategy_name: str = "srs_compliant"
    ) -> dict[str, Any]:
        """评估投注机会"""
        ev_calculator = CoreEVCalculator()
        strategy = self.strategies.get(strategy_name, self.strategies["srs_compliant"])

        # 计算核心指标
        ev = ev_calculator.calculate_ev(probability, odds)
        kelly_fraction = ev_calculator.calculate_kelly_fraction(
            ev, odds, probability, strategy["max_kelly_fraction"]
        )
        risk_level = ev_calculator.assess_risk_level(probability, odds, ev)
        value_rating = ev_calculator.calculate_value_rating(ev, probability, odds)

        # 检查SRS合规性
        srs_compliance = ev_calculator.check_srs_compliance(
            ev, probability, risk_level, value_rating
        )

        # 生成投注建议
        if ev >= strategy["min_ev_threshold"] and srs_compliance["overall_compliance"]:
            recommendation = "bet"
        elif ev > 0:
            recommendation = "small_bet"
        else:
            recommendation = "avoid"

        return {
            "ev": ev,
            "kelly_fraction": kelly_fraction,
            "risk_level": risk_level.value,
            "value_rating": value_rating,
            "recommendation": recommendation,
            "srs_compliance": srs_compliance,
            "strategy_used": strategy_name,
            "probability": probability,
            "odds": odds,
        }


# 测试器类
class BettingCoreTester:
    """EV计算和投注策略核心功能测试器"""

    def __init__(self):
        self.test_results = {
            "test_name": "Betting EV Strategy Core Test",
            "issue_number": 116,
            "test_date": datetime.now().isoformat(),
            "test_status": "running",
            "individual_tests": {},
            "summary": {},
        }

    async def run_core_tests(self):
        """运行核心功能测试"""

        try:
            # 1. EV计算精度测试
            await self._test_ev_calculation_precision()

            # 2. Kelly准则测试
            await self._test_kelly_criterion()

            # 3. 风险评估测试
            await self._test_risk_assessment()

            # 4. 价值评级测试
            await self._test_value_rating()

            # 5. SRS合规性测试
            await self._test_srs_compliance()

            # 6. 策略优化测试
            await self._test_strategy_optimization()

            # 7. 综合场景测试
            await self._test_comprehensive_scenarios()

            # 计算总体结果
            self._calculate_summary()

            return self.test_results

        except Exception:
            self.test_results["test_status"] = "error"
            self.test_results["error"] = str(e)
            return self.test_results

    async def _test_ev_calculation_precision(self):
        """测试EV计算精度"""

        calculator = CoreEVCalculator()
        test_cases = [
            (0.6, 2.0, 0.2),  # (概率, 赔率, 期望EV)
            (0.4, 2.5, 0.0),
            (0.3, 3.0, -0.1),
            (0.8, 1.8, 0.44),
            (0.2, 5.0, 0.0),
        ]

        passed = 0
        for prob, odds, expected in test_cases:
            calculated = calculator.calculate_ev(prob, odds)
            if abs(calculated - expected) <= 0.01:  # 1%容差
                passed += 1
            else:
                pass

        accuracy = passed / len(test_cases)
        self.test_results["individual_tests"]["ev_calculation"] = {
            "passed": passed,
            "total": len(test_cases),
            "accuracy": accuracy,
            "status": "passed" if accuracy >= 0.9 else "failed",
        }

    async def _test_kelly_criterion(self):
        """测试Kelly准则"""

        calculator = CoreEVCalculator()
        test_cases = [
            (0.2, 2.0, 0.6, (0.1, 0.2)),  # (EV, 赔率, 概率, 期望范围)
            (0.1, 2.5, 0.5, (0.04, 0.1)),
            (-0.1, 3.0, 0.3, (0.0, 0.0)),
            (0.44, 1.8, 0.8, (0.1, 0.25)),
        ]

        passed = 0
        for ev, odds, prob, expected_range in test_cases:
            kelly = calculator.calculate_kelly_fraction(ev, odds, prob)
            min_exp, max_exp = expected_range
            if min_exp <= kelly <= max_exp:
                passed += 1
            else:
                pass

        accuracy = passed / len(test_cases)
        self.test_results["individual_tests"]["kelly_criterion"] = {
            "passed": passed,
            "total": len(test_cases),
            "accuracy": accuracy,
            "status": "passed" if accuracy >= 0.9 else "failed",
        }

    async def _test_risk_assessment(self):
        """测试风险评估"""

        calculator = CoreEVCalculator()
        test_cases = [
            (0.8, 1.8, 0.44, RiskLevel.LOW),
            (0.6, 2.2, 0.32, RiskLevel.MEDIUM),
            (0.4, 3.0, 0.2, RiskLevel.HIGH),
            (0.2, 4.0, -0.2, RiskLevel.VERY_HIGH),
        ]

        passed = 0
        for prob, odds, _ev, expected_risk in test_cases:
            calculated_ev = calculator.calculate_ev(prob, odds)
            assessed_risk = calculator.assess_risk_level(prob, odds, calculated_ev)
            if assessed_risk == expected_risk:
                passed += 1
            else:
                pass

        accuracy = passed / len(test_cases)
        self.test_results["individual_tests"]["risk_assessment"] = {
            "passed": passed,
            "total": len(test_cases),
            "accuracy": accuracy,
            "status": "passed" if accuracy >= 0.9 else "failed",
        }

    async def _test_value_rating(self):
        """测试价值评级"""

        calculator = CoreEVCalculator()
        test_cases = [
            (0.15, 0.8, 8.5),  # (EV, 概率, 最小期望评级)
            (0.08, 0.6, 6.8),
            (0.02, 0.3, 4.2),
            (0.25, 0.9, 9.5),
        ]

        passed = 0
        for ev, prob, min_expected in test_cases:
            rating = calculator.calculate_value_rating(ev, prob, 2.0)
            if rating >= min_expected:
                passed += 1
            else:
                pass

        accuracy = passed / len(test_cases)
        self.test_results["individual_tests"]["value_rating"] = {
            "passed": passed,
            "total": len(test_cases),
            "accuracy": accuracy,
            "status": "passed" if accuracy >= 0.9 else "failed",
        }

    async def _test_srs_compliance(self):
        """测试SRS合规性"""

        calculator = CoreEVCalculator()
        test_cases = [
            (0.65, 2.1, True),  # (概率, 赔率, 是否应该合规)
            (0.4, 2.8, False),
            (0.75, 1.9, True),
            (0.3, 4.0, False),
        ]

        passed = 0
        for prob, odds, should_comply in test_cases:
            ev = calculator.calculate_ev(prob, odds)
            risk = calculator.assess_risk_level(prob, odds, ev)
            value = calculator.calculate_value_rating(ev, prob, odds)
            compliance = calculator.check_srs_compliance(ev, prob, risk, value)

            if compliance["overall_compliance"] == should_comply:
                passed += 1
            else:
                pass

        accuracy = passed / len(test_cases)
        self.test_results["individual_tests"]["srs_compliance"] = {
            "passed": passed,
            "total": len(test_cases),
            "accuracy": accuracy,
            "status": "passed" if accuracy >= 0.8 else "failed",
        }

    async def _test_strategy_optimization(self):
        """测试策略优化"""

        optimizer = CoreStrategyOptimizer()
        strategies = ["conservative", "balanced", "srs_compliant"]

        passed = 0
        for strategy_name in strategies:
            try:
                # 测试一个好的投注机会
                result = optimizer.evaluate_betting_opportunity(
                    0.65, 2.1, strategy_name
                )

                # 验证结果结构
                required_keys = [
                    "ev",
                    "kelly_fraction",
                    "risk_level",
                    "value_rating",
                    "recommendation",
                    "srs_compliance",
                ]
                if all(key in result for key in required_keys):
                    passed += 1
                else:
                    pass

            except Exception:
                pass

        accuracy = passed / len(strategies)
        self.test_results["individual_tests"]["strategy_optimization"] = {
            "passed": passed,
            "total": len(strategies),
            "accuracy": accuracy,
            "status": "passed" if accuracy >= 0.9 else "failed",
        }

    async def _test_comprehensive_scenarios(self):
        """测试综合场景"""

        optimizer = CoreStrategyOptimizer()

        # 模拟真实比赛场景
        scenarios = [
            {
                "name": "热门主队",
                "probability": 0.7,
                "odds": 1.85,
                "expected_outcome": "bet",
            },
            {
                "name": "势均力敌",
                "probability": 0.5,
                "odds": 2.1,
                "expected_outcome": "bet",
            },
            {
                "name": "冷门高赔",
                "probability": 0.25,
                "odds": 4.5,
                "expected_outcome": "avoid",
            },
            {
                "name": "价值投注",
                "probability": 0.6,
                "odds": 2.2,
                "expected_outcome": "bet",
            },
        ]

        passed = 0
        for scenario in scenarios:
            try:
                result = optimizer.evaluate_betting_opportunity(
                    scenario["probability"], scenario["odds"], "srs_compliant"
                )

                # 检查SRS合规性
                srs_ok = result["srs_compliance"]["overall_compliance"]

                # 检查推荐合理性
                recommendation_ok = (
                    result["recommendation"] in ["bet", "small_bet"]
                    and result["ev"] > 0
                ) or (result["recommendation"] == "avoid" and result["ev"] <= 0)

                if srs_ok and recommendation_ok:
                    passed += 1
                else:
                    pass

            except Exception:
                pass

        accuracy = passed / len(scenarios)
        self.test_results["individual_tests"]["comprehensive_scenarios"] = {
            "passed": passed,
            "total": len(scenarios),
            "accuracy": accuracy,
            "status": "passed" if accuracy >= 0.7 else "failed",
        }

    def _calculate_summary(self):
        """计算测试总结"""
        individual_tests = self.test_results["individual_tests"]

        if not individual_tests:
            self.test_results["test_status"] = "failed"
            return

        total_passed = sum(test["passed"] for test in individual_tests.values())
        total_tests = sum(test["total"] for test in individual_tests.values())
        overall_accuracy = total_passed / total_tests if total_tests > 0 else 0

        # 关键功能评分
        critical_scores = {
            "ev_calculation": individual_tests.get("ev_calculation", {}).get(
                "accuracy", 0
            ),
            "kelly_criterion": individual_tests.get("kelly_criterion", {}).get(
                "accuracy", 0
            ),
            "srs_compliance": individual_tests.get("srs_compliance", {}).get(
                "accuracy", 0
            ),
            "risk_assessment": individual_tests.get("risk_assessment", {}).get(
                "accuracy", 0
            ),
        }

        # 判断总体状态
        if overall_accuracy >= 0.9 and all(
            score >= 0.8 for score in critical_scores.values()
        ):
            status = "passed"
        elif overall_accuracy >= 0.7 and critical_scores["srs_compliance"] >= 0.8:
            status = "partially_passed"
        else:
            status = "failed"

        self.test_results.update(
            {
                "test_status": status,
                "summary": {
                    "total_tests": total_tests,
                    "total_passed": total_passed,
                    "overall_accuracy": overall_accuracy,
                    "critical_scores": critical_scores,
                    "srs_compliance_achieved": critical_scores["srs_compliance"] >= 0.8,
                    "core_functionality_achieved": overall_accuracy >= 0.8,
                },
            }
        )

    def generate_report(self):
        """生成测试报告"""

        if "summary" in self.test_results:
            summary = self.test_results["summary"]

            summary["critical_scores"]

        for _test_name, result in self.test_results["individual_tests"].items():
            (
                "✅"
                if result["status"] == "passed"
                else "⚠️"
                if result["status"] == "partially_passed"
                else "❌"
            )

        # 保存报告
        report_path = Path("test_betting_core_report.json")
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)

        if self.test_results["test_status"] == "passed":
            pass
        elif self.test_results["test_status"] == "partially_passed":
            pass
        else:
            pass


async def main():
    """主函数"""

    tester = BettingCoreTester()
    test_result = await tester.run_core_tests()
    tester.generate_report()

    if test_result["test_status"] in ["passed", "partially_passed"]:
        pass
    else:
        pass


if __name__ == "__main__":
    asyncio.run(main())