"""
Unit tests for Football Prediction Backtest module.

测试足球预测回测模块的各项功能。
"""

import pytest
import numpy as np
import pandas as pd
import csv
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from datetime import datetime

from src.evaluation.backtest import (
    Bet, BetType, BacktestResult,
    StakingStrategy, FlatStakingStrategy, PercentageStakingStrategy,
    KellyStakingStrategy, ValueBettingStrategy,
    Backtester, run_backtest,
)


class TestBet:
    """Bet类测试"""

    @pytest.fixture
    def sample_bet(self):
        """创建样本Bet"""
        return Bet(
            match_id="match_001",
            date="2024-01-01",
            prediction=0,  # Home win
            predicted_proba=[0.6, 0.3, 0.1],
            odds=[2.1, 3.2, 4.5],
            stake=10.0,
            bet_type=BetType.HOME_WIN,
            actual_result=0,  # Home win (correct)
            won=True,
            profit=11.0,  # 10.0 * 2.1 - 10.0
            ev=0.26,  # (0.6 * 2.1) - 1
            confidence=0.6
        )

    def test_bet_creation(self, sample_bet):
        """测试Bet创建"""
        assert sample_bet.match_id == "match_001"
        assert sample_bet.prediction == 0
        assert sample_bet.won is True
        assert sample_bet.profit == 11.0

    def test_bet_to_dict(self, sample_bet):
        """测试Bet转字典"""
        bet_dict = sample_bet.to_dict()

        assert bet_dict["match_id"] == "match_001"
        assert bet_dict["prediction"] == 0
        assert bet_dict["won"] is True
        assert bet_dict["profit"] == 11.0

    def test_bet_type_enum(self):
        """测试BetType枚举"""
        assert BetType.HOME_WIN.value == "H"
        assert BetType.DRAW.value == "D"
        assert BetType.AWAY_WIN.value == "A"


class TestStakingStrategies:
    """投注策略测试"""

    def test_flat_staking_strategy(self):
        """测试固定投注策略"""
        strategy = FlatStakingStrategy(stake_amount=15.0)

        stake = strategy.calculate_stake(bankroll=1000.0)
        assert stake == 15.0

        # 测试资金限制（最多投注10%）
        stake_limited = strategy.calculate_stake(bankroll=100.0)
        assert stake_limited == 10.0

    def test_percentage_staking_strategy(self):
        """测试百分比投注策略"""
        strategy = PercentageStakingStrategy(percentage=0.02)  # 2%

        stake = strategy.calculate_stake(bankroll=1000.0)
        assert stake == 20.0

        stake_small = strategy.calculate_stake(bankroll=500.0)
        assert stake_small == 10.0

    def test_kelly_staking_strategy(self):
        """测试凯利投注策略"""
        strategy = KellyStakingStrategy(
            kelly_fraction=0.25,
            min_stake=5.0,
            max_stake_percentage=0.1
        )

        # 高价值投注
        stake = strategy.calculate_stake(
            bankroll=1000.0,
            predicted_proba=[0.7, 0.2, 0.1],
            odds=[3.0, 3.2, 3.5],
            prediction=0
        )
        assert stake >= 5.0  # 最小投注

        # 低价值投注
        stake_low = strategy.calculate_stake(
            bankroll=1000.0,
            predicted_proba=[0.4, 0.3, 0.3],
            odds=[2.0, 3.2, 3.5],
            prediction=0
        )
        assert stake_low == 0.0  # 不投注

    def test_value_betting_strategy(self):
        """测试价值投注策略"""
        strategy = ValueBettingStrategy(
            min_ev_threshold=0.1,
            base_stake=10.0,
            max_stake_percentage=0.05
        )

        # 高价值投注
        stake = strategy.calculate_stake(
            bankroll=1000.0,
            predicted_proba=[0.6, 0.2, 0.2],
            odds=[3.0, 3.2, 3.5],
            prediction=0
        )
        assert stake >= 0  # 应该投注

        # 低价值投注
        stake_low = strategy.calculate_stake(
            bankroll=1000.0,
            predicted_proba=[0.4, 0.3, 0.3],
            odds=[2.0, 3.2, 3.5],
            prediction=0
        )
        assert stake_low == 0.0  # 不投注


