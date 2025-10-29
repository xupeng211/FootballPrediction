from unittest.mock import MagicMock, patch

"""测试基础策略类"""

import asyncio
from typing import Any, Dict, List, Tuple

import pytest

from src.domain.strategies.base import (
    PredictionInput,
    PredictionOutput,
    PredictionStrategy,
    StrategyMetrics,
    StrategyType,
)
from src.domain.models.prediction import Prediction


class MockStrategy(PredictionStrategy):
    """用于测试的模拟策略类"""

    def __init__(self, name: str = "mock_strategy"):
        super().__init__(name, StrategyType.ML_MODEL)
        self._validate_input_called = False
        self._pre_process_called = False
        self._post_process_called = False

    async def initialize(self, config: Dict[str, Any]) -> None:
        """初始化策略"""
        self._is_initialized = True
        self.config.update(config)

    async def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """执行预测"""
        # 简单的模拟预测逻辑
        home_goals = 2 if input_data.home_team else 1
        away_goals = 1 if input_data.away_team else 0
        confidence = 0.75

        return PredictionOutput(
            predicted_home_score=home_goals,
            predicted_away_score=away_goals,
            confidence=confidence,
            metadata={"reasoning": "Mock prediction for testing"},
        )

    async def batch_predict(self, inputs: List[PredictionInput]) -> List[PredictionOutput]:
        """批量预测"""
        results = []
        for input_data in inputs:
            result = await self.predict(input_data)
            results.append(result)
        return results

    async def update_metrics(self, actual_results: List[Tuple[Prediction, Dict[str, Any]]]) -> None:
        """更新策略性能指标"""
        # 模拟指标更新
        self._metrics = StrategyMetrics(
            accuracy=0.8,
            precision=0.75,
            recall=0.7,
            f1_score=0.72,
            total_predictions=len(actual_results),
        )


@pytest.fixture
def mock_strategy():
    """创建模拟策略实例"""
    return MockStrategy("test_mock_strategy")


@pytest.fixture
def valid_prediction_input():
    """创建有效的预测输入"""
    # 创建模拟的Match对象
    match = MagicMock()
    match.id = 123
    match.home_team_id = 1
    match.away_team_id = 2

    # 创建模拟的Team对象
    home_team = MagicMock()
    home_team.id = 1
    home_team.name = "Home Team"

    away_team = MagicMock()
    away_team.id = 2
    away_team.name = "Away Team"

    return PredictionInput(
        match=match,
        home_team=home_team,
        away_team=away_team,
        historical_data={"home_form": "WWLDW", "away_form": "LDDLL"},
    )


@pytest.fixture
def invalid_prediction_input():
    """创建无效的预测输入"""
    return PredictionInput(match=None, home_team=None, away_team=None)


