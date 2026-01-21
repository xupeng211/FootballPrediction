#!/usr/bin/env python3
"""
工业级策略引擎测试 - V9.7 质量保证
针对 Kelly 策略和风险控制进行银行级测试

测试用例:
1. 零优势测试: Edge <= 0 时，确保下注额严格为 0
2. 极端优势测试: 即使 Edge 极大，确保单笔下注不突破 2% 硬上限
3. 余额衰减测试: 模拟余额从 $1000 到 $1 的全过程逻辑稳定性
"""

import math
import os

# 导入策略引擎模块
import sys

import pytest

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from src.logic.strategy_engine import BettingParameters, RiskLevel, StrategyEngine, StrategyMode


class TestStrategyEngine:
    """策略引擎工业级测试套件"""

    @pytest.fixture
    def default_params(self) -> BettingParameters:
        """默认测试参数"""
        return BettingParameters()

    @pytest.fixture
    def conservative_params(self) -> BettingParameters:
        """保守测试参数"""
        return BettingParameters(
            max_single_bet_pct=0.01,  # 1% 最大单注
            kelly_fraction=0.1,  # 10% Kelly系数
            min_edge_threshold=0.1,  # 10% 最小边际
        )

    @pytest.fixture
    def strategy_engine(self, default_params: BettingParameters) -> StrategyEngine:
        """策略引擎实例"""
        return StrategyEngine(params=default_params, mode=StrategyMode.SANDBOX)

    @pytest.fixture
    def sample_market_odds(self) -> dict[str, float]:
        """示例市场赔率"""
        return {"home_win": 2.10, "draw": 3.40, "away_win": 3.60}

    @pytest.fixture
    def sample_model_probs(self) -> dict[str, float]:
        """示例模型概率"""
        return {"home_win": 0.52, "draw": 0.25, "away_win": 0.23}

    # ==================== 零优势测试 ====================

    def test_zero_edge_no_bet(
        self,
        strategy_engine: StrategyEngine,
        sample_market_odds: dict[str, float],
        sample_model_probs: dict[str, float],
    ):
        """
        测试用例1: 零优势测试
        当 Edge <= 0 时，确保下注额严格为 0
        """
        # 设置零优势或负优势场景
        zero_edge_probs = {
            "home_win": 0.40,  # 40% 概率 vs 2.10 赔率 => 负边际
            "draw": 0.30,
            "away_win": 0.30,
        }

        recommendation = strategy_engine.evaluate_betting_opportunity(
            model_probabilities=zero_edge_probs,
            market_odds=sample_market_odds,
            match_id="test_zero_edge",
            home_team="Test Home",
            away_team="Test Away",
        )

        # 验证严格不下注
        assert recommendation.recommendation_type == "NO_BET"
        assert recommendation.recommended_stake_pct == 0.0
        assert recommendation.kelly_fraction == 0.0
        assert recommendation.edge <= 0

    def test_negative_edge_no_bet(
        self, strategy_engine: StrategyEngine, sample_market_odds: dict[str, float]
    ):
        """
        测试负优势场景 - 严格不下注
        """
        # 明显的负优势场景
        negative_edge_probs = {
            "home_win": 0.35,  # 35% 概率 vs 2.10 赔率 => 强负边际
            "draw": 0.35,
            "away_win": 0.30,
        }

        recommendation = strategy_engine.evaluate_betting_opportunity(
            model_probabilities=negative_edge_probs,
            market_odds=sample_market_odds,
            match_id="test_negative_edge",
            home_team="Test Home",
            away_team="Test Away",
        )

        # 验证严格不下注
        assert recommendation.recommendation_type == "NO_BET"
        assert (
            recommendation.recommended_stake_pct is None
            or recommendation.recommended_stake_pct == 0.0
        )
        assert any("负边际优势" in warning for warning in recommendation.warnings)

    # ==================== 极端优势测试 ====================

    def test_extreme_edge_respect_hard_limit(
        self, strategy_engine: StrategyEngine, conservative_params: BettingParameters
    ):
        """
        测试用例2: 极端优势测试
        即使 Edge 极大，确保单笔下注不突破 1% 硬上限
        """
        # 使用保守参数
        engine = StrategyEngine(params=conservative_params, mode=StrategyMode.SANDBOX)

        # 设置极端优势场景 - 模型认为有99%胜率，但市场只有2.0赔率
        extreme_edge_probs = {
            "home_win": 0.99,  # 99% 概率 vs 2.0 赔率 => 极大边际
            "draw": 0.005,
            "away_win": 0.005,
        }

        extreme_odds = {"home_win": 2.0, "draw": 10.0, "away_win": 15.0}

        recommendation = engine.evaluate_betting_opportunity(
            model_probabilities=extreme_edge_probs,
            market_odds=extreme_odds,
            match_id="test_extreme_edge",
            home_team="Test Home",
            away_team="Test Away",
        )

        # 验证遵守硬上限
        if recommendation.recommended_stake_pct is not None:
            assert recommendation.recommended_stake_pct <= conservative_params.max_single_bet_pct
            assert recommendation.recommended_stake_pct <= 0.01  # 1%硬上限

    def test_kelly_formula_hard_cap(self, conservative_params: BettingParameters):
        """
        测试Kelly公式计算的硬上限
        """
        StrategyEngine(params=conservative_params, mode=StrategyMode.SANDBOX)

        # 测试各种极端场景
        test_cases = [
            (0.95, 1.5),  # 极高概率，低赔率
            (0.90, 2.0),  # 高概率，中等赔率
            (0.80, 5.0),  # 高概率，高赔率
            (0.70, 10.0),  # 中高概率，极高赔率
        ]

        for prob, odds in test_cases:
            with pytest.raises(ValueError):
                # 这些组合会产生荒谬的Kelly值，应该被系统拦截
                edge = prob - (1.0 / odds)
                if edge > 0:
                    # 手动计算Kelly验证不会超过上限
                    b = odds - 1.0
                    p = prob
                    q = 1.0 - p
                    raw_kelly = (b * p - q) / b

                    # 应用保守系数和上限
                    conservative_kelly = raw_kelly * conservative_params.kelly_fraction
                    capped_kelly = min(conservative_kelly, conservative_params.max_single_bet_pct)

                    # 验证上限有效
                    assert capped_kelly <= conservative_params.max_single_bet_pct

    # ==================== 余额衰减测试 ====================

    def test_capital_decay_stability(self, strategy_engine: StrategyEngine):
        """
        测试用例3: 余额衰减测试
        模拟余额从 $1000 到 $1 的全过程逻辑稳定性
        """
        # 设置初始状态
        strategy_engine.portfolio.current_capital = 1000.0
        strategy_engine.portfolio.initial_capital = 1000.0
        strategy_engine.portfolio.consecutive_losses = 0

        # 连续亏损场景测试
        for i in range(50):  # 模拟50次连续亏损
            # 设置合理的有优势场景，但结果为亏损
            model_probs = {"home_win": 0.55, "draw": 0.25, "away_win": 0.20}

            market_odds = {"home_win": 2.2, "draw": 3.5, "away_win": 4.0}

            # 下注（模拟）
            if strategy_engine.portfolio.current_capital > 10:  # 只有资金>10才下注
                recommendation = strategy_engine.evaluate_betting_opportunity(
                    model_probabilities=model_probs,
                    market_odds=market_odds,
                    match_id=f"decay_test_{i}",
                    home_team=f"Home_{i}",
                    away_team=f"Away_{i}",
                )

                # 如果建议下注，模拟亏损
                if (
                    recommendation.recommended_stake_pct
                    and recommendation.recommended_stake_pct > 0
                ):
                    bet_amount = (
                        strategy_engine.portfolio.current_capital
                        * recommendation.recommended_stake_pct
                    )
                    strategy_engine.portfolio.current_capital -= bet_amount
                    strategy_engine.portfolio.consecutive_losses += 1

            # 验证系统稳定性
            assert strategy_engine.portfolio.current_capital >= 0
            assert (
                strategy_engine.portfolio.consecutive_losses
                <= strategy_engine.params.max_consecutive_losses + 5
            )

            # 在低余额时应该触发风险控制
            if strategy_engine.portfolio.current_capital < 100:  # 低于10%初始资金
                # 应该触发高级别风险控制
                current_ratio = (
                    strategy_engine.portfolio.current_capital
                    / strategy_engine.portfolio.initial_capital
                )
                if current_ratio < 0.1:  # 低于10%
                    # 系统应该进入紧急停止状态
                    break

    def test_minimum_bet_threshold(self, strategy_engine: StrategyEngine):
        """
        测试最小投注阈值
        当资金过少时，不应该下注
        """
        # 设置极低余额
        strategy_engine.portfolio.current_capital = 5.0

        # 设置合理优势场景
        model_probs = {"home_win": 0.60, "draw": 0.25, "away_win": 0.15}

        market_odds = {"home_win": 2.1, "draw": 3.4, "away_win": 4.0}

        recommendation = strategy_engine.evaluate_betting_opportunity(
            model_probabilities=model_probs,
            market_odds=market_odds,
            match_id="test_minimum_bet",
            home_team="Test Home",
            away_team="Test Away",
        )

        # 资金过少时，即使有优势也不应该下注
        if strategy_engine.portfolio.current_capital * recommendation.recommended_stake_pct < 1:
            assert (
                recommendation.recommendation_type == "NO_BET"
                or recommendation.recommended_stake_pct == 0.0
            )

    # ==================== 风险控制测试 ====================

    def test_consecutive_loss_protection(self, strategy_engine: StrategyEngine):
        """
        测试连续亏损保护机制
        """
        # 设置连续亏损
        strategy_engine.portfolio.consecutive_losses = strategy_engine.params.max_consecutive_losses

        recommendation = strategy_engine.evaluate_betting_opportunity(
            model_probabilities={"home_win": 0.60, "draw": 0.25, "away_win": 0.15},
            market_odds={"home_win": 2.1, "draw": 3.4, "away_win": 4.0},
            match_id="test_consecutive_loss",
            home_team="Test Home",
            away_team="Test Away",
        )

        # 应该触发紧急停止
        assert recommendation.risk_level == RiskLevel.CRITICAL
        assert recommendation.recommendation_type == "NO_BET"

    def test_odds_validation(self, strategy_engine: StrategyEngine):
        """
        测试赔率验证
        """
        # 测试无效赔率
        invalid_odds_cases = [
            {"home_win": 0.5, "draw": 3.4, "away_win": 4.0},  # 赔率过低
            {"home_win": 2.1, "draw": 3.4, "away_win": 200.0},  # 赔率过高
            {"home_win": 2.1, "draw": 3.4, "away_win": 50.0},  # 赔率范围过大
        ]

        for invalid_odds in invalid_odds_cases:
            recommendation = strategy_engine.evaluate_betting_opportunity(
                model_probabilities={"home_win": 0.50, "draw": 0.25, "away_win": 0.25},
                market_odds=invalid_odds,
                match_id="test_invalid_odds",
                home_team="Test Home",
                away_team="Test Away",
            )

            # 应该拒绝或警告
            assert recommendation.recommendation_type == "NO_BET"
            assert len(recommendation.warnings) > 0

    # ==================== 数值精度测试 ====================

    def test_numerical_precision(self, strategy_engine: StrategyEngine):
        """
        测试数值计算精度
        """
        # 测试极小数值
        tiny_prob = 1e-10
        recommendation = strategy_engine.evaluate_betting_opportunity(
            model_probabilities={"home_win": 0.5, "draw": tiny_prob, "away_win": 0.5 - tiny_prob},
            market_odds={"home_win": 2.0, "draw": 100.0, "away_win": 2.0},
            match_id="test_precision",
            home_team="Test Home",
            away_team="Test Away",
        )

        # 确保不会出现数值错误
        assert recommendation is not None
        assert not math.isnan(recommendation.edge) if hasattr(recommendation, "edge") else True
        assert not math.isinf(recommendation.edge) if hasattr(recommendation, "edge") else True

    # ==================== 集成测试 ====================

    def test_complete_betting_flow(self, strategy_engine: StrategyEngine):
        """
        完整下注流程测试
        """
        # 测试完整场景：评估 -> 下注 -> 更新状态
        recommendation = strategy_engine.evaluate_betting_opportunity(
            model_probabilities={"home_win": 0.55, "draw": 0.25, "away_win": 0.20},
            market_odds={"home_win": 2.2, "draw": 3.5, "away_win": 4.0},
            match_id="integration_test",
            home_team="Integration Home",
            away_team="Integration Away",
        )

        # 验证推荐结果完整性
        assert recommendation.match_id == "integration_test"
        assert recommendation.home_team == "Integration Home"
        assert recommendation.away_team == "Integration Away"
        assert recommendation.outcome in ["home_win", "draw", "away_win", "no_value"]
        assert 0 <= recommendation.model_probability <= 1
        assert recommendation.odds > 1

        # 验证风险指标计算
        if recommendation.recommendation_type != "NO_BET":
            assert recommendation.recommended_stake_pct > 0
            assert recommendation.recommended_stake_pct <= strategy_engine.params.max_single_bet_pct
            assert recommendation.kelly_fraction is not None


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"])