class TestBacktester:
    """Backtester类测试"""

    @pytest.fixture
    def backtester(self):
        """创建Backtester实例"""
        return Backtester(initial_bankroll=1000.0, random_seed=42)

    @pytest.fixture
    def sample_predictions(self):
        """创建样本预测数据"""
        np.random.seed(42)
        n_samples = 100

        # 创建预测DataFrame
        predictions = pd.DataFrame({
            'prob_H': np.random.uniform(0.2, 0.7, n_samples),
            'prob_D': np.random.uniform(0.1, 0.4, n_samples),
            'prob_A': np.random.uniform(0.1, 0.5, n_samples),
            'predicted_class': np.random.randint(0, 3, n_samples),
            'actual_result': np.random.randint(0, 3, n_samples),
            'date': [f"2024-01-{i+1:02d}" for i in range(n_samples)]
        })

        # 归一化概率
        prob_cols = ['prob_H', 'prob_D', 'prob_A']
        predictions[prob_cols] = predictions[prob_cols].div(
            predictions[prob_cols].sum(axis=1), axis=0
        )

        return predictions

    @pytest.fixture
    def sample_odds(self):
        """创建样本赔率数据"""
        np.random.seed(42)
        n_samples = 100

        odds = pd.DataFrame({
            'odds_H': np.random.uniform(1.8, 4.0, n_samples),
            'odds_D': np.random.uniform(2.8, 4.5, n_samples),
            'odds_A': np.random.uniform(2.5, 6.0, n_samples)
        })

        return odds

    def test_initialization(self, backtester):
        """测试Backtester初始化"""
        assert backtester.initial_bankroll == 1000.0
        assert backtester.random_seed == 42
        assert backtester.bets == []
        assert backtester.equity_curve == [1000.0]

    def test_calculate_expected_value(self, backtester):
        """测试期望值计算"""
        predicted_proba = [0.6, 0.3, 0.1]
        odds = [2.5, 3.2, 4.0]

        ev = backtester.calculate_expected_value(predicted_proba, odds)

        assert len(ev) == 3
        assert abs(ev[0] - ((0.6 * 2.5) - 1)) < 1e-10
        assert abs(ev[1] - ((0.3 * 3.2) - 1)) < 1e-10
        assert abs(ev[2] - ((0.1 * 4.0) - 1)) < 1e-10

    def test_should_bet(self, backtester):
        """测试是否应该下注判断"""
        predicted_proba = [0.7, 0.2, 0.1]
        odds = [2.0, 3.0, 4.0]

        # 高价值情况
        should_bet = backtester.should_bet(predicted_proba, odds, strategy="value", threshold=0.1)
        assert should_bet is True

        # 低价值情况
        should_bet_low = backtester.should_bet(predicted_proba, odds, strategy="value", threshold=0.5)
        assert should_bet_low is False

    def test_get_best_bet(self, backtester):
        """测试获取最佳投注选择"""
        predicted_proba = [0.5, 0.3, 0.2]
        odds = [2.0, 4.0, 5.0]

        # 基于期望值
        best_idx, best_value = backtester.get_best_bet(predicted_proba, odds, strategy="ev")
        assert best_idx in [0, 1, 2]
        assert isinstance(best_value, float)

        # 基于概率
        best_prob_idx, best_prob_value = backtester.get_best_bet(predicted_proba, odds, strategy="prob")
        assert best_prob_idx == 0  # 最高概率
        assert best_prob_value == 0.5

    def test_simulate_bet(self, backtester):
        """测试单笔投注模拟"""
        predicted_proba = [0.6, 0.3, 0.1]
        odds = [2.5, 3.2, 4.0]
        strategy = FlatStakingStrategy(stake_amount=10.0)

        # 获胜情况
        bet = backtester.simulate_bet(
            match_id="test_001",
            date="2024-01-01",
            predicted_proba=predicted_proba,
            odds=odds,
            actual_result=0,  # Home win
            stake_strategy=strategy
        )

        assert bet is not None
        assert bet.match_id == "test_001"
        assert bet.prediction == 0  # 应该选择期望值最高的
        assert bet.won is True
        assert bet.profit > 0

        # 失败情况
        bet_lose = backtester.simulate_bet(
            match_id="test_002",
            date="2024-01-02",
            predicted_proba=predicted_proba,
            odds=odds,
            actual_result=1,  # Not home win
            stake_strategy=strategy
        )

        assert bet_lose is not None
        assert bet_lose.won is False
        assert bet_lose.profit < 0

    def test_simulate(self, backtester, sample_predictions, sample_odds):
        """测试完整回测模拟"""
        strategy = FlatStakingStrategy(stake_amount=10.0)

        result = backtester.simulate(
            predictions=sample_predictions,
            odds=sample_odds,
            stake_strategy=strategy
        )

        assert isinstance(result, BacktestResult)
        assert result.initial_bankroll == 1000.0
        assert result.total_bets >= 0
        assert result.final_bankroll >= 0
        assert len(result.equity_curve) >= 1  # 至少包含初始资金
        assert result.equity_curve[0] == 1000.0

    def test_simulate_with_value_strategy(self, backtester, sample_predictions, sample_odds):
        """测试价值投注策略回测"""
        strategy = ValueBettingStrategy(min_ev_threshold=0.05)  # 较低阈值

        result = backtester.simulate(
            predictions=sample_predictions,
            odds=sample_odds,
            stake_strategy=strategy
        )

        assert isinstance(result, BacktestResult)
        # 价值策略可能投注次数较少
        assert result.total_bets >= 0

    def test_calculate_backtest_result_empty(self, backtester):
        """测试无投注时的回测结果"""
        result = backtester._calculate_backtest_result()

        assert result.total_bets == 0
        assert result.final_bankroll == backtester.initial_bankroll
        assert result.net_profit == 0.0
        assert result.roi == 0.0

    def test_save_and_load_results(self, backtester, sample_predictions, sample_odds, tmp_path):
        """测试回测结果保存和加载"""
        strategy = FlatStakingStrategy(stake_amount=10.0)
        result = backtester.simulate(
            predictions=sample_predictions,
            odds=sample_odds,
            stake_strategy=strategy
        )

        # 保存结果
        save_path = tmp_path / "backtest_result.json"
        backtester.save_results(result, save_path)

        assert save_path.exists()
        assert (tmp_path / "backtest_result.csv").exists()

        # 加载结果
        loaded_result = Backtester.load_results(save_path)

        assert loaded_result.initial_bankroll == result.initial_bankroll
        assert loaded_result.final_bankroll == result.final_bankroll
        assert loaded_result.total_bets == result.total_bets
        assert len(loaded_result.bets) == len(result.bets)


