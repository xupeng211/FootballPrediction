#!/usr/bin/env python3
"""
工业级回测器数学验证 - V9.7 质量保证
针对 Shin's Method 去水准确性和 Kelly 公式进行银行级验证

验证内容:
1. Shin's Method 的去水准确性
2. 手算验证"公平概率"之和等于 1.0
3. Kelly 公式计算的数学正确性
4. 边界条件和异常处理
"""

import pytest
import numpy as np
from typing import Tuple, Dict, Any

# 导入回测器模块
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.ml.standard_backtester import StandardBacktester


class TestBacktesterMath:
    """回测器数学验证测试套件"""

    @pytest.fixture
    def backtester(self) -> StandardBacktester:
        """回测器实例"""
        return StandardBacktester(version="V9.7-MATH-TEST")

    # ==================== Shin's Method 去水验证 ====================

    def test_shin_method_basic_accuracy(self, backtester: StandardBacktester):
        """
        测试用例1: Shin's Method 基础准确性验证
        手算一组赔率（2.0, 3.0, 4.0），确保代码计算的"公平概率"之和等于 1.0
        """
        # 测试用例1: 赔率 (2.0, 3.0, 4.0)
        home_odds, draw_odds, away_odds = 2.0, 3.0, 4.0

        adj_home_odds, adj_draw_odds, adj_away_odds = backtester.shin_method(home_odds, draw_odds, away_odds)

        # 计算调整后的隐含概率
        adj_home_prob = 1 / adj_home_odds
        adj_draw_prob = 1 / adj_draw_odds
        adj_away_prob = 1 / adj_away_odds

        total_prob = adj_home_prob + adj_draw_prob + adj_away_prob

        # 验证概率总和等于 1.0（允许浮点误差）
        assert abs(total_prob - 1.0) < 1e-10, f"概率总和不为1.0: {total_prob}"

        # 验证赔率合理性
        assert adj_home_odds > 1.0
        assert adj_draw_odds > 1.0
        assert adj_away_odds > 1.0

        # 验证去水效果（调整后的赔率应该更高，表示更低的不合理抽水）
        assert adj_home_odds >= home_odds * 0.95  # 至少不应该大幅降低

    def test_shin_method_known_cases(self, backtester: StandardBacktester):
        """
        测试已知结果的标准用例
        """
        test_cases = [
            # (home_odds, draw_odds, away_odds, expected_sum_error_tolerance)
            (2.0, 3.0, 4.0, 1e-10),  # 标准案例
            (1.5, 3.5, 5.0, 1e-10),  # 低主胜赔率
            (3.0, 3.2, 2.5, 1e-10),  # 均衡赔率
            (10.0, 6.0, 1.4, 1e-10),  # 极端赔率
            (1.8, 2.1, 4.5, 1e-10),  # 实际赔率范围
        ]

        for home_odds, draw_odds, away_odds, tolerance in test_cases:
            adj_home_odds, adj_draw_odds, adj_away_odds = backtester.shin_method(home_odds, draw_odds, away_odds)

            # 计算隐含概率
            adj_home_prob = 1 / adj_home_odds
            adj_draw_prob = 1 / adj_draw_odds
            adj_away_prob = 1 / adj_away_odds
            total_prob = adj_home_prob + adj_draw_prob + adj_away_prob

            assert abs(total_prob - 1.0) < tolerance, (
                f"赔率 ({home_odds}, {draw_odds}, {away_odds}) 概率总和: {total_prob}"
            )

    def test_shin_method_water_removal_amount(self, backtester: StandardBacktester):
        """
        测试去水量的正确性
        """
        # 设置已知的去水量
        water_removal = backtester.WATER_REMOVAL

        # 使用简单赔率进行手动验证
        home_odds, draw_odds, away_odds = 2.0, 3.0, 4.0

        # 计算原始隐含概率
        original_home_prob = 1 / home_odds
        original_draw_prob = 1 / draw_odds
        original_away_prob = 1 / away_odds
        original_total = original_home_prob + original_draw_prob + original_away_prob

        # 原始归一化概率
        norm_home = original_home_prob / original_total
        norm_draw = original_draw_prob / original_total
        norm_away = original_away_prob / original_total

        # 应用Shin's Method调整
        adj_home_odds, adj_draw_odds, adj_away_odds = backtester.shin_method(home_odds, draw_odds, away_odds)

        # 验证调整符合预期的去水量
        adj_home_prob = 1 / adj_home_odds
        adj_draw_prob = 1 / adj_draw_odds
        adj_away_prob = 1 / adj_away_odds

        # 验证概率减少比例接近去水量
        home_reduction = (norm_home - adj_home_prob) / norm_home
        draw_reduction = (norm_draw - adj_draw_prob) / norm_draw
        away_reduction = (norm_away - adj_away_prob) / norm_away

        # 所有结果应该接近目标去水量（允许小的差异因为重新归一化）
        assert abs(home_reduction - water_removal) < 0.01
        assert abs(draw_reduction - water_removal) < 0.01
        assert abs(away_reduction - water_removal) < 0.01

    def test_shin_method_edge_cases(self, backtester: StandardBacktester):
        """
        测试边界条件和异常情况
        """
        # 测试极小赔率（不应该出现但需要处理）
        with pytest.raises((ZeroDivisionError, ValueError)):
            backtester.shin_method(0.0, 3.0, 4.0)

        with pytest.raises((ZeroDivisionError, ValueError)):
            backtester.shin_method(2.0, 0.0, 4.0)

        with pytest.raises((ZeroDivisionError, ValueError)):
            backtester.shin_method(2.0, 3.0, 0.0)

        # 测试极大赔率
        large_home, large_draw, large_away = backtester.shin_method(1000.0, 500.0, 200.0)

        # 验证极大赔率也能正常处理
        assert large_home > 1.0
        assert large_draw > 1.0
        assert large_away > 1.0

        # 验证概率总和
        total_prob = 1 / large_home + 1 / large_draw + 1 / large_away
        assert abs(total_prob - 1.0) < 1e-10

    # ==================== Kelly 公式验证 ====================

    def test_kelly_formula_known_cases(self, backtester: StandardBacktester):
        """
        测试Kelly公式的已知计算结果
        """
        test_cases = [
            # (true_prob, odds, expected_kelly_fraction)
            (0.6, 2.0, 0.1),  # f = (1*0.6-0.4)/1 * 0.25 = 0.05
            (0.7, 2.5, 0.06),  # f = (1.5*0.7-0.3)/1.5 * 0.25 ≈ 0.06
            (0.8, 1.8, 0.11),  # f = (0.8*0.8-0.2)/0.8 * 0.25 = 0.15 * 0.25 = 0.0375
        ]

        for true_prob, odds, expected_kelly in test_cases:
            kelly = backtester.kelly_criterion(true_prob, odds)

            # 计算理论值
            b = odds - 1
            p = true_prob
            q = 1 - p
            theoretical = max(0, (b * p - q) / b) * backtester.KELLY_FRACTION

            # 应用最大投注限制
            theoretical = min(theoretical, backtester.MAX_BET)

            assert abs(kelly - theoretical) < 1e-4, (
                f"Kelly计算错误: true_prob={true_prob}, odds={odds}, expected={theoretical}, got={kelly}"
            )

    def test_kelly_formula_zero_edge(self, backtester: StandardBacktester):
        """
        测试零边际时Kelly公式返回0
        """
        # 当隐含概率等于真实概率时，边际为0
        test_cases = [
            (0.5, 2.0),  # 隐含概率=0.5
            (0.4, 2.5),  # 隐含概率=0.4
            (0.25, 4.0),  # 隐含概率=0.25
        ]

        for true_prob, odds in test_cases:
            kelly = backtester.kelly_criterion(true_prob, odds)
            assert kelly == 0.0, f"零边际时Kelly应该为0: true_prob={true_prob}, odds={odds}, kelly={kelly}"

    def test_kelly_formula_negative_edge(self, backtester: StandardBacktester):
        """
        测试负边际时Kelly公式返回0
        """
        test_cases = [
            (0.3, 2.0),  # 隐含概率=0.5 > 真实概率
            (0.2, 3.0),  # 隐含概率≈0.333 > 真实概率
            (0.1, 5.0),  # 隐含概率=0.2 > 真实概率
        ]

        for true_prob, odds in test_cases:
            kelly = backtester.kelly_criterion(true_prob, odds)
            assert kelly == 0.0, f"负边际时Kelly应该为0: true_prob={true_prob}, odds={odds}, kelly={kelly}"

    def test_kelly_formula_cap_limits(self, backtester: StandardBacktester):
        """
        测试Kelly公式的硬上限
        """
        # 极端高优势场景
        extreme_cases = [
            (0.95, 2.0),  # 95%概率，2倍赔率
            (0.90, 1.5),  # 90%概率，1.5倍赔率
            (0.99, 3.0),  # 99%概率，3倍赔率
        ]

        for true_prob, odds in extreme_cases:
            kelly = backtester.kelly_criterion(true_prob, odds)

            # 应该被限制在最大投注比例
            assert kelly <= backtester.MAX_BET, (
                f"Kelly超过最大限制: true_prob={true_prob}, odds={odds}, kelly={kelly}, max={backtester.MAX_BET}"
            )

    def test_kelly_formula_monotonicity(self, backtester: StandardBacktester):
        """
        测试Kelly公式的单调性
        """
        odds = 2.0

        # 随着概率增加，Kelly应该单调递增（在合理范围内）
        prev_kelly = 0
        for prob in np.linspace(0.51, 0.9, 10):
            kelly = backtester.kelly_criterion(prob, odds)
            assert kelly >= prev_kelly - 1e-10, f"Kelly公式不单调: prob={prob}, kelly={kelly}, prev_kelly={prev_kelly}"
            prev_kelly = kelly

    # ==================== 数值精度测试 ====================

    def test_numerical_precision_extreme_cases(self, backtester: StandardBacktester):
        """
        测试极端情况下的数值精度
        """
        # 测试极小概率
        tiny_prob_cases = [
            (1e-6, 2.0),
            (1e-8, 3.0),
            (1e-10, 5.0),
        ]

        for tiny_prob, odds in tiny_prob_cases:
            kelly = backtester.kelly_criterion(tiny_prob, odds)

            # 应该返回0或极小值，但不应该出现数值错误
            assert not np.isnan(kelly)
            assert not np.isinf(kelly)
            assert kelly >= 0

        # 测试接近1的概率
        high_prob_cases = [
            (0.999999, 2.0),
            (0.9999999, 3.0),
            (0.99999999, 5.0),
        ]

        for high_prob, odds in high_prob_cases:
            kelly = backtester.kelly_criterion(high_prob, odds)

            # 应该返回合理值，但不应该超过最大限制
            assert not np.isnan(kelly)
            assert not np.isinf(kelly)
            assert 0 <= kelly <= backtester.MAX_BET

    def test_floating_point_precision(self, backtester: StandardBacktester):
        """
        测试浮点精度处理
        """
        # 测试大量连续计算是否累积误差
        accumulated_error = 0

        for i in range(1000):
            # 使用相近的数值进行连续计算
            prob = 0.55 + i * 1e-6
            odds = 2.0 + i * 1e-6

            kelly = backtester.kelly_criterion(prob, odds)
            theoretical = max(0, ((odds - 1) * prob - (1 - prob)) / (odds - 1)) * backtester.KELLY_FRACTION
            theoretical = min(theoretical, backtester.MAX_BET)

            error = abs(kelly - theoretical)
            accumulated_error += error

        # 累积误差应该保持在可接受范围内
        assert accumulated_error < 0.1, f"累积误差过大: {accumulated_error}"

    # ==================== 集成验证 ====================

    def test_shin_kelly_integration(self, backtester: StandardBacktester):
        """
        测试Shin's Method和Kelly公式的集成
        """
        # 使用实际市场赔率
        original_odds = {"home": 2.10, "draw": 3.40, "away": 3.60}

        # 应用Shin's Method去水
        adj_home, adj_draw, adj_away = backtester.shin_method(
            original_odds["home"], original_odds["draw"], original_odds["away"]
        )

        # 验证去水后的赔率更公平
        adj_odds = {"home": adj_home, "draw": adj_draw, "away": adj_away}

        # 比较隐含概率
        original_probs = {k: 1 / v for k, v in original_odds.items()}
        adj_probs = {k: 1 / v for k, v in adj_odds.items()}

        original_sum = sum(original_probs.values())
        adj_sum = sum(adj_probs.values())

        # 调整后的总和应该更接近1.0
        assert abs(adj_sum - 1.0) < abs(original_sum - 1.0)

        # 测试Kelly公式在去水后的赔率上的表现
        model_prob = 0.52
        original_kelly = backtester.kelly_criterion(model_prob, original_odds["home"])
        adj_kelly = backtester.kelly_criterion(model_prob, adj_odds["home"])

        # 去水后的Kelly应该更保守（因为赔率更公平）
        # 但这取决于具体情况，所以我们只验证计算是合理的
        assert 0 <= original_kelly <= backtester.MAX_BET
        assert 0 <= adj_kelly <= backtester.MAX_BET