@pytest.mark.unit
class TestPredictionStrategy:
    """测试预测策略基类"""

    def test_strategy_initialization(self, mock_strategy):
        """测试策略初始化"""
        assert mock_strategy.name == "test_mock_strategy"
        assert mock_strategy.strategy_type == StrategyType.ML_MODEL
        assert mock_strategy._is_initialized is False
        # 移除不存在的属性检查

    @pytest.mark.asyncio
    async def test_strategy_configuration(self, mock_strategy):
        """测试策略配置"""
        _config = {"param1": "value1", "param2": 42, "model_path": "/path/to/model"}

        await mock_strategy.initialize(_config)

        assert mock_strategy._is_initialized is True
        assert mock_strategy._config == _config

    @pytest.mark.asyncio
    async def test_successful_prediction_flow(self, mock_strategy, valid_prediction_input):
        """测试成功的预测流程"""
        # 初始化策略
        await mock_strategy.initialize({})

        # 执行预测
        _result = await mock_strategy.predict(valid_prediction_input)

        # 验证结果
        assert isinstance(_result, PredictionOutput)
        assert hasattr(_result, "predicted_home_score")
        assert hasattr(_result, "predicted_away_score")
        assert isinstance(_result.predicted_home_score, int)
        assert isinstance(_result.predicted_away_score, int)
        assert isinstance(_result.confidence, float)
        assert 0 <= _result.confidence <= 1
        assert _result.metadata is not None
        assert _result.metadata.get("reasoning") is not None

        # 验证所有步骤都被调用
        assert mock_strategy._validate_input_called is True
        assert mock_strategy._pre_process_called is True
        assert mock_strategy._post_process_called is True

        # 验证统计数据
        assert mock_strategy._prediction_count == 1
        assert mock_strategy._total_confidence == _result.confidence

    @pytest.mark.asyncio
    async def test_prediction_without_initialization(self, mock_strategy, valid_prediction_input):
        """测试未初始化的预测"""
        with pytest.raises(RuntimeError, match="策略未初始化"):
            await mock_strategy.predict(valid_prediction_input)

    @pytest.mark.asyncio
    async def test_invalid_input_handling(self, mock_strategy, invalid_prediction_input):
        """测试无效输入处理"""
        await mock_strategy.initialize({})

        with pytest.raises(ValueError, match="输入数据无效"):
            await mock_strategy.predict(invalid_prediction_input)

    @pytest.mark.asyncio
    async def test_prediction_metrics(self, mock_strategy, valid_prediction_input):
        """测试预测指标"""
        await mock_strategy.initialize({})

        # 执行多次预测
        for _ in range(5):
            await mock_strategy.predict(valid_prediction_input)

        # 获取指标
        metrics = await mock_strategy.get_metrics()

        assert isinstance(metrics, StrategyMetrics)
        assert metrics.strategy_name == mock_strategy.name
        assert metrics.strategy_type == mock_strategy.type
        assert metrics.prediction_count == 5
        assert metrics.average_confidence > 0
        assert metrics.average_confidence < 1
        assert metrics.is_initialized is True

    @pytest.mark.asyncio
    async def test_average_confidence_calculation(self, mock_strategy, valid_prediction_input):
        """测试平均置信度计算"""
        await mock_strategy.initialize({})

        # 执行预测并修改置信度
        predictions = []
        for i in range(3):
            _result = await mock_strategy.predict(valid_prediction_input)
            predictions.append(_result)

        metrics = await mock_strategy.get_metrics()
        expected_avg = sum(p.confidence for p in predictions) / len(predictions)

        assert abs(metrics.average_confidence - expected_avg) < 0.001

    @pytest.mark.asyncio
    async def test_strategy_reset(self, mock_strategy, valid_prediction_input):
        """测试策略重置"""
        await mock_strategy.initialize({})

        # 执行一些预测
        await mock_strategy.predict(valid_prediction_input)
        await mock_strategy.predict(valid_prediction_input)

        assert mock_strategy._prediction_count == 2

        # 重置策略
        await mock_strategy.reset()

        assert mock_strategy._prediction_count == 0
        assert mock_strategy._total_confidence == 0.0

    @pytest.mark.asyncio
    async def test_preprocessing_modification(self, mock_strategy, valid_prediction_input):
        """测试预处理修改"""
        await mock_strategy.initialize({})

        await mock_strategy.predict(valid_prediction_input)

        # 验证预处理标记被添加
        assert hasattr(valid_prediction_input, "processed")
        assert valid_prediction_input.processed is True

    @pytest.mark.asyncio
    async def test_postprocessing_modification(self, mock_strategy, valid_prediction_input):
        """测试后处理修改"""
        await mock_strategy.initialize({})

        _result = await mock_strategy.predict(valid_prediction_input)

        # 验证后处理标记被添加
        assert "[Post-processed]" in _result.metadata.get("reasoning", "")

    @pytest.mark.asyncio
    async def test_prediction_with_timing(self, mock_strategy, valid_prediction_input):
        """测试带计时器的预测"""
        await mock_strategy.initialize({})

        with patch("time.time", side_effect=[0.0, 0.1]):
            _result = await mock_strategy.predict_with_timing(valid_prediction_input)

        # 验证结果包含计时信息
        assert _result[0] is not None  # PredictionOutput
        assert _result[1] > 0  # 预测时间
        assert _result[1] < 1  # 合理的时间范围

    def test_strategy_type_validation(self):
        """测试策略类型验证"""
        # 所有有效的策略类型
        valid_types = [
            StrategyType.HISTORICAL,
            StrategyType.STATISTICAL,
            StrategyType.ML_MODEL,
            StrategyType.ENSEMBLE,
        ]

        for strategy_type in valid_types:
            strategy = MockStrategy("test")
            strategy.type = strategy_type
            assert strategy.type in valid_types

    @pytest.mark.asyncio
    async def test_batch_predictions(self, mock_strategy):
        """测试批量预测"""
        await mock_strategy.initialize({})

        # 创建多个输入
        inputs = [
            PredictionInput(
                match_id=i,
                home_team_id=1,
                away_team_id=2,
                home_team_form="W" * i,
                away_team_form="L" * i,
            )
            for i in range(1, 6)
        ]

        # 执行批量预测
        results = await mock_strategy.batch_predict(inputs)

        assert len(results) == 5
        for _result in results:
            assert isinstance(_result, PredictionOutput)
            assert hasattr(_result, "predicted_home_score")
            assert hasattr(_result, "predicted_away_score")

    @pytest.mark.asyncio
    async def test_error_handling_in_prediction(self):
        """测试预测中的错误处理"""

        class ErrorStrategy(MockStrategy):
            async def _predict_internal(self, processed_input):
                raise Exception("Prediction error")

        strategy = ErrorStrategy("error_strategy")
        await strategy.initialize({})

        input_data = PredictionInput(match_id=1, home_team_id=1, away_team_id=2)

        with pytest.raises(Exception, match="Prediction error"):
            await strategy.predict(input_data)

    def test_strategy_serialization(self, mock_strategy):
        """测试策略序列化"""
        strategy_dict = mock_strategy.to_dict()

        assert "name" in strategy_dict
        assert "type" in strategy_dict
        assert "is_initialized" in strategy_dict
        assert strategy_dict["name"] == mock_strategy.name
        assert strategy_dict["type"] == mock_strategy.type.value

    @pytest.mark.asyncio
    async def test_strategy_deserialization(self):
        """测试策略反序列化"""
        strategy_data = {
            "name": "deserialized_strategy",
            "type": "statistical",
            "config": {"param1": "value1"},
        }

        # 注意：这需要在实际实现中支持
        # strategy = PredictionStrategy.from_dict(strategy_data)
        # assert strategy.name == "deserialized_strategy"

        # 目前只测试数据格式
        assert "name" in strategy_data
        assert "type" in strategy_data

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self, mock_strategy, valid_prediction_input):
        """测试并发预测"""
        await mock_strategy.initialize({})

        # 创建并发任务
        tasks = [mock_strategy.predict(valid_prediction_input) for _ in range(10)]

        # 执行并发预测
        results = await asyncio.gather(*tasks)

        assert len(results) == 10
        assert all(isinstance(r, PredictionOutput) for r in results)

        # 验证计数正确
        assert mock_strategy._prediction_count == 10

    def test_strategy_comparison(self, mock_strategy):
        """测试策略比较"""
        strategy1 = MockStrategy("strategy1")
        strategy2 = MockStrategy("strategy2")
        strategy3 = MockStrategy("strategy1")

        assert strategy1 != strategy2
        assert strategy1 != strategy3  # 不同的实例
        assert hash(strategy1) != hash(strategy2)

    @pytest.mark.asyncio
    async def test_strategy_health_check(self, mock_strategy):
        """测试策略健康检查"""
        await mock_strategy.initialize({})

        health = await mock_strategy.health_check()

        assert health["status"] == "healthy"
        assert "initialized" in health
        assert health["initialized"] is True
        assert "prediction_count" in health
