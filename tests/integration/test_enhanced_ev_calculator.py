#!/usr/bin/env python3
"""
增强EV计算器测试和验证脚本
Issue #121: EV计算算法参数调优

测试内容：
1. Kelly Criterion优化效果验证
2. 价值评级算法改进验证
3. 回测性能对比
4. 风险管理效果评估
"""

import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Any

# 添加项目根目录到Python路径
sys.path.append(str(Path(__file__).parent))

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/enhanced_ev_test.log", encoding="utf-8"),
    ],
)

logger = logging.getLogger(__name__)


def create_test_data() -> list[dict[str, Any]]:
    """创建测试数据"""

    # 模拟历史投注数据
    historical_bets = [
        {
            "bet_type": "home_win",
            "probability": 0.65,
            "odds": 1.85,
            "confidence": 0.8,
            "outcome": True,  # 赢了
            "historical_data": {
                "accuracy": 0.68,
                "roi": 0.12,
                "consistency": 0.75,
                "max_drawdown": 0.08,
            },
            "market_data": {
                "market_odds": 1.87,
                "liquidity_score": 0.8,
                "spread_percentage": 0.02,
            },
        },
        {
            "bet_type": "draw",
            "probability": 0.25,
            "odds": 3.40,
            "confidence": 0.6,
            "outcome": False,  # 输了
            "historical_data": {
                "accuracy": 0.62,
                "roi": -0.05,
                "consistency": 0.70,
                "max_drawdown": 0.12,
            },
        },
        {
            "bet_type": "away_win",
            "probability": 0.45,
            "odds": 2.60,
            "confidence": 0.7,
            "outcome": True,  # 赢了
            "historical_data": {
                "accuracy": 0.70,
                "roi": 0.08,
                "consistency": 0.80,
                "max_drawdown": 0.06,
            },
        },
        {
            "bet_type": "over_2_5",
            "probability": 0.55,
            "odds": 1.95,
            "confidence": 0.75,
            "outcome": True,  # 赢了
            "historical_data": {
                "accuracy": 0.72,
                "roi": 0.15,
                "consistency": 0.78,
                "max_drawdown": 0.05,
            },
        },
        {
            "bet_type": "home_win",
            "probability": 0.35,
            "odds": 2.80,
            "confidence": 0.5,
            "outcome": False,  # 输了
            "historical_data": {
                "accuracy": 0.55,
                "roi": -0.12,
                "consistency": 0.60,
                "max_drawdown": 0.18,
            },
        },
        {
            "bet_type": "btts",
            "probability": 0.60,
            "odds": 1.75,
            "confidence": 0.8,
            "outcome": True,  # 赢了
            "historical_data": {
                "accuracy": 0.75,
                "roi": 0.18,
                "consistency": 0.82,
                "max_drawdown": 0.04,
            },
        },
    ]

    # 扩展数据以获得更可靠的回测结果
    extended_bets = []
    for i in range(10):  # 创建10轮数据
        for bet in historical_bets:
            new_bet = bet.copy()
            # 添加一些随机变化
            new_bet["probability"] = max(
                0.1, min(0.9, bet["probability"] + (i % 3 - 1) * 0.05)
            )
            new_bet["odds"] = max(1.1, bet["odds"] + (i % 3 - 1) * 0.1)
            new_bet["confidence"] = max(
                0.3, min(1.0, bet["confidence"] + (i % 2 - 0.5) * 0.1)
            )
            # 随机化结果但保持一定胜率
            if bet["outcome"] and i < 7:  # 前几轮保持原结果
                new_bet["outcome"] = True
            elif not bet["outcome"] and i > 2:  # 后几轮可能反转
                new_bet["outcome"] = i % 3 == 0

            extended_bets.append(new_bet)

    return extended_bets


def test_kelly_optimization():
    """测试Kelly准则优化"""

    logger.info("🔧 测试Kelly准则优化...")

    try:
        from src.services.betting.enhanced_ev_calculator import EnhancedKellyCalculator

        kelly_calc = EnhancedKellyCalculator()

        # 测试案例
        test_cases = [
            {
                "prob": 0.6,
                "odds": 1.9,
                "confidence": 0.8,
                "description": "高概率低赔率",
            },
            {
                "prob": 0.35,
                "odds": 3.2,
                "confidence": 0.6,
                "description": "低概率高赔率",
            },
            {"prob": 0.5, "odds": 2.1, "confidence": 0.7, "description": "平衡投注"},
            {"prob": 0.8, "odds": 1.3, "confidence": 0.9, "description": "极高概率"},
        ]

        results = []
        for case in test_cases:
            result = kelly_calc.calculate_fractional_kelly(
                case["prob"], case["odds"], case["confidence"]
            )

            results.append(
                {
                    "case": case["description"],
                    "probability": case["prob"],
                    "odds": case["odds"],
                    "optimal_fraction": result.optimal_fraction,
                    "expected_growth": result.expected_growth,
                    "risk_of_ruin": result.risk_of_ruin,
                    "recommendation": result.recommended_adjustment,
                }
            )

            logger.info(
                f"  {case['description']}: Kelly={result.optimal_fraction:.3f}, "
                f"期望增长={result.expected_growth:.3f}, "
                f"破产风险={result.risk_of_ruin:.3f}"
            )

        return {"status": "success", "results": results}

    except Exception as e:
        logger.error(f"Kelly准则优化测试失败: {e}")
        return {"status": "error", "message": str(e)}