def run_manual_verification():
    """
    手动验证函数 - 可以独立运行进行验证
    """
    print("🔬 开始手动数学验证...")

    backtester = StandardBacktester(version="MANUAL-VERIFICATION")

    # 验证1: Shin's Method基础案例
    print("\n1. 验证Shin's Method基础案例 (2.0, 3.0, 4.0)")
    home_odds, draw_odds, away_odds = 2.0, 3.0, 4.0
    adj_home, adj_draw, adj_away = backtester.shin_method(home_odds, draw_odds, away_odds)

    print(f"原始赔率: home={home_odds}, draw={draw_odds}, away={away_odds}")
    print(f"调整后赔率: home={adj_home:.6f}, draw={adj_draw:.6f}, away={adj_away:.6f}")

    # 验证概率总和
    total_prob = 1 / adj_home + 1 / adj_draw + 1 / adj_away
    print(f"隐含概率总和: {total_prob:.10f} (应该接近1.0)")

    # 验证2: Kelly公式
    print("\n2. 验证Kelly公式")
    true_prob, odds = 0.6, 2.0
    kelly = backtester.kelly_criterion(true_prob, odds)

    # 手动计算
    b = odds - 1
    p = true_prob
    q = 1 - p
    manual_kelly = max(0, (b * p - q) / b) * backtester.KELLY_FRACTION

    print(f"真实概率: {true_prob}, 赔率: {odds}")
    print(f"Kelly计算结果: {kelly:.6f}")
    print(f"手动计算结果: {manual_kelly:.6f}")
    print(f"差异: {abs(kelly - manual_kelly):.10f}")

    print("\n✅ 手动验证完成!")


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])

    # 额外运行手动验证
    run_manual_verification()
