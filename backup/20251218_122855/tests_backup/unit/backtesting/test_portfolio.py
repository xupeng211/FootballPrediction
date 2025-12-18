"""
资金管理测试 (Portfolio Tests)

测试Portfolio类的资金管理和下注功能。

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

import pytest
from decimal import Decimal
from datetime import datetime

from src.backtesting.models import (
    BacktestConfig,
    BetDecision,
    BetOutcome,
    BetType,
)
from src.backtesting.portfolio import Portfolio


class TestPortfolio:
    """Portfolio类测试"""

    @pytest.fixture
    def config(self):
        """回测配置fixture"""
        return BacktestConfig(
            initial_balance=Decimal("10000.00"),
            max_stake_pct=0.05,
            min_stake=Decimal("100.00"),
            max_stake=Decimal("500.00"),
            value_threshold=0.1,
            min_confidence=0.3,
            max_daily_bets=10,
        )

    @pytest.fixture
    def portfolio(self, config):
        """Portfolio fixture"""
        return Portfolio(config)

    def test_portfolio_initialization(self, portfolio, config):
        """测试Portfolio初始化"""
        assert portfolio.initial_balance == config.initial_balance
        assert portfolio.current_balance == config.initial_balance
        assert portfolio.max_balance == config.initial_balance
        assert portfolio.min_balance == config.initial_balance
        assert portfolio.total_staked == Decimal("0.00")
        assert portfolio.total_wins == 0
        assert portfolio.total_losses == 0
        assert portfolio.total_skips == 0

    def test_calculate_stake(self, portfolio):
        """测试下注金额计算"""
        decision = BetDecision(
            match_id=1,
            bet_type=BetType.HOME,
            stake=Decimal("0.00"),
            confidence=0.8,
            implied_probability=0.4,
            model_probability=0.5,
            odds=Decimal("2.5"),
            value_edge=0.1,
        )

        stake = portfolio.calculate_stake(decision)
        expected = portfolio.current_balance * Decimal(
            str(portfolio.config.max_stake_pct)
        )
        expected *= Decimal(str(decision.confidence))
        expected *= Decimal(str(1 + min(decision.value_edge * 2, 1.0)))

        assert stake == expected.quantize(Decimal("0.01"))

    def test_calculate_stake_skip(self, portfolio):
        """测试跳过下注的金额计算"""
        decision = BetDecision(
            match_id=1,
            bet_type=BetType.SKIP,
            stake=Decimal("0.00"),
            confidence=0.0,
            implied_probability=0.0,
            model_probability=0.0,
            odds=Decimal("2.0"),
        )

        stake = portfolio.calculate_stake(decision)
        assert stake == Decimal("0.00")

    def test_can_place_bet_valid(self, portfolio):
        """测试有效下注条件检查"""
        decision = BetDecision(
            match_id=1,
            bet_type=BetType.HOME,
            stake=Decimal("0.00"),
            confidence=0.5,
            implied_probability=0.3,
            model_probability=0.5,
            odds=Decimal("3.0"),
            value_edge=0.2,
        )

        # 满足所有条件
        assert portfolio.can_place_bet(decision, datetime.now())

    def test_can_place_bet_insufficient_balance(self, portfolio):
        """测试余额不足时的下注检查"""
        # 模拟余额不足
        portfolio.current_balance = Decimal("50.00")

        decision = BetDecision(
            match_id=1,
            bet_type=BetType.HOME,
            stake=Decimal("100.00"),
            confidence=0.5,
            implied_probability=0.3,
            model_probability=0.5,
            odds=Decimal("3.0"),
            value_edge=0.2,
        )

        assert not portfolio.can_place_bet(decision, datetime.now())

    def test_can_place_bet_insufficient_value_edge(self, portfolio):
        """测试价值边际不足时的下注检查"""
        decision = BetDecision(
            match_id=1,
            bet_type=BetType.HOME,
            stake=Decimal("0.00"),
            confidence=0.5,
            implied_probability=0.45,
            model_probability=0.5,
            odds=Decimal("2.0"),
            value_edge=0.05,  # 小于配置的0.1阈值
        )

        assert not portfolio.can_place_bet(decision, datetime.now())

    def test_place_bet_success(self, portfolio):
        """测试成功下注"""
        initial_balance = portfolio.current_balance

        decision = BetDecision(
            match_id=1,
            bet_type=BetType.HOME,
            stake=Decimal("0.00"),
            confidence=0.5,
            implied_probability=0.3,
            model_probability=0.5,
            odds=Decimal("3.0"),
            value_edge=0.2,
        )

        result = portfolio.place_bet(decision)
        assert result is True
        assert portfolio.current_balance < initial_balance  # 下注后余额减少
        assert decision.match_id in portfolio.pending_bets
        assert portfolio.total_staked > Decimal("0.00")

    def test_place_bet_skip(self, portfolio):
        """测试跳过下注"""
        initial_balance = portfolio.current_balance

        decision = BetDecision(
            match_id=1,
            bet_type=BetType.SKIP,
            stake=Decimal("0.00"),
            confidence=0.0,
            implied_probability=0.0,
            model_probability=0.0,
            odds=Decimal("2.0"),
        )

        result = portfolio.place_bet(decision)
        assert result is True
        assert portfolio.current_balance == initial_balance  # 跳过下注余额不变
        assert portfolio.total_skips == 1

    def test_settle_bet_win(self, portfolio):
        """测试结算获胜下注"""
        initial_balance = portfolio.current_balance

        # 先下注
        decision = BetDecision(
            match_id=1,
            bet_type=BetType.HOME,
            stake=Decimal("500.00"),
            confidence=0.5,
            implied_probability=0.3,
            model_probability=0.5,
            odds=Decimal("3.0"),
            value_edge=0.2,
        )
        portfolio.place_bet(decision)

        # 结算获胜
        result = portfolio.settle_bet(1, BetOutcome.HOME_WIN)
        assert result is not None
        assert result.profit_loss > 0  # 应该有盈利
        assert result.is_correct is True
        assert portfolio.current_balance > initial_balance  # 余额应该增加
        assert portfolio.total_wins == 1

    def test_settle_bet_lose(self, portfolio):
        """测试结算失败下注"""
        initial_balance = portfolio.current_balance

        # 先下注
        decision = BetDecision(
            match_id=1,
            bet_type=BetType.HOME,
            stake=Decimal("500.00"),
            confidence=0.5,
            implied_probability=0.3,
            model_probability=0.5,
            odds=Decimal("3.0"),
            value_edge=0.2,
        )
        portfolio.place_bet(decision)

        # 结算失败
        result = portfolio.settle_bet(1, BetOutcome.AWAY_WIN)
        assert result is not None
        assert result.profit_loss < 0  # 应该有亏损
        assert result.is_correct is False
        assert portfolio.current_balance < initial_balance  # 余额应该减少
        assert portfolio.total_losses == 1

    def test_settle_bet_not_found(self, portfolio):
        """测试结算不存在的下注"""
        result = portfolio.settle_bet(999, BetOutcome.HOME_WIN)
        assert result is None

    def test_get_statistics(self, portfolio):
        """测试获取统计信息"""
        # 模拟一些下注
        for i in range(3):
            decision = BetDecision(
                match_id=i,
                bet_type=BetType.HOME,
                stake=Decimal("100.00"),
                confidence=0.5,
                implied_probability=0.3,
                model_probability=0.5,
                odds=Decimal("2.5"),
                value_edge=0.1,
            )
            portfolio.place_bet(decision)

        # 结算前两个为赢，最后一个为输
        portfolio.settle_bet(0, BetOutcome.HOME_WIN)
        portfolio.settle_bet(1, BetOutcome.HOME_WIN)
        portfolio.settle_bet(2, BetOutcome.DRAW)

        stats = portfolio.get_statistics()
        assert stats["total_bets"] == 3
        assert stats["total_wins"] == 2
        assert stats["total_losses"] == 1
        assert stats["win_rate"] == pytest.approx(2 / 3)
        assert stats["roi_percent"] > 0  # 应该有正ROI

    def test_reset(self, portfolio):
        """测试重置功能"""
        # 模拟一些活动
        decision = BetDecision(
            match_id=1,
            bet_type=BetType.HOME,
            stake=Decimal("100.00"),
            confidence=0.5,
            implied_probability=0.3,
            model_probability=0.5,
            odds=Decimal("2.5"),
            value_edge=0.1,
        )
        portfolio.place_bet(decision)
        portfolio.total_skips = 5

        # 重置
        portfolio.reset()

        # 验证重置状态
        assert portfolio.current_balance == portfolio.initial_balance
        assert portfolio.total_staked == Decimal("0.00")
        assert portfolio.total_wins == 0
        assert portfolio.total_losses == 0
        assert portfolio.total_skips == 0
        assert len(portfolio.bet_history) == 0
        assert len(portfolio.pending_bets) == 0

    def test_balance_history(self, portfolio):
        """测试余额历史"""
        # 添加一些下注记录
        for i in range(3):
            decision = BetDecision(
                match_id=i,
                bet_type=BetType.HOME,
                stake=Decimal("100.00"),
                confidence=0.5,
                implied_probability=0.3,
                model_probability=0.5,
                odds=Decimal("2.5"),
                value_edge=0.1,
            )
            portfolio.place_bet(decision)
            portfolio.settle_bet(
                i, BetOutcome.HOME_WIN if i % 2 == 0 else BetOutcome.AWAY_WIN
            )

        history = portfolio.get_balance_history()
        assert len(history) > 1  # 应该包含初始余额和变化记录
        assert history[0]["event"] == "initial"
        assert all(isinstance(h["balance"], Decimal) for h in history)
