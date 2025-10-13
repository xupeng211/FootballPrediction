"""
策略预测服务测试（真实实现）
Tests for Strategy Prediction Service (Real Implementation)

这个测试文件专注于测试服务的核心逻辑，减少不必要的Mock使用，
只在需要模拟外部依赖（如数据库、网络）时使用Mock。
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock, Mock

from src.services.strategy_prediction_service import StrategyPredictionService
from src.domain.strategies import PredictionStrategy, PredictionStrategyFactory
from src.domain.models import Prediction, Match, Team


class MockStrategy(PredictionStrategy):
    """模拟预测策略"""

    def __init__(self, name="mock_strategy"):
        self.name = name

    async def predict(self, input_data):
        """简单的预测逻辑"""
        return MagicMock(
            predicted_home_score=2,
            predicted_away_score=1,
            confidence=0.85,
            reasoning=f"Mock prediction by {self.name}",
        )


class MockStrategyFactory(PredictionStrategyFactory):
    """模拟策略工厂"""

    def __init__(self):
        self.strategies = {}
        self.create_default_strategies_called = False

    async def initialize_default_strategies(self):
        """初始化默认策略"""
        self.create_default_strategies_called = True
        # 添加几个模拟策略
        self.strategies["mock_strategy"] = MockStrategy("mock_strategy")
        self.strategies["mock_strategy_2"] = MockStrategy("mock_strategy_2")

    async def get_strategy(self, strategy_name):
        """获取策略"""
        return self.strategies.get(strategy_name)


class MockMatchRepository:
    """模拟比赛仓储"""

    def __init__(self):
        self._matches = {}
        self._setup_test_data()

    def _setup_test_data(self):
        """设置测试数据"""
        # 创建测试球队
        team1 = Mock(spec=Team)
        team1.id = 1
        team1.name = "Team A"

        team2 = Mock(spec=Team)
        team2.id = 2
        team2.name = "Team B"

        # 创建测试比赛
        match = Mock(spec=Match)
        match.id = 123
        match.home_team_id = 1
        match.away_team_id = 2
        match.home_team = team1
        match.away_team = team2
        match.match_date = datetime.utcnow() + timedelta(days=1)
        match.status = "SCHEDULED"

        self.matches[123] = match

    async def get_by_id(self, match_id):
        """根据ID获取比赛"""
        return self.matches.get(match_id)


class MockPredictionRepository:
    """模拟预测仓储"""

    def __init__(self):
        self.predictions = []
        self.create_calls = []

    async def create(self, prediction):
        """创建预测"""
        self.create_calls.append(prediction)
        # 模拟设置ID
        prediction.id = len(self.predictions) + 1
        prediction.created_at = datetime.utcnow()
        self.predictions.append(prediction)
        return prediction


class MockPredictionDomainService:
    """模拟预测领域服务"""

    def create_prediction(self, **kwargs):
        """创建预测"""
        _prediction = Mock(spec=Prediction)
        prediction.id = None  # 将在仓储中设置
        prediction.user_id = kwargs.get("user_id")
        prediction.match_id = kwargs.get("match")
        prediction.predicted_home_score = kwargs.get("predicted_home")
        prediction.predicted_away_score = kwargs.get("predicted_away")
        prediction.confidence_score = kwargs.get("confidence")
        prediction.created_at = datetime.utcnow()
        return prediction


class TestStrategyPredictionServiceReal:
    """策略预测服务真实测试"""

    @pytest.fixture
    def strategy_factory(self):
        """策略工厂fixture"""
        return MockStrategyFactory()

    @pytest.fixture
    def prediction_service(self):
        """预测领域服务fixture"""
        return MockPredictionDomainService()

    @pytest.fixture
    def match_repository(self):
        """比赛仓储fixture"""
        return MockMatchRepository()

    @pytest.fixture
    def prediction_repository(self):
        """预测仓储fixture"""
        return MockPredictionRepository()

    @pytest.fixture
    def service(
        self,
        strategy_factory,
        prediction_service,
        match_repository,
        prediction_repository,
    ):
        """服务实例fixture"""
        return StrategyPredictionService(
            strategy_factory=strategy_factory,
            prediction_domain_service=prediction_service,
            match_repository=match_repository,
            prediction_repository=prediction_repository,
            default_strategy="mock_strategy",
        )

    @pytest.mark.asyncio
    async def test_service_initialization_with_real_dependencies(
        self,
        strategy_factory,
        prediction_service,
        match_repository,
        prediction_repository,
    ):
        """测试：使用真实依赖初始化服务"""
        # When
        service = StrategyPredictionService(
            strategy_factory=strategy_factory,
            prediction_domain_service=prediction_service,
            match_repository=match_repository,
            prediction_repository=prediction_repository,
        )

        # Then
        assert service._strategy_factory is strategy_factory
        assert service._prediction_domain_service is prediction_service
        assert service._match_repository is match_repository
        assert service._prediction_repository is prediction_repository
        assert service._default_strategy == "ensemble_predictor"
        assert service._current_strategies == {}

    @pytest.mark.asyncio
    async def test_initialize_service_success(self, service, strategy_factory):
        """测试：成功初始化服务"""
        # When
        await service.initialize()

        # Then
        assert service._initialized is True
        assert strategy_factory.create_default_strategies_called is True
        assert "mock_strategy" in service._current_strategies

    @pytest.mark.asyncio
    async def test_predict_match_success(self, service):
        """测试：成功预测比赛"""
        # Given
        await service.initialize()

        # When
        _result = await service.predict_match(
            match_id=123,
            user_id=456,
            strategy_name="mock_strategy",
            confidence=0.9,
            notes="测试预测",
        )

        # Then
        assert result is not None
        assert service._prediction_repository.create_calls
        created_prediction = service._prediction_repository.create_calls[0]
        assert created_prediction.user_id == 456
        assert created_prediction.match_id == 123

    @pytest.mark.asyncio
    async def test_predict_match_with_default_strategy(self, service):
        """测试：使用默认策略预测"""
        # Given
        await service.initialize()

        # When
        _result = await service.predict_match(match_id=123, user_id=456)

        # Then
        assert result is not None
        # 应该使用默认策略
        assert service._current_strategies["mock_strategy"].name == "mock_strategy"

    @pytest.mark.asyncio
    async def test_predict_match_match_not_found(self, service):
        """测试：比赛不存在"""
        # Given
        await service.initialize()

        # When / Then
        with pytest.raises(ValueError, match="比赛不存在"):
            await service.predict_match(match_id=999, user_id=456)

    @pytest.mark.asyncio
    async def test_batch_predict_multiple_matches(self, service):
        """测试：批量预测多个比赛"""
        # Given
        await service.initialize()
        # 添加更多测试比赛
        service._match_repository.matches[456] = Mock(
            spec=Match, id=456, home_team_id=3, away_team_id=4
        )
        service._match_repository.matches[789] = Mock(
            spec=Match, id=789, home_team_id=5, away_team_id=6
        )

        # When
        results = await service.batch_predict(
            match_ids=[123, 456, 789], user_id=1001, strategy_name="mock_strategy"
        )

        # Then
        assert len(results) == 3
        assert len(service._prediction_repository.create_calls) == 3

    @pytest.mark.asyncio
    async def test_batch_predict_empty_list(self, service):
        """测试：批量预测空列表"""
        # Given
        await service.initialize()

        # When
        results = await service.batch_predict([], user_id=456)

        # Then
        assert results == []
        assert len(service._prediction_repository.create_calls) == 0

    @pytest.mark.asyncio
    async def test_get_or_create_strategy_existing(self, service):
        """测试：获取已存在的策略"""
        # Given
        await service.initialize()
        strategy = service._current_strategies["mock_strategy"]

        # When
        _result = await service._get_or_create_strategy("mock_strategy")

        # Then
        assert result is strategy
        # 不应该从工厂获取
        service._strategy_factory.get_strategy.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_strategy_new(self, service):
        """测试：获取新策略"""
        # Given
        await service.initialize()
        new_strategy = MockStrategy("new_test_strategy")
        service._strategy_factory.get_strategy = AsyncMock(return_value=new_strategy)

        # When
        _result = await service._get_or_create_strategy("new_test_strategy")

        # Then
        assert result is new_strategy
        service._strategy_factory.get_strategy.assert_called_once_with(
            "new_test_strategy"
        )
        assert "new_test_strategy" in service._current_strategies

    @pytest.mark.asyncio
    async def test_prepare_prediction_input(self, service):
        """测试：准备预测输入"""
        # Given
        await service.initialize()
        match = await service._match_repository.get_by_id(123)

        # When
        _result = await service._prepare_prediction_input(match)

        # Then
        assert result.match == match
        assert result.home_team == match.home_team
        assert result.away_team == match.away_team
        assert result.user_id is not None  # 应该在上下文中设置

    def test_service_attributes(self, service):
        """测试：服务属性"""
        # Then
        assert hasattr(service, "_strategy_factory")
        assert hasattr(service, "_prediction_domain_service")
        assert hasattr(service, "_match_repository")
        assert hasattr(service, "_prediction_repository")
        assert hasattr(service, "_current_strategies")
        assert hasattr(service, "_default_strategy")

    def test_default_strategy_value(self):
        """测试：默认策略值"""
        # When
        service = StrategyPredictionService(
            strategy_factory=Mock(),
            prediction_domain_service=Mock(),
            match_repository=Mock(),
            prediction_repository=Mock(),
            default_strategy="custom_default",
        )

        # Then
        assert service._default_strategy == "custom_default"

    @pytest.mark.asyncio
    async def test_service_lifecycle(self, service, strategy_factory):
        """测试：服务生命周期"""
        # Given
        assert not service._initialized
        assert not strategy_factory.create_default_strategies_called

        # When - 初始化
        await service.initialize()

        # Then
        assert service._initialized
        assert strategy_factory.create_default_strategies_called

        # When - 关闭
        await service.shutdown()

        # Then
        assert not service._initialized

    @pytest.mark.asyncio
    async def test_concurrent_predictions(self, service):
        """测试：并发预测"""
        # Given
        await service.initialize()

        # When - 并发执行多个预测
        import asyncio

        tasks = [service.predict_match(match_id=123, user_id=i) for i in range(1, 6)]
        results = await asyncio.gather(*tasks)

        # Then
        assert len(results) == 5
        assert all(r is not None for r in results)
        # 所有预测都应该被创建
        assert len(service._prediction_repository.create_calls) == 5
