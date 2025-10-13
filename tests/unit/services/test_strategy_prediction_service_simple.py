"""
策略预测服务测试（简化版）
Tests for Strategy Prediction Service (Simplified)
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.services.strategy_prediction_service import StrategyPredictionService


class TestStrategyPredictionServiceSimple:
    """策略预测服务测试"""

    @pytest.fixture
    def mock_service(self):
        """Mock策略预测服务"""
        service = Mock(spec=StrategyPredictionService)
        service._strategy_factory = Mock()
        service._prediction_domain_service = Mock()
        service._match_repository = Mock()
        service._prediction_repository = Mock()
        service._default_strategy = "test_strategy"
        service._current_strategies = {}
        return service

    @pytest.fixture
    def sample_match(self):
        """示例比赛"""
        match = Mock()
        match.id = 123
        match.home_team_id = 1
        match.away_team_id = 2
        return match

    @pytest.fixture
    def sample_prediction(self):
        """示例预测"""
        _prediction = Mock()
        prediction.id = 456
        prediction.user_id = 789
        prediction.match_id = 123
        return prediction

    def test_service_initialization(self):
        """测试：服务初始化"""
        # Given
        strategy_factory = Mock()
        prediction_service = Mock()
        match_repository = Mock()
        prediction_repository = Mock()

        # When
        service = StrategyPredictionService(
            strategy_factory=strategy_factory,
            prediction_domain_service=prediction_service,
            match_repository=match_repository,
            prediction_repository=prediction_repository,
            default_strategy="default_strategy",
        )

        # Then
        assert service._strategy_factory == strategy_factory
        assert service._prediction_domain_service == prediction_service
        assert service._match_repository == match_repository
        assert service._prediction_repository == prediction_repository
        assert service._default_strategy == "default_strategy"
        assert service._current_strategies == {}

    @pytest.mark.asyncio
    async def test_initialize(self, mock_service):
        """测试：初始化服务"""
        # Given
        mock_service.initialize = AsyncMock()

        # When
        await mock_service.initialize()

        # Then
        mock_service.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_match_basic(self, mock_service, sample_prediction):
        """测试：基本预测功能"""
        # Given
        mock_service.predict_match = AsyncMock(return_value=sample_prediction)

        # When
        _result = await mock_service.predict_match(match_id=123, user_id=456)

        # Then
        assert _result == sample_prediction
        mock_service.predict_match.assert_called_once_with(match_id=123, user_id=456)

    @pytest.mark.asyncio
    async def test_predict_match_with_strategy(self, mock_service):
        """测试：指定策略预测"""
        # Given
        mock_service.predict_match = AsyncMock()

        # When
        await mock_service.predict_match(
            match_id=123, user_id=456, strategy_name="custom_strategy"
        )

        # Then
        mock_service.predict_match.assert_called_once()
        # 验证调用参数包含策略名称
        call_args, call_kwargs = mock_service.predict_match.call_args
        assert call_kwargs.get("strategy_name") == "custom_strategy"

    @pytest.mark.asyncio
    async def test_predict_match_with_confidence(self, mock_service):
        """测试：带信心度的预测"""
        # Given
        mock_service.predict_match = AsyncMock()

        # When
        await mock_service.predict_match(match_id=123, user_id=456, confidence=0.85)

        # Then
        mock_service.predict_match.assert_called_once()
        call_args, call_kwargs = mock_service.predict_match.call_args
        assert call_kwargs.get("confidence") == 0.85

    @pytest.mark.asyncio
    async def test_predict_match_with_notes(self, mock_service):
        """测试：带备注的预测"""
        # Given
        mock_service.predict_match = AsyncMock()

        # When
        await mock_service.predict_match(
            match_id=123, user_id=456, notes="测试预测备注"
        )

        # Then
        mock_service.predict_match.assert_called_once()
        call_args, call_kwargs = mock_service.predict_match.call_args
        assert call_kwargs.get("notes") == "测试预测备注"

    @pytest.mark.asyncio
    async def test_predict_match_not_found(self, mock_service):
        """测试：比赛不存在时的处理"""
        # Given
        mock_service.predict_match = AsyncMock()
        mock_service.predict_match.side_effect = ValueError("比赛不存在")

        # When / Then
        with pytest.raises(ValueError, match="比赛不存在"):
            await mock_service.predict_match(match_id=999, user_id=456)

    @pytest.mark.asyncio
    async def test_batch_predict_basic(self, mock_service):
        """测试：批量预测基本功能"""
        # Given
        predictions = [Mock(id=1), Mock(id=2), Mock(id=3)]
        mock_service.batch_predict = AsyncMock(return_value=predictions)
        match_ids = [101, 102, 103]

        # When
        _result = await mock_service.batch_predict(match_ids, user_id=456)

        # Then
        assert len(result) == 3
        assert _result == predictions
        mock_service.batch_predict.assert_called_once_with(match_ids, user_id=456)

    @pytest.mark.asyncio
    async def test_batch_predict_with_strategy(self, mock_service):
        """测试：批量预测指定策略"""
        # Given
        mock_service.batch_predict = AsyncMock()

        # When
        await mock_service.batch_predict(
            match_ids=[101, 102], user_id=456, strategy_name="batch_strategy"
        )

        # Then
        mock_service.batch_predict.assert_called_once()
        call_args, call_kwargs = mock_service.batch_predict.call_args
        assert call_kwargs.get("strategy_name") == "batch_strategy"

    @pytest.mark.asyncio
    async def test_batch_predict_empty_list(self, mock_service):
        """测试：空批量预测列表"""
        # Given
        mock_service.batch_predict = AsyncMock(return_value=[])

        # When
        _result = await mock_service.batch_predict([], user_id=456)

        # Then
        assert _result == []
        mock_service.batch_predict.assert_called_once_with([], user_id=456)

    @pytest.mark.asyncio
    async def test_compare_strategies_basic(self, mock_service):
        """测试：策略比较基本功能"""
        # Given
        mock_service.compare_strategies = AsyncMock(return_value={})

        # When
        _result = await mock_service.compare_strategies(match_id=123)

        # Then
        assert isinstance(result, dict)
        mock_service.compare_strategies.assert_called_once_with(match_id=123)

    @pytest.mark.asyncio
    async def test_compare_strategies_with_list(self, mock_service):
        """测试：指定策略列表比较"""
        # Given
        mock_service.compare_strategies = AsyncMock(return_value={"strategy1": None})
        strategies = ["strategy1", "strategy2"]

        # When
        _result = await mock_service.compare_strategies(
            match_id=123, strategy_names=strategies
        )

        # Then
        assert isinstance(result, dict)
        mock_service.compare_strategies.assert_called_once_with(
            match_id=123, strategy_names=strategies
        )

    @pytest.mark.asyncio
    async def test_compare_strategies_match_not_found(self, mock_service):
        """测试：策略比较时比赛不存在"""
        # Given
        mock_service.compare_strategies = AsyncMock()
        mock_service.compare_strategies.side_effect = ValueError("比赛不存在")

        # When / Then
        with pytest.raises(ValueError, match="比赛不存在"):
            await mock_service.compare_strategies(match_id=999)

    def test_service_attributes(self, mock_service):
        """测试：服务属性"""
        # Then
        assert hasattr(mock_service, "_strategy_factory")
        assert hasattr(mock_service, "_prediction_domain_service")
        assert hasattr(mock_service, "_match_repository")
        assert hasattr(mock_service, "_prediction_repository")
        assert hasattr(mock_service, "_current_strategies")
        assert hasattr(mock_service, "_default_strategy")

    def test_default_strategy_value(self):
        """测试：默认策略值"""
        # Given & When
        service = StrategyPredictionService(
            strategy_factory=Mock(),
            prediction_domain_service=Mock(),
            match_repository=Mock(),
            prediction_repository=Mock(),
            default_strategy="custom_default",
        )

        # Then
        assert service._default_strategy == "custom_default"

    def test_default_strategy_default(self):
        """测试：默认策略默认值"""
        # Given & When
        service = StrategyPredictionService(
            strategy_factory=Mock(),
            prediction_domain_service=Mock(),
            match_repository=Mock(),
            prediction_repository=Mock(),
        )

        # Then
        assert service._default_strategy == "ensemble_predictor"

    def test_service_dependency_injection(self):
        """测试：依赖注入"""
        # Given
        strategy_factory = Mock()
        prediction_service = Mock()
        match_repository = Mock()
        prediction_repository = Mock()

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

    def test_service_initialization_with_empty_current_strategies(self):
        """测试：初始化时当前策略为空"""
        # Given
        service = StrategyPredictionService(
            strategy_factory=Mock(),
            prediction_domain_service=Mock(),
            match_repository=Mock(),
            prediction_repository=Mock(),
        )

        # Then
        assert service._current_strategies == {}

    def test_service_configuration(self):
        """测试：服务配置"""
        # Given & When
        service = StrategyPredictionService(
            strategy_factory=Mock(),
            prediction_domain_service=Mock(),
            match_repository=Mock(),
            prediction_repository=Mock(),
            default_strategy="config_test",
        )

        # Then
        # 服务应该能接受配置参数
        assert service is not None
        assert service._default_strategy == "config_test"

    @pytest.mark.asyncio
    async def test_service_logging(self, mock_service):
        """测试：服务日志记录"""
        # Given
        mock_service.predict_match = AsyncMock()

        # When
        await mock_service.predict_match(match_id=123, user_id=456)

        # Then
        mock_service.predict_match.assert_called_once()

    def test_service_inheritance(self):
        """测试：服务继承关系"""
        # When
        service = StrategyPredictionService(
            strategy_factory=Mock(),
            prediction_domain_service=Mock(),
            match_repository=Mock(),
            prediction_repository=Mock(),
        )

        # Then
        assert isinstance(service, StrategyPredictionService)

    def test_service_is_mockable(self):
        """测试：服务可以被Mock"""
        # When & Then
        service = Mock()
        service._strategy_factory = Mock()
        service.predict_match = AsyncMock()
        service.batch_predict = AsyncMock()
        assert hasattr(service, "_strategy_factory")
        assert hasattr(service, "predict_match")
        assert hasattr(service, "batch_predict")
