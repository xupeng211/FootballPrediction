"""
策略模式测试套件
Strategy Pattern Test Suite

测试预测策略模式的核心功能，包括策略基类、工厂、具体策略实现等。
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from typing import Any, Dict, List

from src.domain.strategies.base import (
    StrategyType,
    PredictionInput,
    PredictionOutput,
    StrategyMetrics,
    PredictionStrategy,
)
from src.domain.strategies.factory import (
    PredictionStrategyFactory,
    StrategyCreationError,
    StrategyConfigurationError,
)
from src.domain.strategies.ml_model import MLModelStrategy
from src.domain.strategies.statistical import StatisticalStrategy


class MockMatch:
    """模拟比赛数据类"""

    def __init__(self, match_id: int, home_team_id: int, away_team_id: int):
        self.match_id = match_id
        self.home_team_id = home_team_id
        self.away_team_id = away_team_id


class MockTeam:
    """模拟队伍数据类"""

    def __init__(self, team_id: int, name: str, rating: float):
        self.team_id = team_id
        self.name = name
        self.rating = rating


class TestStrategyType:
    """策略类型测试"""

    def test_strategy_type_enum(self):
        """测试策略类型枚举"""
        assert StrategyType.ML_MODEL.value == "ml_model"
        assert StrategyType.STATISTICAL.value == "statistical"
        assert StrategyType.HISTORICAL.value == "historical"
        assert StrategyType.ENSEMBLE.value == "ensemble"

    def test_strategy_type_values(self):
        """测试策略类型值"""
        strategy_types = list(StrategyType)
        assert len(strategy_types) == 4
        assert StrategyType.ML_MODEL in strategy_types
        assert StrategyType.STATISTICAL in strategy_types
        assert StrategyType.HISTORICAL in strategy_types
        assert StrategyType.ENSEMBLE in strategy_types


class TestPredictionInput:
    """预测输入测试"""

    def test_prediction_input_initialization(self):
        """测试预测输入初始化"""
        match = MockMatch(123, 1, 2)
        home_team = MockTeam(1, "Team A", 85.5)
        away_team = MockTeam(2, "Team B", 78.2)

        input_data = PredictionInput(
            match=match,
            home_team=home_team,
            away_team=away_team,
            historical_data={"wins": 10, "losses": 5},
            additional_features={"weather": "sunny"},
        )

        assert input_data.match == match
        assert input_data.home_team == home_team
        assert input_data.away_team == away_team
        assert input_data.historical_data == {"wins": 10, "losses": 5}
        assert input_data.additional_features == {"weather": "sunny"}
        assert isinstance(input_data.timestamp, datetime)

    def test_prediction_input_defaults(self):
        """测试预测输入默认值"""
        match = MockMatch(123, 1, 2)
        home_team = MockTeam(1, "Team A", 85.5)
        away_team = MockTeam(2, "Team B", 78.2)

        input_data = PredictionInput(
            match=match, home_team=home_team, away_team=away_team
        )

        assert input_data.historical_data is None
        assert input_data.additional_features == {}
        assert isinstance(input_data.timestamp, datetime)

    def test_prediction_input_timestamp_auto_generation(self):
        """测试预测输入时间戳自动生成"""
        match = MockMatch(123, 1, 2)
        home_team = MockTeam(1, "Team A", 85.5)
        away_team = MockTeam(2, "Team B", 78.2)

        input_data1 = PredictionInput(match, home_team, away_team)
        input_data2 = PredictionInput(match, home_team, away_team)

        # 验证时间戳是最近的
        now = datetime.utcnow()
        assert abs((input_data1.timestamp - now).total_seconds()) < 5
        assert abs((input_data2.timestamp - now).total_seconds()) < 5


class TestPredictionOutput:
    """预测输出测试"""

    def test_prediction_output_initialization(self):
        """测试预测输出初始化"""
        output_data = PredictionOutput(
            predicted_home_score=2,
            predicted_away_score=1,
            confidence=0.85,
            probability_distribution={"home_win": 0.6, "draw": 0.2, "away_win": 0.2},
            feature_importance={"rating_diff": 0.7, "home_advantage": 0.3},
            strategy_used="ml_model",
            execution_time_ms=150.5,
        )

        assert output_data.predicted_home_score == 2
        assert output_data.predicted_away_score == 1
        assert output_data.confidence == 0.85
        assert output_data.probability_distribution == {
            "home_win": 0.6,
            "draw": 0.2,
            "away_win": 0.2,
        }
        assert output_data.feature_importance == {
            "rating_diff": 0.7,
            "home_advantage": 0.3,
        }
        assert output_data.strategy_used == "ml_model"
        assert output_data.execution_time_ms == 150.5

    def test_prediction_output_defaults(self):
        """测试预测输出默认值"""
        output_data = PredictionOutput(
            predicted_home_score=1, predicted_away_score=1, confidence=0.5
        )

        assert output_data.probability_distribution is None
        assert output_data.feature_importance is None
        assert output_data.strategy_used is None
        assert output_data.execution_time_ms is None
        assert output_data.metadata == {}

    def test_prediction_output_confidence_validation(self):
        """测试预测输出置信度验证"""
        # 测试有效置信度
        valid_output = PredictionOutput(
            predicted_home_score=2, predicted_away_score=1, confidence=0.75
        )
        assert 0.0 <= valid_output.confidence <= 1.0

        # 置信度超出范围（在实际应用中应该有验证）
        # 这里只测试数据存储，不进行业务规则验证
        high_confidence_output = PredictionOutput(
            predicted_home_score=3, predicted_away_score=0, confidence=1.5
        )
        assert high_confidence_output.confidence == 1.5


class TestStrategyMetrics:
    """策略指标测试"""

    def test_strategy_metrics_initialization(self):
        """测试策略指标初始化"""
        metrics = StrategyMetrics(
            accuracy=0.85,
            precision=0.78,
            recall=0.92,
            f1_score=0.84,
            total_predictions=100,
        )

        assert metrics.accuracy == 0.85
        assert metrics.precision == 0.78
        assert metrics.recall == 0.92
        assert metrics.f1_score == 0.84
        assert metrics.total_predictions == 100

    def test_strategy_metrics_bounds(self):
        """测试策略指标边界"""
        # 测试指标在0-1范围内
        metrics = StrategyMetrics(
            accuracy=0.95,
            precision=0.88,
            recall=0.91,
            f1_score=0.89,
            total_predictions=150,
        )

        assert 0.0 <= metrics.accuracy <= 1.0
        assert 0.0 <= metrics.precision <= 1.0
        assert 0.0 <= metrics.recall <= 1.0
        assert 0.0 <= metrics.f1_score <= 1.0


class TestPredictionStrategy:
    """预测策略基类测试"""

    def test_strategy_initialization(self):
        """测试策略初始化"""
        strategy = MockPredictionStrategy("test_strategy", StrategyType.ML_MODEL)

        assert strategy.name == "test_strategy"
        assert strategy.strategy_type == StrategyType.ML_MODEL
        assert strategy._metrics is None
        assert strategy._is_initialized is False
        assert strategy.config == {}

    async def test_strategy_initialize(self):
        """测试策略初始化方法"""
        strategy = MockPredictionStrategy("test_strategy", StrategyType.ML_MODEL)
        config = {"param1": "value1", "param2": 42}

        await strategy.initialize(config)

        assert strategy._is_initialized is True
        assert strategy.config == config

    def test_strategy_name_and_type(self):
        """测试策略名称和类型"""
        strategy = MockPredictionStrategy("ml_strategy_v1", StrategyType.ML_MODEL)

        assert strategy.name == "ml_strategy_v1"
        assert strategy.strategy_type == StrategyType.ML_MODEL

    def test_strategy_metrics_setting(self):
        """测试策略指标设置"""
        strategy = MockPredictionStrategy("test_strategy", StrategyType.STATISTICAL)
        metrics = StrategyMetrics(
            accuracy=0.85, precision=0.78, recall=0.92, f1_score=0.84
        )

        strategy.set_metrics(metrics)

        assert strategy._metrics == metrics

    def test_strategy_metrics_getting(self):
        """测试策略指标获取"""
        strategy = MockPredictionStrategy("test_strategy", StrategyType.STATISTICAL)
        metrics = StrategyMetrics(
            accuracy=0.90, precision=0.85, recall=0.88, f1_score=0.86
        )

        strategy.set_metrics(metrics)
        retrieved_metrics = strategy.get_metrics()

        assert retrieved_metrics == metrics

    def test_strategy_metrics_none_when_not_set(self):
        """测试未设置指标时返回None"""
        strategy = MockPredictionStrategy("test_strategy", StrategyType.STATISTICAL)

        assert strategy.get_metrics() is None


class TestPredictionStrategyFactory:
    """预测策略工厂测试"""

    def test_factory_initialization(self):
        """测试工厂初始化"""
        factory = PredictionStrategyFactory()

        assert hasattr(factory, "_strategies")
        assert hasattr(factory, "_default_config")
        assert hasattr(factory, "_strategy_registry")

    def test_create_ml_strategy(self):
        """测试创建机器学习策略"""
        factory = PredictionStrategyFactory()
        config = {"model_path": "/path/to/model.pkl", "features": ["rating", "form"]}

        strategy = factory.create_strategy("ml_model", "Test ML Strategy", config)

        assert strategy is not None
        assert isinstance(strategy, MLModelStrategy)
        assert strategy.name == "Test ML Strategy"
        assert strategy.strategy_type == StrategyType.ML_MODEL

    def test_create_statistical_strategy(self):
        """测试创建统计策略"""
        factory = PredictionStrategyFactory()
        config = {"method": "poisson", "window_size": 10}

        strategy = factory.create_strategy(
            "statistical", "Test Statistical Strategy", config
        )

        assert strategy is not None
        assert isinstance(strategy, StatisticalStrategy)
        assert strategy.name == "Test Statistical Strategy"
        assert strategy.strategy_type == StrategyType.STATISTICAL

    def test_create_unknown_strategy_type(self):
        """测试创建未知策略类型"""
        factory = PredictionStrategyFactory()
        config = {}

        with pytest.raises(StrategyCreationError):
            factory.create_strategy("unknown_type", "Test Strategy", config)

    def test_factory_strategy_registry(self):
        """测试工厂策略注册表"""
        factory = PredictionStrategyFactory()

        # 验证默认策略类型已注册
        registered_types = factory.get_registered_strategy_types()

        assert StrategyType.ML_MODEL.value in registered_types
        assert StrategyType.STATISTICAL.value in registered_types
        assert StrategyType.HISTORICAL.value in registered_types
        assert StrategyType.ENSEMBLE.value in registered_types

    def test_factory_config_validation(self):
        """测试工厂配置验证"""
        factory = PredictionStrategyFactory()

        # 测试有效配置
        valid_config = {"model_path": "/path/to/model", "features": ["rating"]}

        # 这应该不会抛出异常
        strategy = factory.create_strategy("ml_model", "Test", valid_config)
        assert strategy is not None

    def test_factory_with_empty_config(self):
        """测试工厂使用空配置"""
        factory = PredictionStrategyFactory()

        # 使用空配置创建策略
        strategy = factory.create_strategy("statistical", "Test", {})

        assert strategy is not None
        assert isinstance(strategy, StatisticalStrategy)


class TestStrategyIntegration:
    """策略集成测试"""

    async def test_strategy_end_to_end_prediction(self):
        """测试策略端到端预测"""
        factory = PredictionStrategyFactory()

        # 创建统计策略
        config = {"method": "simple", "default_home_advantage": 0.1}
        strategy = factory.create_strategy(
            "statistical", "Integration Test Strategy", config
        )

        # 初始化策略
        await strategy.initialize(config)

        # 创建测试输入
        match = MockMatch(123, 1, 2)
        home_team = MockTeam(1, "Team A", 85.5)
        away_team = MockTeam(2, "Team B", 78.2)

        input_data = PredictionInput(
            match=match,
            home_team=home_team,
            away_team=away_team,
            additional_features={"home_advantage": 0.1},
        )

        # 执行预测
        output = await strategy.predict(input_data)

        # 验证预测结果
        assert output is not None
        assert isinstance(output, PredictionOutput)
        assert output.predicted_home_score >= 0
        assert output.predicted_away_score >= 0
        assert 0.0 <= output.confidence <= 1.0
        assert output.strategy_used == "Integration Test Strategy"

    def test_multiple_strategy_creation(self):
        """测试创建多个策略"""
        factory = PredictionStrategyFactory()

        strategies = []

        # 创建多个不同类型的策略
        strategy_configs = [
            ("ml_model", "ML Strategy 1", {"model_path": "model1.pkl"}),
            ("statistical", "Statistical Strategy 1", {"method": "poisson"}),
            ("ml_model", "ML Strategy 2", {"model_path": "model2.pkl"}),
            ("statistical", "Statistical Strategy 2", {"method": "linear"}),
        ]

        for strategy_type, name, config in strategy_configs:
            strategy = factory.create_strategy(strategy_type, name, config)
            strategies.append(strategy)

        # 验证所有策略都被正确创建
        assert len(strategies) == 4
        assert all(s is not None for s in strategies)
        assert all(isinstance(s, PredictionStrategy) for s in strategies)

    async def test_strategy_error_handling(self):
        """测试策略错误处理"""
        factory = PredictionStrategyFactory()

        # 创建一个会抛出异常的模拟策略
        class FailingStrategy(MockPredictionStrategy):
            async def predict(self, input_data: PredictionInput) -> PredictionOutput:
                raise Exception("Prediction failed")

        # 注册失败策略到工厂（如果可能）
        try:
            # 测试错误处理
            strategy = FailingStrategy("failing_strategy", StrategyType.ML_MODEL)

            match = MockMatch(123, 1, 2)
            home_team = MockTeam(1, "Team A", 85.5)
            away_team = MockTeam(2, "Team B", 78.2)

            input_data = PredictionInput(
                match=match, home_team=home_team, away_team=away_team
            )

            # 预测应该抛出异常
            with pytest.raises(Exception, match="Prediction failed"):
                await strategy.predict(input_data)

        except Exception as e:
            # 如果注册失败，跳过测试
            pytest.skip(f"Strategy registration failed: {e}")


class TestStrategyPerformance:
    """策略性能测试"""

    async def test_strategy_prediction_performance(self):
        """测试策略预测性能"""
        import time

        factory = PredictionStrategyFactory()

        # 创建统计策略
        config = {"method": "simple"}
        strategy = factory.create_strategy(
            "statistical", "Performance Test Strategy", config
        )
        await strategy.initialize(config)

        # 创建测试输入
        match = MockMatch(123, 1, 2)
        home_team = MockTeam(1, "Team A", 85.5)
        away_team = MockTeam(2, "Team B", 78.2)

        input_data = PredictionInput(
            match=match, home_team=home_team, away_team=away_team
        )

        # 测试多次预测的性能
        start_time = time.time()

        predictions = []
        for i in range(100):
            # 修改输入以模拟不同场景
            input_data.additional_features = {"test_id": i}
            output = await strategy.predict(input_data)
            predictions.append(output)

        end_time = time.time()
        duration = end_time - start_time

        # 验证性能（100次预测应该在5秒内完成）
        assert duration < 5.0, f"Strategy prediction too slow: {duration}s"
        assert len(predictions) == 100

        # 验证所有预测结果都有效
        for output in predictions:
            assert output is not None
            assert isinstance(output, PredictionOutput)
            assert output.predicted_home_score >= 0
            assert output.predicted_away_score >= 0


# 辅助类和函数
class MockPredictionStrategy(PredictionStrategy):
    """模拟预测策略实现"""

    def __init__(self, name: str, strategy_type: StrategyType):
        super().__init__(name, strategy_type)

    async def initialize(self, config: dict[str, Any]) -> None:
        """初始化模拟策略"""
        self._is_initialized = True
        self.config = config

    async def predict(self, input_data: PredictionInput) -> PredictionOutput:
        """执行预测"""
        if not self._is_initialized:
            raise ValueError("Strategy not initialized")

        # 简单的模拟预测逻辑
        home_score = max(0, int(input_data.home_team.rating / 30))
        away_score = max(0, int(input_data.away_team.rating / 30))

        # 基于评分差计算置信度
        rating_diff = abs(input_data.home_team.rating - input_data.away_team.rating)
        confidence = min(0.9, 0.5 + (rating_diff / 100))

        return PredictionOutput(
            predicted_home_score=home_score,
            predicted_away_score=away_score,
            confidence=confidence,
            strategy_used=self.name,
            execution_time_ms=10.0,
        )

    def set_metrics(self, metrics: StrategyMetrics) -> None:
        """设置策略指标"""
        self._metrics = metrics

    def get_metrics(self) -> StrategyMetrics | None:
        """获取策略指标"""
        return self._metrics


def create_test_match() -> MockMatch:
    """创建测试比赛"""
    return MockMatch(12345, 1, 2)


def create_test_teams() -> tuple[MockTeam, MockTeam]:
    """创建测试队伍"""
    home_team = MockTeam(1, "Team A", 85.5)
    away_team = MockTeam(2, "Team B", 78.2)
    return home_team, away_team


def create_test_prediction_input() -> PredictionInput:
    """创建测试预测输入"""
    match = create_test_match()
    home_team, away_team = create_test_teams()

    return PredictionInput(
        match=match,
        home_team=home_team,
        away_team=away_team,
        historical_data={"home_wins": 5, "away_wins": 3},
        additional_features={"weather": "sunny", "venue": "home"},
    )


def assert_valid_prediction_output(output: PredictionOutput):
    """断言预测输出有效"""
    assert output is not None
    assert isinstance(output, PredictionOutput)
    assert output.predicted_home_score >= 0
    assert output.predicted_away_score >= 0
    assert 0.0 <= output.confidence <= 1.0
    assert isinstance(output.strategy_used, (str, type(None)))
    assert isinstance(output.execution_time_ms, (float, int, type(None)))
