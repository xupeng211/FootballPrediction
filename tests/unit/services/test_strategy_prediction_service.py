"""
策略预测服务测试
Tests for Strategy Prediction Service
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.services.strategy_prediction_service import StrategyPredictionService
from src.domain.strategies import PredictionStrategy, PredictionStrategyFactory
from src.domain.strategies import (
    PredictionInput,
    PredictionOutput,
    PredictionContext,
    StrategyType,
)
from src.domain.models import Prediction, Match, Team


class TestStrategyPredictionService:
    """策略预测服务测试"""

    @pytest.fixture
    def mock_strategy_factory(self):
        """Mock策略工厂"""
        return Mock(spec=PredictionStrategyFactory)

    @pytest.fixture
    def mock_prediction_domain_service(self):
        """Mock预测领域服务"""
        return Mock()

    @pytest.fixture
    def mock_match_repository(self):
        """Mock比赛仓储"""
        return Mock()

    @pytest.fixture
    def mock_prediction_repository(self):
        """Mock预测仓储"""
        return Mock()

    @pytest.fixture
    def service(
        self,
        mock_strategy_factory,
        mock_prediction_domain_service,
        mock_match_repository,
        mock_prediction_repository,
    ):
        """创建服务实例"""
        return StrategyPredictionService(
            strategy_factory=mock_strategy_factory,
            prediction_domain_service=mock_prediction_domain_service,
            match_repository=mock_match_repository,
            prediction_repository=mock_prediction_repository,
            default_strategy="test_strategy",
        )

    @pytest.fixture
    def sample_match(self):
        """示例比赛"""
        match = Mock(spec=Match)
        match.id = 123
        match.home_team_id = 1
        match.away_team_id = 2
        match.match_date = datetime.utcnow()
        match.status = "SCHEDULED"
        return match

    @pytest.fixture
    def sample_team(self):
        """示例球队"""
        team = Mock(spec=Team)
        team.id = 1
        team.name = "Test Team"
        team.stats = Mock()
        return team

    @pytest.fixture
    def sample_strategy(self):
        """示例策略"""
        strategy = Mock(spec=PredictionStrategy)
        strategy.name = "test_strategy"
        strategy.predict = AsyncMock()
        return strategy

    @pytest.fixture
    def sample_prediction_output(self):
        """示例预测输出"""
        output = Mock(spec=PredictionOutput)
        output.predicted_home_score = 2
        output.predicted_away_score = 1
        output.confidence = 0.85
        return output

    def test_service_initialization(self, service):
        """测试：服务初始化"""
        assert service._strategy_factory is not None
        assert service._prediction_domain_service is not None
        assert service._match_repository is not None
        assert service._prediction_repository is not None
        assert service._default_strategy == "test_strategy"
        assert service._current_strategies == {}

    @pytest.mark.asyncio
    async def test_initialize_service(self, service, sample_strategy):
        """测试：初始化服务"""
        # Given
        service._strategy_factory.initialize_default_strategies = AsyncMock()
        service._strategy_factory.get_strategy = AsyncMock(return_value=sample_strategy)

        # When
        await service.initialize()

        # Then
        service._strategy_factory.initialize_default_strategies.assert_called_once()
        service._strategy_factory.get_strategy.assert_called_once_with("test_strategy")
        assert service._current_strategies["test_strategy"] == sample_strategy

    @pytest.mark.asyncio
    async def test_predict_match_success(
        self,
        service,
        sample_match,
        sample_team,
        sample_strategy,
        sample_prediction_output,
    ):
        """测试：成功预测比赛"""
        # Given
        service._match_repository.get_by_id = AsyncMock(return_value=sample_match)
        service._get_team_info = AsyncMock(return_value=sample_team)
        service._get_or_create_strategy = AsyncMock(return_value=sample_strategy)
        service._prepare_prediction_input = AsyncMock()
        sample_strategy.predict.return_value = sample_prediction_output
        service._prediction_domain_service.create_prediction = Mock(return_value=Mock())
        service._prediction_repository.create = AsyncMock()
        service._log_prediction_details = AsyncMock()

        # When
        result = await service.predict_match(
            match_id=123,
            user_id=456,
            strategy_name="test_strategy",
            confidence=0.9,
            notes="测试预测",
        )

        # Then
        service._match_repository.get_by_id.assert_called_once_with(123)
        assert result is not None
        service._prediction_repository.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_match_with_default_strategy(
        self, service, sample_match, sample_strategy, sample_prediction_output
    ):
        """测试：使用默认策略预测比赛"""
        # Given
        service._match_repository.get_by_id = AsyncMock(return_value=sample_match)
        service._get_team_info = AsyncMock(return_value=sample_team)
        service._get_or_create_strategy = AsyncMock(return_value=sample_strategy)
        service._prepare_prediction_input = AsyncMock()
        sample_strategy.predict.return_value = sample_prediction_output
        service._prediction_domain_service.create_prediction = Mock(return_value=Mock())
        service._prediction_repository.create = AsyncMock()

        # When - 不指定策略名称
        await service.predict_match(match_id=123, user_id=456)

        # Then
        service._get_or_create_strategy.assert_called_once_with("test_strategy")

    @pytest.mark.asyncio
    async def test_predict_match_not_found(self, service):
        """测试：比赛不存在"""
        # Given
        service._match_repository.get_by_id = AsyncMock(return_value=None)

        # When / Then
        with pytest.raises(ValueError, match="比赛不存在"):
            await service.predict_match(match_id=999, user_id=456)

    @pytest.mark.asyncio
    async def test_batch_predict(
        self, service, sample_match, sample_strategy, sample_prediction_output
    ):
        """测试：批量预测"""
        # Given
        match_ids = [101, 102, 103]
        predictions = []
        for i in range(3):
            pred = Mock(spec=Prediction)
            pred.id = i + 1
            predictions.append(pred)

        service._match_repository.get_by_id = AsyncMock(return_value=sample_match)
        service._get_team_info = AsyncMock(return_value=sample_team)
        service._get_or_create_strategy = AsyncMock(return_value=sample_strategy)
        service._prepare_prediction_input = AsyncMock()
        sample_strategy.predict.return_value = sample_prediction_output
        service._prediction_domain_service.create_prediction = Mock(
            side_effect=predictions.append
        )
        service._prediction_repository.create = AsyncMock()
        service._log_prediction_details = AsyncMock()

        # When
        result = await service.batch_predict(
            match_ids, user_id=456, strategy_name="test"
        )

        # Then
        assert len(result) == 3
        assert service._match_repository.get_by_id.call_count == 3
        assert service._prediction_repository.create.call_count == 3

    @pytest.mark.asyncio
    async def test_get_or_create_strategy_existing(self, service, sample_strategy):
        """测试：获取已存在的策略"""
        # Given
        service._current_strategies["test_strategy"] = sample_strategy

        # When
        result = await service._get_or_create_strategy("test_strategy")

        # Then
        assert result == sample_strategy
        # 不应该从工厂获取
        service._strategy_factory.get_strategy.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_or_create_strategy_new(self, service, sample_strategy):
        """测试：获取新策略"""
        # Given
        service._strategy_factory.get_strategy = AsyncMock(return_value=sample_strategy)

        # When
        result = await service._get_or_create_strategy("new_strategy")

        # Then
        assert result == sample_strategy
        service._strategy_factory.get_strategy.assert_called_once_with("new_strategy")
        assert "new_strategy" in service._current_strategies

    @pytest.mark.asyncio
    async def test_prepare_prediction_input(self, service):
        """测试：准备预测输入"""
        # Given
        context = PredictionContext(
            match=Mock(), home_team=Mock(), away_team=Mock(), user_id=123
        )

        # When
        result = await service._prepare_prediction_input(context)

        # Then
        assert isinstance(result, PredictionInput)
        assert result.match == context.match
        assert result.home_team == context.home_team
        assert result.away_team == context.away_team

    def test_get_team_info(self, service):
        """测试：获取球队信息"""
        # Given
        team = Mock()
        service._match_repository.get_team = AsyncMock(return_value=team)

        # When
        result = service._get_team_info(123)

        # Then
        assert result == team
        service._match_repository.get_team.assert_called_once_with(123)

    def test_service_attributes(self, service):
        """测试：服务属性"""
        assert hasattr(service, "_strategy_factory")
        assert hasattr(service, "_prediction_domain_service")
        assert hasattr(service, "_match_repository")
        assert hasattr(service, "_prediction_repository")
        assert hasattr(service, "_current_strategies")
        assert hasattr(service, "_default_strategy")

    def test_default_strategy_value(self, service):
        """测试：默认策略值"""
        assert service._default_strategy == "test_strategy"

    def test_current_strategies_initially_empty(self, service):
        """测试：当前策略字典初始为空"""
        assert service._current_strategies == {}

    @pytest.mark.asyncio
    async def test_prediction_context_creation(
        self, service, sample_match, sample_team
    ):
        """测试：预测上下文创建"""
        # Given
        service._match_repository.get_by_id = AsyncMock(return_value=sample_match)
        service._get_team_info = AsyncMock(return_value=sample_team)
        service._get_or_create_strategy = AsyncMock()

        # When
        await service.predict_match(match_id=123, user_id=456)

        # Then
        # 验证上下文被正确创建
        service._prepare_prediction_input.assert_called_once()
        call_args = service._prepare_prediction_input.call_args[0][0]
        assert isinstance(call_args, PredictionContext)
        assert call_args.user_id == 456

    @pytest.mark.asyncio
    async def test_prediction_output_processing(
        self, service, sample_prediction_output
    ):
        """测试：预测输出处理"""
        # Given
        prediction = Mock()
        service._prediction_domain_service.create_prediction = Mock(
            return_value=prediction
        )

        # When
        await service._process_prediction_output(
            sample_prediction_output, Mock(), 123, 456
        )

        # Then
        service._prediction_domain_service.create_prediction.assert_called_once_with(
            user_id=456,
            match=Mock(),
            predicted_home=sample_prediction_output.predicted_home_score,
            predicted_away=sample_prediction_output.predicted_away_score,
            confidence=sample_prediction_output.confidence,
            notes=None,
        )

    @pytest.mark.asyncio
    async def test_log_prediction_details(self, service):
        """测试：记录预测详情"""
        # Given
        prediction = Mock()
        output = Mock()
        service.log_prediction_details = AsyncMock()

        # When
        await service._log_prediction_details(prediction, output, "test_strategy")

        # Then
        service.log_prediction_details.assert_called_once()

    def test_strategy_selection_priority(self, service):
        """测试：策略选择优先级"""
        # When strategy_name is provided, it should be used
        assert service._select_strategy("custom", "default") == "custom"
        # When strategy_name is None, default should be used
        assert service._select_strategy(None, "default") == "default"

    def test_strategy_selection_with_none_value(self, service):
        """测试：策略选择（处理None值）"""
        # Given
        strategy = Mock()
        service._current_strategies["test"] = strategy

        # When
        result = service._select_strategy("test", None)

        # Then
        assert result == "test"

    def test_strategy_factory_dependency(self):
        """测试：策略工厂依赖注入"""
        # Given & When
        with patch(
            "src.services.strategy_prediction_service.PredictionStrategyFactory"
        ) as mock_factory:
            mock_service_instance = Mock()
            mock_factory.return_value = mock_service_instance

        # Then
        assert isinstance(mock_service_instance, PredictionStrategyFactory)