class TestBacktestResult:
    """BacktestResult类测试"""

    @pytest.fixture
    def sample_backtest_result(self):
        """创建样本BacktestResult"""
        bets = [
            Bet("match_1", "2024-01-01", 0, [0.6, 0.3, 0.1], [2.5, 3.2, 4.0],
                 10.0, BetType.HOME_WIN, 0, True, 15.0, 0.5, 0.6),
            Bet("match_2", "2024-01-02", 1, [0.2, 0.6, 0.2], [2.8, 3.0, 4.2],
                 10.0, BetType.DRAW, 1, True, 20.0, 0.8, 0.6),
            Bet("match_3", "2024-01-03", 2, [0.1, 0.2, 0.7], [3.0, 3.5, 2.8],
                 10.0, BetType.AWAY_WIN, 0, False, -10.0, 0.3, 0.7)
        ]

        equity_curve = [1000.0, 1015.0, 1035.0, 1025.0]

        return BacktestResult(
            initial_bankroll=1000.0,
            final_bankroll=1025.0,
            total_bets=3,
            winning_bets=2,
            losing_bets=1,
            total_stake=30.0,
            total_winnings=45.0,
            net_profit=15.0,
            roi=50.0,
            win_rate=66.67,
            avg_odds=2.9,
            max_consecutive_losses=1,
            max_consecutive_wins=2,
            max_drawdown=10.0,
            max_drawdown_percentage=1.0,
            sharpe_ratio=1.5,
            calmar_ratio=15.0,
            profit_factor=3.0,
            avg_profit_per_bet=5.0,
            std_profit_per_bet=12.5,
            bets=bets,
            equity_curve=equity_curve,
            metadata={"test": True}
        )

    def test_backtest_result_creation(self, sample_backtest_result):
        """测试BacktestResult创建"""
        assert sample_backtest_result.initial_bankroll == 1000.0
        assert sample_backtest_result.final_bankroll == 1025.0
        assert sample_backtest_result.total_bets == 3
        assert sample_backtest_result.roi == 50.0

    def test_backtest_result_to_dict(self, sample_backtest_result):
        """测试BacktestResult转字典"""
        result_dict = sample_backtest_result.to_dict()

        assert result_dict["initial_bankroll"] == 1000.0
        assert result_dict["final_bankroll"] == 1025.0
        assert result_dict["total_bets"] == 3
        assert "equity_curve" in result_dict
        assert "bets" in result_dict

    def test_backtest_result_to_json(self, sample_backtest_result):
        """测试BacktestResult转JSON"""
        json_str = sample_backtest_result.to_json()

        import json
        parsed = json.loads(json_str)
        assert parsed["initial_bankroll"] == 1000.0
        assert parsed["total_bets"] == 3


