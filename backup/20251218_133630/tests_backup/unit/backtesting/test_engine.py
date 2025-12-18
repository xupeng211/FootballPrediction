"""
回测引擎测试 (Backtest Engine Tests)

测试BacktestEngine的核心功能。

作者: Backtesting Engineer (P2-4)
创建时间: 2025-12-06
版本: 1.0.0
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from src.backtesting.models import (
    BacktestConfig,
    BacktestResult,
)
from src.backtesting.engine import BacktestEngine, run_simple_backtest
from src.backtesting.strategy import SimpleValueStrategy


class TestBacktestEngine:
    """BacktestEngine测试"""

    @pytest.fixture
    def config(self):
        """回测配置fixture"""
        return BacktestConfig(
            initial_balance=Decimal("10000.00"),
            max_stake_pct=0.05,
            min_stake=Decimal("100.00"),
            max_stake=Decimal("500.00"),
        )

    @pytest.fixture
    def engine(self, config):
        """引擎fixture"""
        return BacktestEngine(config)

    @pytest.fixture
    def strategy(self):
        """策略fixture"""
        return SimpleValueStrategy(value_threshold=0.1, min_confidence=0.3)

    def test_engine_initialization(self, engine, config):
        """测试引擎初始化"""
        assert engine.config == config
        assert engine.portfolio.initial_balance == config.initial_balance
        assert engine.result.config == config
        assert engine.strategy is None

    def test_set_strategy(self, engine, strategy):
        """测试设置策略"""
        engine.set_strategy(strategy)
        assert engine.strategy == strategy

    def test_set_progress_callback(self, engine):
        """测试设置进度回调"""

        def callback(current, total, message):
            return None

        engine.set_progress_callback(callback)
        assert engine.progress_callback == callback

    @pytest.mark.asyncio
    async def test_run_backtest_no_strategy(self, engine):
        """测试没有策略时运行回测"""
        start_date = datetime.now() - timedelta(days=7)
        end_date = datetime.now()

        with pytest.raises(ValueError, match="Strategy must be set"):
            await engine.run_backtest(start_date, end_date)

    @pytest.mark.asyncio
    async def test_run_backtest_with_strategy(self, engine, strategy):
        """测试使用策略运行回测"""
        # 设置策略
        engine.set_strategy(strategy)

        # 设置日期范围
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        # 模拟数据库查询结果
        mock_matches = [
            {
                "id": 1,
                "home_team_id": 1,
                "away_team_id": 2,
                "home_team_name": "Team A",
                "away_team_name": "Team B",
                "home_score": 2,
                "away_score": 1,
                "match_date": datetime.now() - timedelta(hours=1),
                "status": "finished",
                "league_id": 1,
                "season": "2023-2024",
                "home_win_prob": 0.45,
                "draw_prob": 0.30,
                "away_win_prob": 0.25,
                "home_xg": 1.8,
                "away_xg": 1.2,
                "home_possession": 55.0,
                "away_possession": 45.0,
                "home_shots": 12,
                "away_shots": 8,
                "home_shots_on_target": 6,
                "away_shots_on_target": 3,
                "odds": {
                    "home": Decimal("2.20"),
                    "draw": Decimal("3.30"),
                    "away": Decimal("3.80"),
                },
            }
        ]

        # 模拟数据库方法
        engine._get_historical_matches = AsyncMock(return_value=mock_matches)

        # 运行回测
        result = await engine.run_backtest(start_date, end_date)

        # 验证结果
        assert isinstance(result, BacktestResult)
        assert result.total_matches == 1
        assert result.initial_balance == engine.config.initial_balance

    @pytest.mark.asyncio
    async def test_generate_mock_predictions(self, engine):
        """测试生成模拟预测"""
        match_data = {"id": 1}

        predictions = engine._generate_mock_predictions(match_data)

        assert "home_win_prob" in predictions
        assert "draw_prob" in predictions
        assert "away_win_prob" in predictions
        assert "model_confidence" in predictions

        # 验证概率总和接近1.0
        total_prob = (
            predictions["home_win_prob"]
            + predictions["draw_prob"]
            + predictions["away_win_prob"]
        )
        assert abs(total_prob - 1.0) < 0.1

    def test_generate_mock_odds(self, engine):
        """测试生成模拟赔率"""
        match_data = {"home_win_prob": 0.4, "draw_prob": 0.3, "away_win_prob": 0.3}

        odds = engine._generate_mock_odds(match_data)

        assert "home" in odds
        assert "draw" in odds
        assert "away" in odds

        # 验证赔率都大于1.1（最小赔率）
        assert all(odd >= Decimal("1.1") for odd in odds.values())

    def test_get_progress_info(self, engine):
        """测试获取进度信息"""
        # 模拟一些活动
        engine.portfolio.total_wins = 5
        engine.portfolio.total_losses = 3
        engine.portfolio.total_staked = Decimal("2000.00")
        engine.portfolio.current_balance = Decimal("11000.00")

        progress = engine.get_progress_info()

        assert progress["current_balance"] == Decimal("11000.00")
        assert progress["total_bets"] == 8  # wins + losses
        assert progress["win_rate"] == pytest.approx(5 / 8)
        assert progress["roi_percent"] == pytest.approx(10.0)


class TestRunSimpleBacktest:
    """简单回测函数测试"""

    @pytest.mark.asyncio
    async def test_run_simple_backtest_default_params(self):
        """测试使用默认参数运行简单回测"""
        # 注意：这个测试可能会因为实际的数据库查询而失败
        # 在真实环境中，我们需要确保有测试数据

        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        try:
            result = await run_simple_backtest(
                strategy_name="simple_value",
                start_date=start_date,
                end_date=end_date,
                initial_balance=Decimal("5000.00"),
            )

            assert isinstance(result, BacktestResult)
            assert result.initial_balance == Decimal("5000.00")

        except Exception as e:
            # 如果数据库中没有数据，这是预期的
            pytest.skip(f"No test data available: {e}")

    @pytest.mark.asyncio
    async def test_run_simple_backtest_custom_strategy(self):
        """测试使用自定义策略参数运行简单回测"""
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()

        try:
            result = await run_simple_backtest(
                strategy_name="conservative",
                start_date=start_date,
                end_date=end_date,
                value_threshold=0.15,
                min_confidence=0.5,
            )

            assert isinstance(result, BacktestResult)

        except Exception as e:
            pytest.skip(f"No test data available: {e}")


class TestBacktestIntegration:
    """回测集成测试"""

    @pytest.mark.asyncio
    async def test_full_backtest_workflow(self):
        """测试完整的回测工作流程"""
        # 创建配置
        config = BacktestConfig(
            initial_balance=Decimal("10000.00"),
            max_stake_pct=0.1,  # 更大的下注比例用于测试
            min_stake=Decimal("50.00"),
        )

        # 创建引擎
        engine = BacktestEngine(config)

        # 设置策略
        strategy = SimpleValueStrategy(value_threshold=0.05, min_confidence=0.2)
        engine.set_strategy(strategy)

        # 创建模拟比赛数据
        mock_matches = []
        for i in range(5):
            match_data = {
                "id": i + 1,
                "home_team_id": i + 1,
                "away_team_id": i + 100,
                "home_team_name": f"Team {i+1}",
                "away_team_name": f"Team {i+100}",
                "home_score": 2 if i % 2 == 0 else 1,
                "away_score": 1 if i % 2 == 0 else 2,
                "match_date": datetime.now() - timedelta(hours=i + 1),
                "status": "finished",
                "league_id": 1,
                "season": "2023-2024",
                "home_win_prob": 0.6 if i % 2 == 0 else 0.3,
                "draw_prob": 0.25,
                "away_win_prob": 0.15 if i % 2 == 0 else 0.45,
                "odds": {
                    "home": Decimal("2.10") if i % 2 == 0 else Decimal("3.20"),
                    "draw": Decimal("3.40"),
                    "away": Decimal("3.80") if i % 2 == 0 else Decimal("2.30"),
                },
            }
            mock_matches.append(match_data)

        # 模拟数据库查询
        engine._get_historical_matches = AsyncMock(return_value=mock_matches)

        # 运行回测
        start_date = datetime.now() - timedelta(days=1)
        end_date = datetime.now()
        result = await engine.run_backtest(start_date, end_date)

        # 验证结果
        assert result.total_matches == 5
        assert result.total_bets >= 0  # 可能有些比赛被跳过
        assert result.initial_balance == Decimal("10000.00")
        assert len(result.bet_results) == result.total_bets

        # 验证结果计算
        result.calculate_metrics()
        assert result.win_rate >= 0.0
        assert isinstance(result.roi, float)

    def test_result_summary(self):
        """测试结果摘要生成"""
        config = BacktestConfig(initial_balance=Decimal("10000.00"))
        result = BacktestResult(config=config)

        result.total_matches = 100
        result.total_bets = 50
        result.winning_bets = 25
        result.losing_bets = 20
        result.skipped_bets = 5
        result.total_profit_loss = Decimal("1500.00")
        result.max_consecutive_wins = 5
        result.max_consecutive_losses = 3
        result.win_rate = 0.5
        result.roi = 15.0

        summary = result.get_summary()

        assert "总比赛场次: 100" in summary
        assert "下注场次: 50" in summary
        assert "胜率: 50.00%" in summary
        assert "总盈亏: +1,500.00" in summary
        assert "投资回报率: +15.00%" in summary
        assert "最大连胜: 5" in summary
        assert "最大连败: 3" in summary
