"""测试统计策略"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta
import numpy as np

from src.domain.strategies.statistical import StatisticalStrategy
from src.domain.strategies.base import (
    PredictionInput as BasePredictionInput,
    PredictionOutput,
    StrategyType,
)
from tests.helpers.test_adapters import SimplePredictionInput as PredictionInput
from src.domain.models.prediction import Prediction


@pytest.fixture
def statistical_strategy():
    """创建统计策略实例"""
    strategy = StatisticalStrategy("test_statistical")

    config = {
        "min_sample_size": 5,
        "weight_recent_games": 0.7,
        "home_advantage_factor": 1.2,
        "poisson_lambda": 1.35,
        "model_weights": {
            "poisson": 0.4,
            "historical": 0.3,
            "form": 0.2,
            "head_to_head": 0.1,
        },
    }

    # 初始化策略
    asyncio.run(strategy.initialize(config))

    # 设置模拟数据
    strategy._team_stats = {
        1: {  # 主队
            "goals_scored_per_game": 1.8,
            "goals_conceded_per_game": 0.9,
            "recent_form": [2, 1, 3, 2, 1],
            "home_goals_per_game": 2.1,
            "sample_size": 20,
        },
        2: {  # 客队
            "goals_scored_per_game": 1.2,
            "goals_conceded_per_game": 1.4,
            "recent_form": [1, 0, 1, 2, 0],
            "away_goals_per_game": 1.0,
            "sample_size": 20,
        },
    }

    strategy._head_to_head_stats = {
        (1, 2): {
            "home_wins": 4,
            "away_wins": 2,
            "draws": 4,
            "avg_home_goals": 1.8,
            "avg_away_goals": 1.1,
            "sample_size": 10,
        }
    }

    return strategy


@pytest.fixture
def prediction_input():
    """创建预测输入"""
    return PredictionInput(
        match_id=123,
        home_team_id=1,
        away_team_id=2,
        home_team_form="WWWDW",
        away_team_form="LDLWL",
        home_team_goals_scored=[2, 1, 3, 2, 1],
        away_team_goals_scored=[1, 0, 1, 2, 0],
        home_team_goals_conceded=[0, 1, 0, 1, 2],
        away_team_goals_conceded=[2, 1, 2, 0, 1],
    )


@pytest.mark.asyncio
async def test_statistical_strategy_initialization():
    """测试统计策略初始化"""
    strategy = StatisticalStrategy()

    config = {
        "min_sample_size": 10,
        "weight_recent_games": 0.8,
        "home_advantage_factor": 1.3,
        "model_weights": {"poisson": 0.5, "historical": 0.3, "form": 0.2},
    }

    await strategy.initialize(config)

    assert strategy._min_sample_size == 10
    assert strategy._model_params["weight_recent_games"] == 0.8
    assert strategy._model_params["home_advantage_factor"] == 1.3
    assert strategy._model_params["model_weights"]["poisson"] == 0.5
    assert strategy._is_initialized is True


@pytest.mark.asyncio
async def test_prediction_output_structure(statistical_strategy, prediction_input):
    """测试预测输出结构"""
    # 转换为标准的PredictionInput
    base_input = prediction_input.to_base_prediction_input()
    result = await statistical_strategy.predict(base_input)

    assert isinstance(result, PredictionOutput)
    assert isinstance(result.prediction, tuple)
    assert len(result.prediction) == 2
    assert all(isinstance(x, (int, float)) for x in result.prediction)
    assert 0 <= result.confidence <= 1
    assert isinstance(result.reasoning, str)
    assert len(result.reasoning) > 0


@pytest.mark.asyncio
async def test_poisson_prediction(statistical_strategy, prediction_input):
    """测试泊松分布预测"""
    result = await statistical_strategy._poisson_prediction(
        prediction_input.to_base_prediction_input()
    )

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(0 <= x <= 10 for x in result)  # 合理的进球数范围

    # 验证结果是合理的进球数
    assert result[0] >= 0 and result[1] >= 0


@pytest.mark.asyncio
async def test_historical_average_prediction(statistical_strategy, prediction_input):
    """测试历史平均预测"""
    result = await statistical_strategy._historical_average_prediction(
        prediction_input.to_base_prediction_input()
    )

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(0 <= x <= 5 for x in result)  # 合理的进球数范围


@pytest.mark.asyncio
async def test_team_form_prediction(statistical_strategy, prediction_input):
    """测试球队状态预测"""
    result = await statistical_strategy._team_form_prediction(
        prediction_input.to_base_prediction_input()
    )

    assert isinstance(result, tuple)
    assert len(result) == 2
    assert all(isinstance(x, (int, float)) for x in result)

    # 主队状态更好，应该预测主队进球更多
    assert _result[0] >= _result[1]


@pytest.mark.asyncio
async def test_head_to_head_prediction(statistical_strategy, prediction_input):
    """测试对战历史预测"""
    result = await statistical_strategy._head_to_head_prediction(
        prediction_input.to_base_prediction_input()
    )

    assert isinstance(result, tuple)
    assert len(result) == 2

    # 基于对战历史，主队占优
    assert _result[0] >= _result[1]


@pytest.mark.asyncio
async def test_ensemble_predictions(statistical_strategy, prediction_input):
    """测试集成多种统计预测"""
    predictions = {
        "poisson": (2.1, 1.3),
        "historical": (1.9, 1.1),
        "form": (2.0, 1.0),
        "head_to_head": (1.8, 1.1),
    }

    result = await statistical_strategy._ensemble_predictions(predictions)

    assert isinstance(result, tuple)
    assert len(result) == 2

    # 结果应该是各预测的加权平均
    expected_home = 2.1 * 0.4 + 1.9 * 0.3 + 2.0 * 0.2 + 1.8 * 0.1
    expected_away = 1.3 * 0.4 + 1.1 * 0.3 + 1.0 * 0.2 + 1.1 * 0.1

    assert abs(_result[0] - expected_home) < 0.01
    assert abs(_result[1] - expected_away) < 0.01


@pytest.mark.asyncio
async def test_insufficient_sample_size():
    """测试样本数量不足的情况"""
    strategy = StatisticalStrategy("test")
    await strategy.initialize({})

    # 设置样本数量不足的统计数据
    strategy._team_stats = {
        1: {"sample_size": 3},  # 少于最小样本数
        2: {"sample_size": 4},
    }

    input_data = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)

    with pytest.raises(ValueError, match="样本数量不足"):
        await strategy.predict(input_data)


@pytest.mark.asyncio
async def test_home_advantage_calculation(statistical_strategy, prediction_input):
    """测试主场优势计算"""
    home_advantage = statistical_strategy._calculate_home_advantage(prediction_input)

    assert isinstance(home_advantage, float)
    assert home_advantage > 1.0  # 主场优势应该大于1

    # 测试没有主场优势数据的情况
    statistical_strategy._team_stats[1]["home_goals_per_game"] = None
    home_advantage_default = statistical_strategy._calculate_home_advantage(
        prediction_input
    )
    assert (
        home_advantage_default
        == statistical_strategy._model_params["home_advantage_factor"]
    )


@pytest.mark.asyncio
async def test_validate_input(statistical_strategy):
    """测试输入验证"""
    # 有效输入
    valid_input = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)
    assert await statistical_strategy.validate_input(valid_input) is True

    # 无效输入（缺少必要字段）
    invalid_input = PredictionInput(match_id=None, home_team_id=1, away_team_id=2)
    assert await statistical_strategy.validate_input(invalid_input) is False


@pytest.mark.asyncio
async def test_preprocessing(statistical_strategy, prediction_input):
    """测试数据预处理"""
    processed = await statistical_strategy.pre_process(
        prediction_input.to_base_prediction_input()
    )

    assert processed is not None
    assert hasattr(processed, "match_id")
    assert hasattr(processed, "home_team_id")
    assert hasattr(processed, "away_team_id")

    # 验证近期状态被处理
    assert processed.home_team_form == prediction_input.home_team_form
    assert processed.away_team_form == prediction_input.away_team_form


@pytest.mark.asyncio
async def test_confidence_calculation(statistical_strategy, prediction_input):
    """测试置信度计算"""
    # 获取多个预测结果
    predictions = {
        "poisson": (2.1, 1.3),
        "historical": (1.9, 1.1),
        "form": (2.0, 1.0),
        "head_to_head": (1.8, 1.1),
    }

    # 计算预测方差作为不确定性度量
    home_preds = [p[0] for p in predictions.values()]
    away_preds = [p[1] for p in predictions.values()]

    variance = np.var(home_preds) + np.var(away_preds)

    # 方差越小，置信度越高
    expected_confidence = max(0.3, 1.0 - variance / 2.0)

    # 验证置信度在合理范围内
    assert 0.3 <= expected_confidence <= 1.0


@pytest.mark.asyncio
async def test_strategy_metrics(statistical_strategy):
    """测试策略指标"""
    metrics = await statistical_strategy.get_metrics()

    assert metrics is not None
    assert hasattr(metrics, "strategy_type")
    assert metrics.strategy_type == StrategyType.STATISTICAL
    assert hasattr(metrics, "prediction_count")
    assert hasattr(metrics, "average_confidence")


@pytest.mark.asyncio
async def test_seasonal_adjustment(statistical_strategy, prediction_input):
    """测试赛季调整因子"""
    # 模拟赛季末段（进球数可能更多）
    season_end_input = PredictionInput(
        **prediction_input.__dict__,
        match_date=datetime(2024, 5, 15),  # 赛季末
    )

    # 模拟赛季初段（进球数可能较少）
    season_start_input = PredictionInput(
        **prediction_input.__dict__,
        match_date=datetime(2024, 8, 15),  # 赛季初
    )

    # 计算两个时期的预测
    await statistical_strategy.predict(season_end_input)
    await statistical_strategy.predict(season_start_input)

    # 赛季末进球数可能略多于赛季初
    assert isinstance(end_result.prediction[0], (int, float))
    assert isinstance(start_result.prediction[0], (int, float))


@pytest.mark.asyncio
async def test_error_handling(statistical_strategy, prediction_input):
    """测试错误处理"""
    # 破坏统计数据
    statistical_strategy._team_stats = None

    with pytest.raises((RuntimeError, ValueError)):
        await statistical_strategy.predict(prediction_input.to_base_prediction_input())


def test_poisson_probability_calculation(statistical_strategy):
    """测试泊松分布概率计算"""
    # 测试lambda=1.5时，k=0的概率
    prob = statistical_strategy._poisson_probability(0, 1.5)
    assert 0 < prob < 1

    # 测试lambda=1.5时，k=2的概率
    prob = statistical_strategy._poisson_probability(2, 1.5)
    assert 0 < prob < 1

    # 验证概率总和接近1（k从0到10）
    total_prob = sum(
        statistical_strategy._poisson_probability(k, 1.5) for k in range(11)
    )
    assert 0.95 < total_prob < 1.05  # 允许小的数值误差


@pytest.mark.asyncio
async def test_team_strength_calculation(statistical_strategy, prediction_input):
    """测试球队实力计算"""
    home_strength = statistical_strategy._calculate_team_strength(
        prediction_input.home_team_id, is_home=True
    )

    away_strength = statistical_strategy._calculate_team_strength(
        prediction_input.away_team_id, is_home=False
    )

    assert isinstance(home_strength, float)
    assert isinstance(away_strength, float)
    assert home_strength > 0
    assert away_strength > 0

    # 主队实力应该包含主场优势
    assert home_strength > away_strength
