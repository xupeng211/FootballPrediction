"""测试集成策略"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
import numpy as np

from src.domain.strategies.ensemble import (
    EnsembleStrategy,
    EnsembleMethod,
    StrategyWeight,
    EnsembleResult,
)
from src.domain.strategies.base import (
    PredictionInput,
    PredictionOutput,
    StrategyType,
)
from src.domain.models.prediction import Prediction


@pytest.fixture
def mock_sub_strategies():
    """创建模拟的子策略"""
    strategies = {}

    # 历史策略 - 保守预测
    historical = MagicMock()
    historical.name = "historical"
    historical.type = StrategyType.HISTORICAL
    historical.predict = AsyncMock(
        return_value=PredictionOutput(
            predicted_home_score=1,
            predicted_away_score=0,
            confidence=0.75,
            metadata={"reasoning": "Historical analysis shows home advantage"},
        )
    )
    strategies["historical"] = historical

    # 统计策略 - 中等预测
    statistical = MagicMock()
    statistical.name = "statistical"
    statistical.type = StrategyType.STATISTICAL
    statistical.predict = AsyncMock(
        return_value=PredictionOutput(
            predicted_home_score=2,
            predicted_away_score=1,
            confidence=0.68,
            metadata={"reasoning": "Statistical models predict moderate win"},
        )
    )
    strategies["statistical"] = statistical

    # ML模型策略 - 激进预测
    ml_model = MagicMock()
    ml_model.name = "ml_model"
    ml_model.type = StrategyType.ML_MODEL
    ml_model.predict = AsyncMock(
        return_value=PredictionOutput(
            predicted_home_score=3,
            predicted_away_score=1,
            confidence=0.82,
            metadata={"reasoning": "ML model predicts strong win"},
        )
    )
    strategies["ml_model"] = ml_model

    return strategies


@pytest.fixture
def ensemble_strategy(mock_sub_strategies):
    """创建集成策略实例"""
    strategy = EnsembleStrategy("test_ensemble")

    # 手动添加子策略（避免异步初始化）
    for name, sub_strategy in mock_sub_strategies.items():
        strategy._sub_strategies[name] = sub_strategy
        strategy._strategy_weights[name] = StrategyWeight(
            strategy_name=name, base_weight=1.0 / len(mock_sub_strategies)
        )

    return strategy


@pytest.mark.asyncio
async def test_ensemble_strategy_initialization():
    """测试集成策略初始化"""
    strategy = EnsembleStrategy()

    _config = {
        "ensemble_method": "weighted_average",
        "consensus_threshold": 0.8,
        "max_disagreement": 1.5,
        "performance_window": 100,
        "sub_strategies": [
            {"name": "historical", "weight": 0.4},
            {"name": "statistical", "weight": 0.35},
            {"name": "ml_model", "weight": 0.25},
        ],
    }

    # Mock子策略初始化
    with patch.object(strategy, "_initialize_sub_strategies"):
        await strategy.initialize(_config)

    assert strategy._ensemble_method == EnsembleMethod.WEIGHTED_AVERAGE
    assert strategy._consensus_threshold == 0.8
    assert strategy._max_disagreement == 1.5
    assert strategy._performance_window == 100


@pytest.mark.asyncio
async def test_weighted_average_prediction(ensemble_strategy):
    """测试加权平均预测"""
    # 设置不同的权重
    ensemble_strategy._strategy_weights["historical"].base_weight = 0.4
    ensemble_strategy._strategy_weights["statistical"].base_weight = 0.35
    ensemble_strategy._strategy_weights["ml_model"].base_weight = 0.25

    # 创建输入
    input_data = PredictionInput(
        match_id=123,
        home_team_id=1,
        away_team_id=2,
        home_team_form="WWWW",
        away_team_form="LDWD",
    )

    # 预测
    _result = await ensemble_strategy.predict(input_data)

    # 验证结果
    assert isinstance(_result, PredictionOutput)
    assert hasattr(_result, 'predicted_home_score')
    assert hasattr(_result, 'predicted_away_score')
    assert 0 <= _result.confidence <= 1
    assert _result.metadata is not None
    assert _result.metadata.get("reasoning") is not None

    # 验证所有子策略都被调用
    for strategy in ensemble_strategy._sub_strategies.values():
        strategy.predict.assert_called_once_with(input_data)


@pytest.mark.asyncio
async def test_majority_voting_prediction(ensemble_strategy):
    """测试多数投票预测"""
    # 修改为多数投票方法
    ensemble_strategy._ensemble_method = EnsembleMethod.MAJORITY_VOTING

    # 修改子策略返回值以产生明确的多数
    ensemble_strategy._sub_strategies[
        "historical"
    ].predict.return_value = PredictionOutput(predicted_home_score=2, predicted_away_score=1, confidence=0.75, metadata={"reasoning": "Test"})
    ensemble_strategy._sub_strategies[
        "statistical"
    ].predict.return_value = PredictionOutput(predicted_home_score=2, predicted_away_score=1, confidence=0.68, metadata={"reasoning": "Test"})

    input_data = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)

    _result = await ensemble_strategy.predict(input_data)

    # 多数投票应该选择(2, 1)
    assert _result.predicted_home_score == 2
    assert _result.predicted_away_score == 1
    assert _result.confidence > 0.5  # 多数投票的置信度应该大于0.5


@pytest.mark.asyncio
async def test_dynamic_weighting(ensemble_strategy):
    """测试动态权重调整"""
    # 设置动态权重方法
    ensemble_strategy._ensemble_method = EnsembleMethod.DYNAMIC_WEIGHTING

    # 添加性能历史
    ensemble_strategy._performance_history = {
        "historical": [0.7, 0.75, 0.72, 0.78, 0.76],
        "statistical": [0.6, 0.65, 0.68, 0.64, 0.66],
        "ml_model": [0.8, 0.82, 0.79, 0.83, 0.81],
    }

    input_data = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)

    _result = await ensemble_strategy.predict(input_data)

    # 验证动态权重已调整
    assert isinstance(_result, PredictionOutput)

    # ML模型性能最好，应该有更高的权重
    ml_weight = ensemble_strategy._strategy_weights["ml_model"].performance_weight
    statistical_weight = ensemble_strategy._strategy_weights[
        "statistical"
    ].performance_weight

    assert ml_weight > statistical_weight


@pytest.mark.asyncio
async def test_consensus_score_calculation(ensemble_strategy):
    """测试共识分数计算"""
    # 所有策略给出相似预测
    ensemble_strategy._sub_strategies[
        "historical"
    ].predict.return_value = PredictionOutput(predicted_home_score=2, predicted_away_score=1, confidence=0.75, metadata={"reasoning": "Consensus test"})
    ensemble_strategy._sub_strategies[
        "statistical"
    ].predict.return_value = PredictionOutput(predicted_home_score=2, predicted_away_score=1, confidence=0.72, metadata={"reasoning": "Consensus test"})
    ensemble_strategy._sub_strategies[
        "ml_model"
    ].predict.return_value = PredictionOutput(predicted_home_score=2, predicted_away_score=1, confidence=0.78, metadata={"reasoning": "Consensus test"})

    input_data = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)

    _result = await ensemble_strategy.predict(input_data)

    # 高共识应该反映在结果中
    reasoning = _result.metadata.get("reasoning", "").lower()
    assert (
        "consensus" in reasoning
        or "agreement" in reasoning
    )


@pytest.mark.asyncio
async def test_disagreement_handling(ensemble_strategy):
    """测试分歧处理"""
    # 设置高度分歧的预测
    ensemble_strategy._sub_strategies[
        "historical"
    ].predict.return_value = PredictionOutput(predicted_home_score=1, predicted_away_score=0, confidence=0.8, metadata={"reasoning": "Disagreement test"})
    ensemble_strategy._sub_strategies[
        "statistical"
    ].predict.return_value = PredictionOutput(predicted_home_score=0, predicted_away_score=0, confidence=0.7, metadata={"reasoning": "Disagreement test"})
    ensemble_strategy._sub_strategies[
        "ml_model"
    ].predict.return_value = PredictionOutput(predicted_home_score=4, predicted_away_score=0, confidence=0.85, metadata={"reasoning": "Disagreement test"})

    input_data = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)

    _result = await ensemble_strategy.predict(input_data)

    # 高分歧应该降低置信度
    assert _result.confidence < 0.7  # 分歧时置信度应该降低
    reasoning = _result.metadata.get("reasoning", "").lower()
    assert (
        "disagreement" in reasoning
        or "uncertain" in reasoning
    )


@pytest.mark.asyncio
async def test_strategy_failure_handling(ensemble_strategy):
    """测试子策略失败处理"""
    # 让一个策略失败
    ensemble_strategy._sub_strategies["historical"].predict.side_effect = Exception(
        "Strategy failed"
    )

    input_data = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)

    # 应该仍然能够预测，使用剩余的策略
    _result = await ensemble_strategy.predict(input_data)

    assert isinstance(_result, PredictionOutput)
    assert hasattr(_result, 'predicted_home_score')
    assert hasattr(_result, 'predicted_away_score')
    reasoning = _result.metadata.get("reasoning", "")
    assert "historical" not in reasoning or "failed" in reasoning.lower()


@pytest.mark.asyncio
async def test_empty_sub_strategies():
    """测试没有子策略的情况"""
    strategy = EnsembleStrategy("empty_ensemble")

    input_data = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)

    with pytest.raises(ValueError, match="No sub-strategies available"):
        await strategy.predict(input_data)


@pytest.mark.asyncio
async def test_single_sub_strategy():
    """测试只有一个子策略的情况"""
    strategy = EnsembleStrategy("single_ensemble")

    # 添加一个子策略
    mock_strategy = MagicMock()
    mock_strategy.predict = AsyncMock(
        return_value=PredictionOutput(
            predicted_home_score=2, predicted_away_score=1, confidence=0.8, metadata={"reasoning": "Single strategy prediction"}
        )
    )

    strategy._sub_strategies["single"] = mock_strategy
    strategy._strategy_weights["single"] = StrategyWeight(
        strategy_name="single", base_weight=1.0
    )

    input_data = PredictionInput(match_id=123, home_team_id=1, away_team_id=2)

    _result = await strategy.predict(input_data)

    # 应该直接返回子策略的结果
    assert _result.predicted_home_score == 2
    assert _result.predicted_away_score == 1
    assert _result.confidence == 0.8
    assert "single" in _result.metadata.get("reasoning", "").lower()


def test_strategy_weight_creation():
    """测试策略权重创建"""
    weight = StrategyWeight(
        strategy_name="test",
        base_weight=0.5,
        dynamic_weight=0.6,
        performance_weight=0.7,
        recent_accuracy=0.75,
    )

    assert weight.strategy_name == "test"
    assert weight.base_weight == 0.5
    assert weight.dynamic_weight == 0.6
    assert weight.performance_weight == 0.7
    assert weight.recent_accuracy == 0.75


def test_ensemble_result_creation():
    """测试集成结果创建"""
    _result = EnsembleResult(
        final_prediction=(2, 1),
        confidence=0.8,
        strategy_contributions={
            "historical": {"weight": 0.4, "prediction": (2, 1)},
            "statistical": {"weight": 0.35, "prediction": (2, 0)},
            "ml_model": {"weight": 0.25, "prediction": (3, 1)},
        },
        consensus_score=0.75,
        disagreement_level=0.5,
    )

    assert _result.final_prediction == (2, 1)
    assert _result.confidence == 0.8
    assert len(_result.strategy_contributions) == 3
    assert _result.consensus_score == 0.75
    assert _result.disagreement_level == 0.5


@pytest.mark.asyncio
async def test_performance_history_update(ensemble_strategy):
    """测试性能历史更新"""
    # 初始化性能历史
    ensemble_strategy._performance_window = 5
    ensemble_strategy._performance_history = {
        "historical": [0.7, 0.75, 0.72, 0.78, 0.76],
        "statistical": [0.6, 0.65, 0.68, 0.64, 0.66],
    }

    # 添加新的性能数据
    await ensemble_strategy._update_performance_history("historical", 0.8)
    await ensemble_strategy._update_performance_history("statistical", 0.63)

    # 验证历史更新（应该保持窗口大小）
    assert len(ensemble_strategy._performance_history["historical"]) == 5
    assert len(ensemble_strategy._performance_history["statistical"]) == 5

    # 最新的值应该在末尾
    assert ensemble_strategy._performance_history["historical"][-1] == 0.8
    assert ensemble_strategy._performance_history["statistical"][-1] == 0.63


@pytest.mark.asyncio
async def test_ensemble_strategy_metrics(ensemble_strategy):
    """测试集成策略指标"""
    # 添加一些性能数据
    ensemble_strategy._performance_history = {
        "historical": [0.7, 0.75, 0.72, 0.78, 0.76],
        "statistical": [0.6, 0.65, 0.68, 0.64, 0.66],
        "ml_model": [0.8, 0.82, 0.79, 0.83, 0.81],
    }

    metrics = await ensemble_strategy.get_metrics()

    assert metrics is not None
    assert "average_accuracy" in metrics.__dict__
    assert "strategy_count" in metrics.__dict__
    assert metrics.strategy_count == 3
    assert 0 <= metrics.average_accuracy <= 1