def test_value_rating_enhancement():
    """测试价值评级增强"""

    logger.info("📊 测试价值评级增强...")

    try:
        from src.services.betting.enhanced_ev_calculator import (
            EnhancedValueRatingCalculator,
        )

        value_calc = EnhancedValueRatingCalculator()

        # 测试案例
        test_cases = [
            {"prob": 0.65, "odds": 1.85, "confidence": 0.8, "description": "优质投注"},
            {
                "prob": 0.25,
                "odds": 4.50,
                "confidence": 0.5,
                "description": "高风险投注",
            },
            {"prob": 0.5, "odds": 2.05, "confidence": 0.7, "description": "公平投注"},
            {
                "prob": 0.8,
                "odds": 1.25,
                "confidence": 0.9,
                "description": "高确定性投注",
            },
        ]

        results = []
        for case in test_cases:
            result = value_calc.calculate_enhanced_value_rating(
                case["prob"], case["odds"], case["confidence"]
            )

            results.append(
                {
                    "case": case["description"],
                    "overall_rating": result.overall_rating,
                    "ev_score": result.ev_score,
                    "probability_score": result.probability_score,
                    "odds_fairness_score": result.odds_fairness_score,
                    "risk_adjusted_score": result.risk_adjusted_score,
                }
            )

            logger.info(
                f"  {case['description']}: 总评级={result.overall_rating:.1f}, "
                f"EV分数={result.ev_score:.1f}, "
                f"风险调整={result.risk_adjusted_score:.1f}"
            )

        return {"status": "success", "results": results}

    except Exception as e:
        logger.error(f"价值评级增强测试失败: {e}")
        return {"status": "error", "message": str(e)}


async def test_enhanced_ev_calculation():
    """测试增强EV计算"""

    logger.info("💰 测试增强EV计算...")

    try:
        from src.services.betting.enhanced_ev_calculator import (
            BetType,
            EnhancedEVCalculator,
        )

        ev_calc = EnhancedEVCalculator()

        # 测试案例
        test_cases = [
            {
                "bet_type": "home_win",
                "prob": 0.65,
                "odds": 1.85,
                "confidence": 0.8,
                "strategy": "srs_premium",
                "description": "SRS策略测试",
            },
            {
                "bet_type": "away_win",
                "prob": 0.35,
                "odds": 3.20,
                "confidence": 0.6,
                "strategy": "conservative_optimized",
                "description": "保守策略测试",
            },
            {
                "bet_type": "draw",
                "prob": 0.30,
                "odds": 3.40,
                "confidence": 0.7,
                "strategy": "aggressive_smart",
                "description": "激进策略测试",
            },
        ]

        results = []
        for case in test_cases:
            result = ev_calc.calculate_enhanced_ev(
                bet_type=BetType(case["bet_type"]),
                probability=case["prob"],
                odds=case["odds"],
                confidence=case["confidence"],
                strategy_name=case["strategy"],
            )

            results.append(
                {
                    "case": case["description"],
                    "strategy": case["strategy"],
                    "ev": result.ev,
                    "kelly_fraction": result.kelly_fraction,
                    "value_rating": result.value_rating,
                    "recommendation": result.recommendation,
                    "expected_roi": result.expected_roi,
                    "risk_level": result.risk_level.value,
                }
            )

            logger.info(
                f"  {case['description']} ({case['strategy']}): "
                f"EV={result.ev:.3f}, Kelly={result.kelly_fraction:.3f}, "
                f"评级={result.value_rating:.1f}, 建议={result.recommendation}"
            )

        return {"status": "success", "results": results}

    except Exception as e:
        logger.error(f"增强EV计算测试失败: {e}")
        return {"status": "error", "message": str(e)}


async def test_strategy_backtesting():
    """测试策略回测"""

    logger.info("📈 测试策略回测...")

    try:
        from src.services.betting.enhanced_ev_calculator import EnhancedEVCalculator

        ev_calc = EnhancedEVCalculator()
        test_bets = create_test_data()

        # 测试不同策略
        strategies = ["conservative_optimized", "balanced_enhanced", "srs_premium"]
        backtest_results = {}

        for strategy in strategies:
            logger.info(f"  回测策略: {strategy}")

            result = await ev_calc.backtest_strategy(strategy, test_bets, 1000.0)

            backtest_results[strategy] = {
                "final_bankroll": result["final_bankroll"],
                "roi": result["roi"],
                "win_rate": result["win_rate"],
                "max_drawdown": result["max_drawdown"],
                "sharpe_ratio": result["sharpe_ratio"],
                "total_bets": result["total_bets"],
                "winning_bets": result["winning_bets"],
            }

            logger.info(
                f"    ROI: {result['roi']:.2f}%, "
                f"胜率: {result['win_rate']:.2f}, "
                f"最大回撤: {result['max_drawdown']:.2f}, "
                f"Sharpe: {result['sharpe_ratio']:.3f}"
            )

        return {"status": "success", "results": backtest_results}

    except Exception as e:
        logger.error(f"策略回测测试失败: {e}")
        return {"status": "error", "message": str(e)}


