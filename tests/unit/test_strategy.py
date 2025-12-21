"""
金融级策略引擎压力测试
极端情况下的系统健壮性验证
"""

import unittest
import sys
from pathlib import Path
import logging
from datetime import datetime

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.logic.strategy_engine import (
    StrategyEngine, StrategyMode, BettingParameters, RiskLevel, BettingRecommendation
)

# 设置测试日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class TestStrategyEngineStress(unittest.TestCase):
    """金融级策略引擎压力测试"""

    def setUp(self):
        """测试设置"""
        # 使用严格的金融级参数
        self.conservative_params = BettingParameters(
            max_single_bet_pct=0.01,          # 单场最大1%
            max_daily_bets=3,                   # 每日最大3次
            max_consecutive_losses=3,           # 最大连续3次亏损
            max_total_exposure=0.15,            # 最大总敞口15%
            kelly_fraction=0.15,                # Kelly保守系数15%
            max_kelly_pct=0.03,                  # 最大Kelly 3%
            min_edge_threshold=0.08,             # 最小边际优势8%
            min_expected_value=0.02,            # 最小期望收益2%
        )

        self.engine = StrategyEngine(params=self.conservative_params, mode=StrategyMode.LIVE)

    def test_model_extreme_confidence_100_percent(self):
        """测试1: 模型狂妄 - 预测胜率100%"""
        print("\n🔥 测试1: 模型狂妄情况 (预测胜率100%)")
        print("-" * 50)

        # 模拟极端预测：模型100%确定主胜
        extreme_model_probs = {
            'home_win': 1.0,  # 100%确定
            'draw': 0.0,
            'away_win': 0.0
        }

        # 正常市场赔率
        market_odds = {
            'home_win': 2.10,
            'draw': 3.40,
            'away_win': 3.60
        }

        # 执行策略引擎
        recommendation = self.engine.evaluate_betting_opportunity(
            extreme_model_probs, market_odds,
            "test_001", "ManCity", "Arsenal"
        )

        # 验证结果
        self.assertIsNotNone(recommendation, "应该生成建议")

        # 验证风险控制 - 极端概率应被正确检测和拒绝
        self.assertEqual(recommendation.recommendation_type, "NO_BET", "极端概率应拒绝下注")
        self.assertEqual(recommendation.risk_level, RiskLevel.HIGH, "应标记为高风险")

        # 验证警告信息包含极端概率检测
        warning_str = str(recommendation.warnings)
        self.assertTrue(any("极端模型概率" in w for w in recommendation.warnings),
                       f"应该检测到极端概率警告，实际警告: {warning_str}")

        # 验证Kelly公式不会产生荒谬结果
        if recommendation.kelly_fraction is not None:
            self.assertLessEqual(recommendation.kelly_fraction, self.conservative_params.max_kelly_pct,
                              "Kelly分数应被限制在最大值内")

        print(f"✅ 结果: {recommendation.recommendation_type}")
        print(f"   风险等级: {recommendation.risk_level.value}")
        print(f"   警告: {recommendation.warnings}")

    def test_market_extreme_odds_1_and_100(self):
        """测试2: 市场异常 - 赔率1.01和100.0"""
        print("\n🔥 测试2: 市场异常情况 (赔率1.01和100.0)")
        print("-" * 50)

        # 测试案例1: 极低赔率 1.01
        print("  子测试2a: 赔率 1.01")
        low_odds_market = {
            'home_win': 1.01,
            'draw': 15.50,
            'away_win': 25.00
        }

        normal_model_probs = {
            'home_win': 0.95,  # 高概率
            'draw': 0.03,
            'away_win': 0.02
        }

        recommendation_low_odds = self.engine.evaluate_betting_opportunity(
            normal_model_probs, low_odds_market,
            "test_002", "Liverpool", "Chelsea"
        )

        # 验证极低赔率处理 - 检查任何赔率相关的警告
        warning_str_low = str(recommendation_low_odds.warnings)
        self.assertTrue(any("赔率" in w and ("低" in w or "异常" in w) for w in recommendation_low_odds.warnings),
                       f"应检测到过低赔率警告，实际警告: {warning_str_low}")
        self.assertEqual(recommendation_low_odds.recommendation_type, "NO_BET", "极低赔率应拒绝下注")

        print(f"  ✅ 结果: {recommendation_low_odds.recommendation_type}")
        print(f"     警告: {recommendation_low_odds.warnings}")

        # 测试案例2: 极高赔率 100.0
        print("  子测试2b: 赔率 100.0")
        high_odds_market = {
            'home_win': 100.0,
            'draw': 50.0,
            'away_win': 1.02
        }

        recommendation_high_odds = self.engine.evaluate_betting_opportunity(
            normal_model_probs, high_odds_market,
            "test_003", "Tottenham", "Burnley"
        )

        # 验证极高赔率处理 - 检查任何赔率相关的警告
        warning_str_high = str(recommendation_high_odds.warnings)
        self.assertTrue(any("赔率" in w and ("高" in w or "异常" in w) for w in recommendation_high_odds.warnings),
                       f"应检测到过高赔率警告，实际警告: {warning_str_high}")
        self.assertEqual(recommendation_high_odds.recommendation_type, "NO_BET", "极高赔率应拒绝下注")

        print(f"  ✅ 结果: {recommendation_high_odds.recommendation_type}")
        print(f"     警告: {recommendation_high_odds.warnings}")

    def test_portfolio_balance_near_zero(self):
        """测试3: 资金枯竭 - 余额趋于0"""
        print("\n🔥 测试3: 资金枯竭情况 (余额趋于0)")
        print("-" * 50)

        # 模拟资金枯竭状态
        self.engine.portfolio.current_capital = 50.0  # 剩余5%
        self.engine.portfolio.consecutive_losses = 4     # 连续4次亏损

        # 测试常规下注机会
        normal_model_probs = {
            'home_win': 0.55,
            'draw': 0.25,
            'away_win': 0.20
        }

        normal_market_odds = {
            'home_win': 2.20,
            'draw': 3.30,
            'away_win': 4.10
        }

        recommendation = self.engine.evaluate_betting_opportunity(
            normal_model_probs, normal_market_odds,
            "test_004", "ManUtd", "Leicester"
        )

        # 验证资金保护机制
        self.assertEqual(recommendation.recommendation_type, "NO_BET", "资金枯竭应拒绝下注")
        self.assertEqual(recommendation.risk_level, RiskLevel.CRITICAL, "应标记为紧急风险")
        self.assertTrue("不足" in str(recommendation.warnings) or "枯竭" in str(recommendation.warnings),
                       "应检测到资金不足警告")

        print(f"✅ 结果: {recommendation.recommendation_type}")
        print(f"   风险等级: {recommendation.risk_level.value}")
        print(f"   资金比例: {recommendation.warnings}")

    def test_kelly_formula_extreme_values(self):
        """测试4: Kelly公式极端值处理"""
        print("\n🔥 测试4: Kelly公式极端值处理")
        print("-" * 50)

        # 测试负Edge情况
        print("  子测试4a: 负边际优势")
        negative_edge_model = {
            'home_win': 0.2,
            'draw': 0.3,
            'away_win': 0.5
        }

        # 使用低赔率确保产生负Edge
        negative_edge_market = {
            'home_win': 1.8,  # 市场隐含概率0.556 > 模型0.2 = 负Edge
            'draw': 2.8,      # 市场隐含概率0.357 > 模型0.3 = 负Edge
            'away_win': 1.7   # 市场隐含概率0.588 > 模型0.5 = 负Edge
        }

        recommendation_negative = self.engine.evaluate_betting_opportunity(
            negative_edge_model, negative_edge_market,
            "test_005", "Everton", "Newcastle"
        )

        self.assertEqual(recommendation_negative.kelly_fraction, 0.0, "负Edge应产生0 Kelly分数")
        self.assertEqual(recommendation_negative.recommendation_type, "NO_BET", "负Edge应拒绝下注")

        print(f"  ✅ Kelly分数: {recommendation_negative.kelly_fraction}")
        print(f"  结果: {recommendation_negative.recommendation_type}")

        # 测试极大Edge情况
        print("  子测试4b: 极大边际优势")
        huge_edge_model = {
            'home_win': 0.95,
            'draw': 0.03,
            'away_win': 0.02
        }

        huge_edge_market = {
            'home_win': 2.0,
            'draw': 10.0,
            'away_win': 30.0
        }

        recommendation_huge = self.engine.evaluate_betting_opportunity(
            huge_edge_model, huge_edge_market,
            "test_006", "WestHam", "Crystal Palace"
        )

        # 验证Kelly公式限制
        if recommendation_huge.kelly_fraction is not None:
            self.assertLessEqual(recommendation_huge.kelly_fraction, self.conservative_params.max_kelly_pct,
                              "极大Edge的Kelly分数应被限制")

        print(f"  ✅ 原始Kelly: {recommendation_huge.kelly_fraction}")
        print(f"  结果: {recommendation_huge.recommendation_type}")

    def test_portfolio_max_constraints_violation(self):
        """测试5: 投资组合约束违反"""
        print("\n🔥 测试5: 投资组合约束违反")
        print("-" * 50)

        # 模拟达到约束上限
        self.engine.portfolio.daily_bets = 5  # 超过3次限制
        self.engine.portfolio.active_positions = [
            {'outcome': 'home_win', 'stake_pct': 0.05}  # 超过2%单场限制
        ]

        normal_model_probs = {
            'home_win': 0.6,
            'draw': 0.25,
            'away_win': 0.15
        }

        normal_market_odds = {
            'home_win': 1.8,
            'draw': 3.6,
            'away_win': 4.8
        }

        recommendation = self.engine.evaluate_betting_opportunity(
            normal_model_probs, normal_market_odds,
            "test_007", "Aston Villa", "West Ham"
        )

        # 验证约束保护
        self.assertEqual(recommendation.recommendation_type, "NO_BET", "约束违反应拒绝下注")
        self.assertTrue(any("超限" in warning for warning in recommendation.warnings),
                       "应检测到约束超限警告")

        print(f"✅ 结果: {recommendation.recommendation_type}")
        print(f"   约束警告数量: {len(recommendation.warnings)}")

    def test_emergency_stop_mechanism(self):
        """测试6: 紧急停止机制"""
        print("\n🔥 测试6: 紧急停止机制")
        print("-" * 50)

        # 模拟紧急情况
        emergency_reason = "连续亏损超过安全阈值"
        stop_result = self.engine.emergency_stop(emergency_reason)

        self.assertTrue(stop_result, "紧急停止应成功执行")
        self.assertEqual(self.engine.portfolio.risk_level, RiskLevel.CRITICAL, "风险等级应为紧急")
        self.assertEqual(len(self.engine.portfolio.active_positions), 0, "活跃仓位应被清空")

        # 验证后续请求被拒绝
        normal_model_probs = {'home_win': 0.5, 'draw': 0.3, 'away_win': 0.2}
        normal_market_odds = {'home_win': 2.0, 'draw': 3.4, 'away_win': 3.6}

        recommendation_after_stop = self.engine.evaluate_betting_opportunity(
            normal_model_probs, normal_market_odds,
            "test_008", "Brighton", "Fulham"
        )

        self.assertEqual(recommendation_after_stop.risk_level, RiskLevel.CRITICAL, "紧急停止后仍为高风险")

        print(f"✅ 紧急停止: {stop_result}")
        print(f"   风险等级: {recommendation_after_stop.risk_level.value}")

    def tearDown(self):
        """测试清理"""
        print("\n🧹 压力测试清理完成")
        # 重置引擎状态
        self.engine.portfolio = self.engine.portfolio.__class__()
        self.engine.risk_metrics = {
            'total_recommendations': 0,
            'high_risk_warnings': 0,
            'circular_warnings': 0,
            'odds_warnings': 0,
            'portfolio_warnings': 0,
            'safety_activations': 0
        }


if __name__ == '__main__':
    print("🛡️ 金融级策略引擎压力测试开始")
    print("=" * 60)
    print("测试极端情况下的系统健壮性...")
    print("🎯 目标: 验证本金归零零风险保护")
    print("⚡ 标准: 任何极端情况都不应产生非理性下注")

    unittest.main()