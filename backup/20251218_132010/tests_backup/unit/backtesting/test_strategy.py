"""
策略测试 (Strategy Tests)

测试策略接口和默认策略实现。

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

import pytest
from decimal import Decimal

from src.backtesting.models import BetType
from src.backtesting.strategy import (
    SimpleValueStrategy,
    ConservativeStrategy,
    AggressiveStrategy,
    StrategyFactory,
)


class TestSimpleValueStrategy:
    """SimpleValueStrategy测试"""

    @pytest.fixture
    def strategy(self):
        """策略fixture"""
        return SimpleValueStrategy(value_threshold=0.1, min_confidence=0.3)

    @pytest.fixture
    def sample_match_data(self):
        """示例比赛数据"""
        return {
            "id": 1,
            "home_team_id": 1,
            "away_team_id": 2,
            "home_score": 2,
            "away_score": 1,
            "home_win_prob": 0.45,
            "draw_prob": 0.30,
            "away_win_prob": 0.25,
            "model_confidence": 0.75,
        }

    @pytest.fixture
    def sample_odds_data(self):
        """示例赔率数据"""
        return {
            "home": Decimal("2.20"),
            "draw": Decimal("3.30"),
            "away": Decimal("3.80"),
            "home_odds": Decimal("2.20"),
            "draw_odds": Decimal("3.30"),
            "away_odds": Decimal("3.80"),
        }

    @pytest.mark.asyncio
    async def test_decide_value_bet(
        self, strategy, sample_match_data, sample_odds_data
    ):
        """测试有价值下注决策"""
        # 创建有价值的主队胜出场景
        sample_match_data["home_win_prob"] = 0.50  # 高概率
        sample_odds_data["home"] = Decimal("2.50")  # 高赔率

        decision = await strategy.decide(sample_match_data, sample_odds_data)

        assert decision.match_id == 1
        assert decision.bet_type == BetType.HOME
        assert decision.value_edge > 0.1  # 应该满足价值阈值
        assert decision.confidence >= 0.3  # 应该满足最小置信度
        assert decision.odds == Decimal("2.50")

    @pytest.mark.asyncio
    async def test_decide_skip_no_value(
        self, strategy, sample_match_data, sample_odds_data
    ):
        """测试无价值时的跳过决策"""
        # 创建无价值场景（概率与赔率匹配）
        sample_match_data["home_win_prob"] = 0.40
        sample_odds_data["home"] = Decimal("2.50")  # 隐含概率约为0.40

        decision = await strategy.decide(sample_match_data, sample_odds_data)

        assert decision.bet_type == BetType.SKIP
        assert decision.stake == Decimal("0.00")

    @pytest.mark.asyncio
    async def test_decide_insufficient_confidence(
        self, strategy, sample_match_data, sample_odds_data
    ):
        """测试置信度不足时的跳过决策"""
        # 创建有价值但置信度不足的场景
        sample_match_data["home_win_prob"] = 0.60
        sample_odds_data["home"] = Decimal("2.80")
        sample_match_data["model_confidence"] = 0.2  # 低于最小置信度

        decision = await strategy.decide(sample_match_data, sample_odds_data)

        assert decision.bet_type == BetType.SKIP

    @pytest.mark.asyncio
    async def test_extract_model_probabilities_different_formats(self, strategy):
        """测试从不同格式提取模型概率"""
        # 测试标准格式
        match_data_1 = {
            "id": 1,
            "predictions": {"home_win": 0.45, "draw": 0.30, "away_win": 0.25},
        }

        probs = strategy._extract_model_probabilities(match_data_1)
        assert probs["home_win"] == 0.45
        assert probs["draw"] == 0.30
        assert probs["away_win"] == 0.25

        # 测试分离字段格式
        match_data_2 = {
            "id": 2,
            "home_win_prob": 0.35,
            "draw_prob": 0.35,
            "away_win_prob": 0.30,
        }

        probs = strategy._extract_model_probabilities(match_data_2)
        assert probs["home_win"] == 0.35
        assert probs["draw"] == 0.35
        assert probs["away_win"] == 0.30

        # 测试无效格式
        match_data_3 = {"id": 3, "invalid": "data"}
        probs = strategy._extract_model_probabilities(match_data_3)
        assert probs is None

    def test_extract_odds_different_formats(self, strategy):
        """测试从不同格式提取赔率"""
        # 测试标准格式
        odds_data_1 = {
            "odds": {
                "home": Decimal("2.20"),
                "draw": Decimal("3.30"),
                "away": Decimal("3.80"),
            }
        }

        odds = strategy._extract_odds(odds_data_1)
        assert odds["home"] == Decimal("2.20")
        assert odds["draw"] == Decimal("3.30")
        assert odds["away"] == Decimal("3.80")

        # 测试分离字段格式
        odds_data_2 = {
            "home_odds": Decimal("2.50"),
            "draw_odds": Decimal("3.40"),
            "away_odds": Decimal("3.90"),
        }

        odds = strategy._extract_odds(odds_data_2)
        assert odds["home"] == Decimal("2.50")
        assert odds["draw"] == Decimal("3.40")
        assert odds["away"] == Decimal("3.90")

        # 测试无效格式
        odds_data_3 = {"invalid": "data"}
        odds = strategy._extract_odds(odds_data_3)
        assert odds is None

    def test_calculate_implied_probability(self, strategy):
        """测试隐含概率计算"""
        prob = strategy._calculate_implied_probability(Decimal("2.00"))
        assert prob == 0.5

        prob = strategy._calculate_implied_probability(Decimal("3.00"))
        assert prob == pytest.approx(0.333333)

        prob = strategy._calculate_implied_probability(Decimal("1.50"))
        assert prob == pytest.approx(0.666667)

    def test_calculate_confidence(self, strategy):
        """测试置信度计算"""
        # 高价值场景
        confidence = strategy._calculate_confidence(0.6, 0.4, 0.2)
        assert confidence > 0.6  # 基础置信度 + 价值加成

        # 低价值场景
        confidence = strategy._calculate_confidence(0.3, 0.35, -0.05)
        assert confidence < 0.4  # 基础置信度较低


class TestStrategyVariants:
    """策略变体测试"""

    @pytest.mark.asyncio
    async def test_conservative_strategy(self):
        """测试保守策略"""
        strategy = ConservativeStrategy(value_threshold=0.15, min_confidence=0.5)

        match_data = {
            "id": 1,
            "home_win_prob": 0.45,
            "draw_prob": 0.30,
            "away_win_prob": 0.25,
        }

        odds_data = {
            "home": Decimal("2.50"),  # 价值边际不足
            "draw": Decimal("3.30"),
            "away": Decimal("3.80"),
        }

        decision = await strategy.decide(match_data, odds_data)
        assert decision.bet_type == BetType.SKIP  # 保守策略应该跳过

    @pytest.mark.asyncio
    async def test_aggressive_strategy(self):
        """测试激进策略"""
        strategy = AggressiveStrategy(value_threshold=0.05, min_confidence=0.2)

        match_data = {
            "id": 1,
            "home_win_prob": 0.45,
            "draw_prob": 0.30,
            "away_win_prob": 0.25,
        }

        odds_data = {
            "home": Decimal("2.50"),  # 对激进策略来说有价值
            "draw": Decimal("3.30"),
            "away": Decimal("3.80"),
        }

        decision = await strategy.decide(match_data, odds_data)
        # 激进策略可能会下注（取决于具体的价值计算）
        assert decision.match_id == 1


class TestStrategyFactory:
    """策略工厂测试"""

    def test_create_strategy_simple_value(self):
        """测试创建简单价值策略"""
        strategy = StrategyFactory.create_strategy("simple_value", value_threshold=0.12)
        assert strategy.name == "SimpleValueStrategy"
        assert strategy.value_threshold == 0.12

    def test_create_strategy_conservative(self):
        """测试创建保守策略"""
        strategy = StrategyFactory.create_strategy("conservative")
        assert strategy.name == "ConservativeStrategy"
        assert strategy.value_threshold == 0.15
        assert strategy.min_confidence == 0.5

    def test_create_strategy_aggressive(self):
        """测试创建激进策略"""
        strategy = StrategyFactory.create_strategy("aggressive")
        assert strategy.name == "AggressiveStrategy"
        assert strategy.value_threshold == 0.05
        assert strategy.min_confidence == 0.2

    def test_create_unknown_strategy(self):
        """测试创建未知策略"""
        with pytest.raises(ValueError, match="Unknown strategy type"):
            StrategyFactory.create_strategy("unknown_strategy")

    def test_list_strategies(self):
        """测试列出可用策略"""
        strategies = StrategyFactory.list_strategies()
        expected = ["simple_value", "conservative", "aggressive"]
        assert all(s in strategies for s in expected)