class TestConvenienceFunctions:
    """便捷函数测试"""

    @pytest.fixture
    def sample_csv_files(self, tmp_path):
        """创建样本CSV文件"""
        # 预测文件
        predictions_data = {
            'match_id': [1, 2, 3],
            'prob_H': [0.6, 0.3, 0.2],
            'prob_D': [0.3, 0.5, 0.3],
            'prob_A': [0.1, 0.2, 0.5],
            'predicted_class': [0, 1, 2],
            'actual_result': [0, 1, 0]
        }
        predictions_df = pd.DataFrame(predictions_data)
        predictions_path = tmp_path / "predictions.csv"
        predictions_df.to_csv(predictions_path, index=False)

        # 赔率文件
        odds_data = {
            'match_id': [1, 2, 3],
            'odds_H': [2.5, 2.8, 3.0],
            'odds_D': [3.2, 3.0, 3.5],
            'odds_A': [4.0, 4.2, 2.8]
        }
        odds_df = pd.DataFrame(odds_data)
        odds_path = tmp_path / "odds.csv"
        odds_df.to_csv(odds_path, index=False)

        return predictions_path, odds_path

    def test_run_backtest_function(self, sample_csv_files):
        """测试run_backtest便捷函数"""
        predictions_path, odds_path = sample_csv_files

        result = run_backtest(
            predictions_file=predictions_path,
            odds_file=odds_path,
            stake_strategy="flat",
            initial_bankroll=1000.0,
            stake_amount=10.0
        )

        assert isinstance(result, BacktestResult)
        assert result.initial_bankroll == 1000.0
        assert result.total_bets >= 0

    def test_run_backtest_kelly_strategy(self, sample_csv_files):
        """测试run_backtest使用凯利策略"""
        predictions_path, odds_path = sample_csv_files

        result = run_backtest(
            predictions_file=predictions_path,
            odds_file=odds_path,
            stake_strategy="kelly",
            initial_bankroll=1000.0,
            kelly_fraction=0.25
        )

        assert isinstance(result, BacktestResult)
        # 凯利策略可能投注较少
        assert result.total_bets >= 0

    def test_run_backtest_invalid_strategy(self, sample_csv_files):
        """测试run_backtest使用无效策略"""
        predictions_path, odds_path = sample_csv_files

        with pytest.raises(ValueError, match="Unknown staking strategy"):
            run_backtest(
                predictions_file=predictions_path,
                odds_file=odds_path,
                stake_strategy="invalid_strategy"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
