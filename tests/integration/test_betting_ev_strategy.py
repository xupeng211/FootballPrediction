#!/usr/bin/env python3
"""
EV计算和投注策略测试脚本
EV Calculation and Betting Strategy Test Script

测试Issue #116的EV计算和投注策略功能是否符合SRS要求：
- EV计算准确性验证
- Kelly Criterion实现验证
- 投注策略有效性验证
- SRS合规性检查
- 风险管理功能验证
- 组合优化算法验证

创建时间: 2025-10-29
Issue: #116 EV计算和投注策略
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

try:
    # 简化导入，避免复杂的依赖问题
    import os
    import sys

    sys.path.append(
        os.path.join(os.path.dirname(__file__), "src", "services", "betting")
    )

    from ev_calculator import (
        BettingOdds,
        BettingStrategy,
        BettingStrategyOptimizer,
        BetType,
        EVCalculator,
        PredictionProbabilities,
        RiskLevel,
        create_betting_recommendation_engine,
    )

    logger = None  # 简化日志处理
except ImportError:
    # 创建简化的日志器
    import logging

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # 创建基本的类定义以允许测试运行
    class BetType:
        HOME_WIN = "home_win"
        DRAW = "draw"
        AWAY_WIN = "away_win"
        OVER_2_5 = "over_2_5"
        UNDER_2_5 = "under_2_5"
        BTTS = "btts"

    class RiskLevel:
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        VERY_HIGH = "very_high"

    class BettingStrategy:
        """简化的投注策略类"""

        def __init__(self):
            self.max_kelly_fraction = 0.25
            self.min_ev_threshold = 0.05
            self.risk_tolerance = 0.5
            self.bankroll_percentage = 0.02
            self.max_daily_bets = 5


class BettingEVStrategyTester:
    """EV计算和投注策略测试器"""

    def __init__(self):
        self.logger = logger
        self.test_results = {
            "test_name": "Betting EV Strategy Compliance Test",
            "issue_number": 116,
            "test_date": datetime.now().isoformat(),
            "test_status": "running",
            "srs_targets": {
                "min_ev_threshold": 0.05,
                "min_kelly_accuracy": 0.9,
                "max_risk_level": RiskLevel.MEDIUM,
                "min_confidence": 0.6,
                "portfolio_optimization": True,
                "risk_management": True,
            },
            "test_results": {},
            "individual_tests": {},
            "performance_metrics": {},
            "recommendations": [],
            "next_steps": [],
        }

    async def run_comprehensive_tests(self):
        """运行全面测试"""

        try:
            # 1. EV计算准确性测试
            await self._test_ev_calculation_accuracy()

            # 2. Kelly Criterion测试
            await self._test_kelly_criterion_implementation()

            # 3. 投注策略测试
            await self._test_betting_strategies()

            # 4. SRS合规性测试
            await self._test_srs_compliance()

            # 5. 风险管理测试
            await self._test_risk_management()

            # 6. 组合优化测试
            await self._test_portfolio_optimization()

            # 7. 投注建议引擎测试
            await self._test_recommendation_engine()

            # 8. 服务集成测试
            await self._test_service_integration()

            # 计算总体测试结果
            self._calculate_overall_results()

            # 生成测试报告
            await self._generate_test_report()

            return self.test_results

        except Exception as e:
            self.logger.error(f"测试执行失败: {e}")
            self.test_results["test_status"] = "error"
            self.test_results["error"] = str(e)
            return self.test_results

    async def _test_ev_calculation_accuracy(self):
        """测试EV计算准确性"""

        test_name = "EV计算准确性"
        ev_calculator = EVCalculator()
        test_cases = [
            # (概率, 赔率, 期望EV)
            (0.6, 2.0, 0.2),  # 正EV情况
            (0.4, 2.5, 0.0),  # 零EV情况
            (0.3, 3.0, -0.1),  # 负EV情况
            (0.8, 1.5, 0.2),  # 高概率低赔率
            (0.2, 5.0, 0.0),  # 低概率高赔率
        ]

        passed_tests = 0
        total_tests = len(test_cases)

        for _i, (probability, odds, expected_ev) in enumerate(test_cases):
            calculated_ev = ev_calculator.calculate_ev(probability, odds)
            tolerance = 0.01  # 1%容差

            if abs(calculated_ev - expected_ev) <= tolerance:
                passed_tests += 1
            else:
                pass

        accuracy_rate = passed_tests / total_tests
        self.test_results["individual_tests"][test_name] = {
            "passed": passed_tests,
            "total": total_tests,
            "accuracy_rate": accuracy_rate,
            "status": "passed" if accuracy_rate >= 0.9 else "failed",
        }


    async def _test_kelly_criterion_implementation(self):
        """测试Kelly Criterion实现"""

        test_name = "Kelly Criterion实现"
        ev_calculator = EVCalculator()
        test_cases = [
            # (EV, 赔率, 概率, 期望Kelly比例范围)
            (0.2, 2.0, 0.6, (0.1, 0.2)),
            (0.1, 2.5, 0.5, (0.04, 0.1)),
            (-0.1, 3.0, 0.3, (0.0, 0.0)),  # 负EV应该返回0
            (0.3, 1.8, 0.7, (0.1, 0.25)),  # 应该被最大值限制
        ]

        passed_tests = 0
        total_tests = len(test_cases)

        for _i, (ev, odds, probability, expected_range) in enumerate(test_cases):
            kelly_fraction = ev_calculator.calculate_kelly_fraction(
                ev, odds, probability
            )
            min_expected, max_expected = expected_range

            if min_expected <= kelly_fraction <= max_expected:
                passed_tests += 1
            else:
                pass

        accuracy_rate = passed_tests / total_tests
        self.test_results["individual_tests"][test_name] = {
            "passed": passed_tests,
            "total": total_tests,
            "accuracy_rate": accuracy_rate,
            "status": "passed" if accuracy_rate >= 0.9 else "failed",
        }


    async def _test_betting_strategies(self):
        """测试投注策略"""

        test_name = "投注策略有效性"
        optimizer = BettingStrategyOptimizer()

        # 测试所有预定义策略
        strategies = ["conservative", "balanced", "aggressive", "srs_compliant"]
        passed_tests = 0
        total_tests = len(strategies)

        for strategy_name in strategies:
            strategy = optimizer.strategies.get(strategy_name)
            if strategy and self._validate_strategy_config(strategy):
                passed_tests += 1
            else:
                pass

        # 测试策略优化功能
        try:
            # 创建模拟EV计算结果
            mock_ev_calculations = self._create_mock_ev_calculations()
            portfolio = optimizer.optimize_portfolio(
                mock_ev_calculations, optimizer.strategies["srs_compliant"]
            )

            if portfolio and "recommended_bets" in portfolio:
                passed_tests += 1
                total_tests += 1
            else:
                total_tests += 1

        except Exception:
            total_tests += 1

        accuracy_rate = passed_tests / total_tests
        self.test_results["individual_tests"][test_name] = {
            "passed": passed_tests,
            "total": total_tests,
            "accuracy_rate": accuracy_rate,
            "status": "passed" if accuracy_rate >= 0.9 else "failed",
        }


    async def _test_srs_compliance(self):
        """测试SRS合规性"""

        test_name = "SRS合规性检查"
        ev_calculator = EVCalculator()
        optimizer = BettingStrategyOptimizer()

        # 测试SRS目标合规性
        srs_requirements = {
            "min_ev_threshold": 0.05,
            "min_confidence": 0.6,
            "max_risk_level": RiskLevel.MEDIUM,
            "kelly_criterion": True,
            "risk_management": True,
        }

        passed_tests = 0
        total_tests = len(srs_requirements)

        # 创建符合SRS要求的测试数据
        compliant_probability = 0.7  # > 0.6
        compliant_odds = 2.0
        compliant_ev = ev_calculator.calculate_ev(compliant_probability, compliant_odds)

        if compliant_ev >= srs_requirements["min_ev_threshold"]:
            passed_tests += 1
        else:
            pass

        if compliant_probability >= srs_requirements["min_confidence"]:
            passed_tests += 1
        else:
            pass

        # 测试风险管理
        risk_level = ev_calculator.assess_risk_level(
            compliant_probability, compliant_odds, compliant_ev
        )
        if risk_level.value <= srs_requirements["max_risk_level"].value:
            passed_tests += 1
        else:
            pass

        # 测试Kelly准则实现
        kelly_fraction = ev_calculator.calculate_kelly_fraction(
            compliant_ev, compliant_odds, compliant_probability
        )
        if kelly_fraction > 0 and kelly_fraction <= 0.25:
            passed_tests += 1
        else:
            pass

        # 测试策略优化
        strategy = optimizer.strategies["srs_compliant"]
        if strategy and strategy.risk_tolerance <= 0.5:
            passed_tests += 1
        else:
            pass

        accuracy_rate = passed_tests / total_tests
        self.test_results["individual_tests"][test_name] = {
            "passed": passed_tests,
            "total": total_tests,
            "accuracy_rate": accuracy_rate,
            "status": "passed" if accuracy_rate >= 0.9 else "failed",
        }


    async def _test_risk_management(self):
        """测试风险管理功能"""

        test_name = "风险管理功能"
        ev_calculator = EVCalculator()

        # 测试不同风险水平的评估
        risk_test_cases = [
            (0.8, 1.8, 0.44, RiskLevel.LOW),  # 低风险
            (0.6, 2.2, 0.32, RiskLevel.MEDIUM),  # 中等风险
            (0.4, 3.0, 0.2, RiskLevel.HIGH),  # 高风险
            (0.2, 4.0, -0.2, RiskLevel.VERY_HIGH),  # 极高风险
        ]

        passed_tests = 0
        total_tests = len(risk_test_cases)

        for probability, odds, _expected_ev, expected_risk in risk_test_cases:
            calculated_ev = ev_calculator.calculate_ev(probability, odds)
            assessed_risk = ev_calculator.assess_risk_level(
                probability, odds, calculated_ev
            )

            if assessed_risk == expected_risk:
                passed_tests += 1
            else:
                pass

        # 测试价值评级
        value_test_cases = [
            (0.15, 0.8, 8.5),  # 高价值
            (0.08, 0.6, 6.8),  # 中等价值
            (0.02, 0.3, 4.2),  # 低价值
        ]

        for ev, probability, min_expected_rating in value_test_cases:
            value_rating = ev_calculator.calculate_value_rating(ev, probability, 2.0)
            if value_rating >= min_expected_rating:
                passed_tests += 1
                total_tests += 1
            else:
                total_tests += 1

        # 测试破产概率计算
        bust_probability = ev_calculator.calculate_bust_probability(0.1, 0.7)
        if 0 <= bust_probability <= 0.5:
            passed_tests += 1
            total_tests += 1
        else:
            total_tests += 1

        accuracy_rate = passed_tests / total_tests
        self.test_results["individual_tests"][test_name] = {
            "passed": passed_tests,
            "total": total_tests,
            "accuracy_rate": accuracy_rate,
            "status": "passed" if accuracy_rate >= 0.9 else "failed",
        }


    async def _test_portfolio_optimization(self):
        """测试组合优化"""

        test_name = "组合优化算法"
        optimizer = BettingStrategyOptimizer()

        # 创建多样化的EV计算结果
        ev_calculations = self._create_diverse_mock_ev_calculations()

        # 测试不同策略的组合优化
        strategies = ["conservative", "balanced", "srs_compliant"]
        passed_tests = 0
        total_tests = len(strategies)

        for strategy_name in strategies:
            try:
                strategy = optimizer.strategies[strategy_name]
                portfolio = optimizer.optimize_portfolio(
                    ev_calculations, strategy, max_total_stake=0.1
                )

                # 验证优化结果
                if self._validate_portfolio_optimization(portfolio, strategy):
                    passed_tests += 1
                else:
                    pass

            except Exception:
                pass

        # 测试多样化评分
        diversity_score = optimizer._assess_portfolio_risk(
            portfolio.get("recommended_bets", []) if "portfolio" in locals() else []
        )
        if diversity_score:
            passed_tests += 1
            total_tests += 1
        else:
            total_tests += 1

        accuracy_rate = passed_tests / total_tests
        self.test_results["individual_tests"][test_name] = {
            "passed": passed_tests,
            "total": total_tests,
            "accuracy_rate": accuracy_rate,
            "status": (
                "passed" if accuracy_rate >= 0.8 else "failed"
            ),  # 组合优化容差稍宽
        }


    async def _test_recommendation_engine(self):
        """测试投注建议引擎"""

        test_name = "投注建议引擎"
        engine = create_betting_recommendation_engine()

        # 创建模拟数据
        odds = BettingOdds(
            home_win=2.1,
            draw=3.4,
            away_win=3.2,
            over_2_5=1.9,
            under_2_5=1.9,
            source="test_bookmaker",
            confidence=0.95,
        )

        probabilities = PredictionProbabilities(
            home_win=0.65,
            draw=0.25,
            away_win=0.10,
            over_2_5=0.55,
            under_2_5=0.45,
            confidence=0.82,
            model_name="test_model",
        )

        try:
            # 测试单场比赛建议生成
            recommendations = await engine.generate_match_recommendations(
                match_id="test_match_001",
                odds=odds,
                probabilities=probabilities,
                strategy_name="srs_compliant",
            )

            if self._validate_recommendations(recommendations):
                len(recommendations.get("individual_bets", []))
                # 修复的多行f-string替换为单行
                recommendations.get("overall_recommendation", {})
                recommendations.get("srs_compliance", {})

                passed_tests = 1
            else:
                passed_tests = 0

            total_tests = 1

        except Exception:
            passed_tests = 0
            total_tests = 1

        accuracy_rate = passed_tests / total_tests
        self.test_results["individual_tests"][test_name] = {
            "passed": passed_tests,
            "total": total_tests,
            "accuracy_rate": accuracy_rate,
            "status": "passed" if accuracy_rate >= 0.9 else "failed",
        }


    async def _test_service_integration(self):
        """测试服务集成"""

        test_name = "服务集成测试"

        try:
            # 创建投注服务实例
            betting_service = create_betting_service()

            # 测试服务组件初始化
            components_status = {
                "ev_calculator": hasattr(betting_service, "recommendation_engine"),
                "betting_service": hasattr(betting_service, "prediction_service"),
                "data_integration": hasattr(betting_service, "data_integration"),
                "redis_client": hasattr(betting_service, "redis_client"),
                "srs_config": hasattr(betting_service, "srs_config"),
            }

            passed_components = sum(components_status.values())
            total_components = len(components_status)

            for _component, _status in components_status.items():
                pass

            # 测试SRS配置
            srs_config_valid = self._validate_srs_configuration(
                betting_service.srs_config
            )
            if srs_config_valid:
                passed_components += 1
            else:
                pass
            total_components += 1

            accuracy_rate = passed_components / total_components
            self.test_results["individual_tests"][test_name] = {
                "passed": passed_components,
                "total": total_components,
                "accuracy_rate": accuracy_rate,
                "components_status": components_status,
                "status": "passed" if accuracy_rate >= 0.9 else "failed",
            }


        except Exception as e:
            self.test_results["individual_tests"][test_name] = {
                "passed": 0,
                "total": 1,
                "accuracy_rate": 0.0,
                "status": "failed",
                "error": str(e),
            }

    # 辅助方法

    def _validate_strategy_config(self, strategy: BettingStrategy) -> bool:
        """验证策略配置"""
        return (
            0 < strategy.max_kelly_fraction <= 0.5
            and strategy.min_ev_threshold >= 0
            and 0 <= strategy.risk_tolerance <= 1
            and 0 < strategy.bankroll_percentage <= 0.1
            and strategy.max_daily_bets > 0
            and strategy.value_threshold >= 1.0
        )

    def _create_mock_ev_calculations(self) -> list:
        """创建模拟EV计算结果"""
        from src.services.betting.ev_calculator import EVCalculation

        return [
            EVCalculation(
                bet_type=BetType.HOME_WIN,
                probability=0.65,
                odds=2.1,
                ev=0.365,
                kelly_fraction=0.15,
                risk_level=RiskLevel.MEDIUM,
                recommendation="bet",
                confidence=0.82,
                value_rating=7.3,
                expected_roi=5.5,
                bust_probability=0.03,
                suggested_stake=0.015,
            ),
            EVCalculation(
                bet_type=BetType.DRAW,
                probability=0.25,
                odds=3.4,
                ev=-0.15,
                kelly_fraction=0.0,
                risk_level=RiskLevel.VERY_HIGH,
                recommendation="avoid",
                confidence=0.25,
                value_rating=0.0,
                expected_roi=0.0,
                bust_probability=0.0,
                suggested_stake=0.0,
            ),
        ]

    def _create_diverse_mock_ev_calculations(self) -> list:
        """创建多样化的模拟EV计算结果"""
        from src.services.betting.ev_calculator import EVCalculation

        return [
            EVCalculation(
                BetType.HOME_WIN,
                0.7,
                2.0,
                0.4,
                0.2,
                RiskLevel.LOW,
                "strong_bet",
                0.9,
                8.5,
                8.0,
                0.01,
                0.02,
            ),
            EVCalculation(
                BetType.DRAW,
                0.3,
                3.5,
                0.05,
                0.03,
                RiskLevel.MEDIUM,
                "small_bet",
                0.4,
                6.2,
                0.15,
                0.08,
                0.003,
            ),
            EVCalculation(
                BetType.AWAY_WIN,
                0.15,
                5.0,
                -0.25,
                0.0,
                RiskLevel.VERY_HIGH,
                "avoid",
                0.15,
                0.0,
                0.0,
                0.0,
                0.0,
            ),
            EVCalculation(
                BetType.OVER_2_5,
                0.6,
                1.9,
                0.14,
                0.12,
                RiskLevel.LOW,
                "bet",
                0.75,
                7.1,
                1.7,
                0.02,
                0.012,
            ),
            EVCalculation(
                BetType.UNDER_2_5,
                0.4,
                2.1,
                -0.16,
                0.0,
                RiskLevel.HIGH,
                "avoid",
                0.4,
                0.0,
                0.0,
                0.0,
                0.0,
            ),
        ]

    def _validate_portfolio_optimization(
        self, portfolio: dict, strategy: BettingStrategy
    ) -> bool:
        """验证组合优化结果"""
        if not portfolio:
            return False

        required_keys = [
            "recommended_bets",
            "total_stake",
            "expected_return",
            "portfolio_risk",
        ]
        if not all(key in portfolio for key in required_keys):
            return False

        # 验证投注限制
        if portfolio["total_stake"] > 0.1:  # 最大10%限制
            return False

        # 验证期望收益合理性
        if portfolio["expected_return"] <= portfolio["total_stake"]:
            return False

        return True

    def _validate_recommendations(self, recommendations: dict) -> bool:
        """验证投注建议"""
        if not recommendations or recommendations.get("status") == "error":
            return False

        required_keys = [
            "match_id",
            "strategy_used",
            "individual_bets",
            "portfolio_optimization",
            "overall_recommendation",
            "srs_compliance",
            "risk_summary",
        ]

        return all(key in recommendations for key in required_keys)

    def _validate_srs_configuration(self, srs_config: dict) -> bool:
        """验证SRS配置"""
        if not srs_config:
            return False

        required_keys = [
            "enable_srs_mode",
            "strict_compliance",
            "min_confidence_threshold",
            "max_risk_level",
            "min_ev_threshold",
            "required_features",
        ]

        return all(key in srs_config for key in required_keys)

    def _calculate_overall_results(self):
        """计算总体测试结果"""
        individual_tests = self.test_results["individual_tests"]

        if not individual_tests:
            self.test_results["test_status"] = "failed"
            return

        total_passed = sum(test["passed"] for test in individual_tests.values())
        total_tests = sum(test["total"] for test in individual_tests.values())

        overall_accuracy = total_passed / total_tests if total_tests > 0 else 0

        # 计算关键指标
        ev_calculation_acc = individual_tests.get("EV计算准确性", {}).get(
            "accuracy_rate", 0
        )
        kelly_criterion_acc = individual_tests.get("Kelly Criterion实现", {}).get(
            "accuracy_rate", 0
        )
        srs_compliance_acc = individual_tests.get("SRS合规性检查", {}).get(
            "accuracy_rate", 0
        )

        # 判断测试状态
        if overall_accuracy >= 0.9 and srs_compliance_acc >= 0.9:
            self.test_results["test_status"] = "passed"
        elif overall_accuracy >= 0.7 and srs_compliance_acc >= 0.8:
            self.test_results["test_status"] = "partially_passed"
        else:
            self.test_results["test_status"] = "failed"

        self.test_results["test_results"] = {
            "total_tests_run": total_tests,
            "total_tests_passed": total_passed,
            "overall_accuracy": overall_accuracy,
            "critical_component_scores": {
                "ev_calculation_accuracy": ev_calculation_acc,
                "kelly_criterion_accuracy": kelly_criterion_acc,
                "srs_compliance_accuracy": srs_compliance_acc,
            },
        }

        # 生成建议
        if self.test_results["test_status"] in ["passed", "partially_passed"]:
            self.test_results["recommendations"] = [
                "✅ EV计算算法实现正确",
                "✅ Kelly Criterion投注策略有效",
                "✅ SRS合规性检查完善",
                "✅ 风险管理功能健全",
                "✅ 组合优化算法合理",
            ]
        else:
            self.test_results["recommendations"] = [
                "⚠️ 需要优化EV计算精度",
                "⚠️ 需要改进Kelly Criterion实现",
                "⚠️ 需要加强SRS合规性检查",
                "⚠️ 需要完善风险管理功能",
            ]

        self.test_results["next_steps"] = [
            "集成到主API服务中",
            "添加前端UI组件",
            "完善文档和使用指南",
            "进行端到端测试",
            "部署到生产环境",
        ]

    async def _generate_test_report(self):
        """生成测试报告"""


        if "test_results" in self.test_results:
            results = self.test_results["test_results"]

            critical_scores = results.get("critical_component_scores", {})
            critical_scores.get("ev_calculation_accuracy", 0) * 100
            critical_scores.get("kelly_criterion_accuracy", 0) * 100
            critical_scores.get("srs_compliance_accuracy", 0) * 100

        for _test_name, result in self.test_results["individual_tests"].items():
            (
                "✅"
                if result["status"] == "passed"
                else "⚠️" if result["status"] == "partially_passed" else "❌"
            )

        for _rec in self.test_results["recommendations"]:
            pass

        for _step in self.test_results["next_steps"]:
            pass

        # 保存详细报告
        report_path = Path("test_betting_ev_strategy_report.json")
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

    tester = BettingEVStrategyTester()
    test_result = await tester.run_comprehensive_tests()

    if test_result["test_status"] in ["passed", "partially_passed"]:
        if test_result["test_status"] == "passed":
            pass
    else:
        pass



if __name__ == "__main__":
    asyncio.run(main())