def compare_with_original():
    """与原始EV计算器对比"""

    logger.info("🔄 与原始EV计算器对比...")

    try:
        from src.services.betting.enhanced_ev_calculator import (
            BetType,
            EnhancedEVCalculator,
        )
        from src.services.betting.ev_calculator import (
            EVCalculator as OriginalEVCalculator,
        )

        original_calc = OriginalEVCalculator()
        enhanced_calc = EnhancedEVCalculator()

        # 测试案例
        test_cases = [
            {"prob": 0.65, "odds": 1.85, "confidence": 0.8},
            {"prob": 0.35, "odds": 3.20, "confidence": 0.6},
            {"prob": 0.5, "odds": 2.05, "confidence": 0.7},
        ]

        comparison_results = []

        for i, case in enumerate(test_cases):
            # 原始计算器
            original_ev = original_calc.calculate_ev(case["prob"], case["odds"])
            original_kelly = original_calc.calculate_kelly_fraction(
                original_ev, case["odds"], case["prob"]
            )

            # 增强计算器
            enhanced_result = enhanced_calc.calculate_enhanced_ev(
                BetType.HOME_WIN, case["prob"], case["odds"], case["confidence"]
            )

            comparison = {
                "case": i + 1,
                "probability": case["prob"],
                "odds": case["odds"],
                "original": {
                    "ev": original_ev,
                    "kelly_fraction": original_kelly,
                },
                "enhanced": {
                    "ev": enhanced_result.ev,
                    "kelly_fraction": enhanced_result.kelly_fraction,
                    "value_rating": enhanced_result.value_rating,
                    "recommendation": enhanced_result.recommendation,
                },
            }

            comparison_results.append(comparison)

            logger.info(
                f"  案例{i+1}: 原始EV={original_ev:.3f}, 增强EV={enhanced_result.ev:.3f}, "
                f"原始Kelly={original_kelly:.3f}, 增强Kelly={enhanced_result.kelly_fraction:.3f}"
            )

        return {"status": "success", "results": comparison_results}

    except Exception as e:
        logger.error(f"对比测试失败: {e}")
        return {"status": "error", "message": str(e)}


async def main():
    """主测试函数"""

    logger.info("=" * 60)
    logger.info("🚀 增强EV计算器测试开始")
    logger.info("Issue #121: EV计算算法参数调优")
    logger.info("=" * 60)

    # 确保日志目录存在
    Path("logs").mkdir(exist_ok=True)

    test_results = {}

    # 1. Kelly准则优化测试
    test_results["kelly_optimization"] = test_kelly_optimization()

    # 2. 价值评级增强测试
    test_results["value_rating"] = test_value_rating_enhancement()

    # 3. 增强EV计算测试
    test_results["enhanced_ev"] = await test_enhanced_ev_calculation()

    # 4. 策略回测测试
    test_results["backtesting"] = await test_strategy_backtesting()

    # 5. 与原始对比测试
    test_results["comparison"] = compare_with_original()

    # 生成测试报告
    logger.info("=" * 60)
    logger.info("📊 测试结果汇总")
    logger.info("=" * 60)

    for test_name, result in test_results.items():
        status = result["status"]
        if status == "success":
            logger.info(f"✅ {test_name}: 通过")
        else:
            logger.error(f"❌ {test_name}: 失败 - {result.get('message', '未知错误')}")

    # 保存测试结果到文件
    try:
        with open("enhanced_ev_test_results.json", "w", encoding="utf-8") as f:
            json.dump(test_results, f, indent=2, ensure_ascii=False, default=str)
        logger.info("📄 测试结果已保存到 enhanced_ev_test_results.json")
    except Exception as e:
        logger.error(f"保存测试结果失败: {e}")

    # 生成优化建议
    logger.info("=" * 60)
    logger.info("💡 优化建议")
    logger.info("=" * 60)

    if test_results.get("backtesting", {}).get("status") == "success":
        backtest_data = test_results["backtesting"]["results"]
        best_strategy = max(backtest_data.items(), key=lambda x: x[1]["roi"])
        logger.info(
            f"🏆 最佳策略: {best_strategy[0]} (ROI: {best_strategy[1]['roi']:.2f}%)"
        )

        for strategy, data in backtest_data.items():
            if data["roi"] > 5 and data["max_drawdown"] < 0.15:
                logger.info(f"✅ {strategy}: ROI={data['roi']:.2f}%, 风险控制良好")
            elif data["roi"] > 0:
                logger.info(f"⚠️ {strategy}: ROI={data['roi']:.2f}%, 需要风险优化")
            else:
                logger.info(f"❌ {strategy}: ROI={data['roi']:.2f}%, 建议调整")

    logger.info("=" * 60)
    logger.info("🎉 增强EV计算器测试完成!")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
