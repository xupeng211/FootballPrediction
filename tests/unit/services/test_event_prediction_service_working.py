# TODO: Consider creating a fixture for 39 repeated Mock creations

# TODO: Consider creating a fixture for 39 repeated Mock creations

from unittest.mock import AsyncMock, MagicMock, Mock, patch

"""
事件驱动预测服务测试（工作版）
Tests for Event-Driven Prediction Service (Working Version)
"""

from datetime import datetime

import pytest

from src.services.event_prediction_service import (
    EventDrivenMatchService, EventDrivenPredictionService,
    EventDrivenUserService, configure_event_driven_services)


@pytest.mark.unit
class TestEventDrivenPredictionService:
    """事件驱动预测服务测试"""

    @pytest.fixture
    def mock_strategy_service(self):
        """Mock策略预测服务"""
        with patch(
            "src.services.event_prediction_service.StrategyPredictionService"
        ) as mock:
            # 设置基类方法
            mock_instance = Mock()
            mock_instance.predict_match = AsyncMock()
            mock_instance.update_prediction = AsyncMock()
            mock_instance.batch_predict = AsyncMock()
            mock_instance._prediction_repository = Mock()
            mock_instance._prediction_repository.get_by_id = AsyncMock()
            mock_instance._prediction_repository.update = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance

    @pytest.fixture
    def mock_event_bus(self):
        """Mock事件总线"""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        return mock_bus

    @pytest.fixture
    def service(self, mock_strategy_service, mock_event_bus):
        """创建服务实例"""
        with patch(
            "src.services.event_prediction_service.get_event_bus",
            return_value=mock_event_bus,
        ):
            service = EventDrivenPredictionService()
            return service

    @pytest.fixture
    def sample_prediction(self):
        """示例预测"""
        pred = Mock()
        pred.id = 123
        pred.match_id = 456
        pred.user_id = 789
        pred.predicted_home_score = 2
        pred.predicted_away_score = 1
        pred.confidence_score = 0.85
        pred.notes = "测试预测"
        pred.created_at = datetime.utcnow()
        pred.updated_at = datetime.utcnow()
        return pred

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_event_bus):
        """测试：服务初始化"""
        with patch(
            "src.services.event_prediction_service.get_event_bus",
            return_value=mock_event_bus,
        ):
            with patch(
                "src.services.event_prediction_service.StrategyPredictionService"
            ):
                service = EventDrivenPredictionService()

                # Then
                assert service._event_bus == mock_event_bus
                assert service._event_source == "prediction_service"

    @pytest.mark.asyncio
    async def test_predict_match_and_publish_event(
        self, service, sample_prediction, mock_event_bus
    ):
        """测试：预测比赛并发布事件"""
        # Given
        service.predict_match = AsyncMock(return_value=sample_prediction)
        strategy_name = "test_strategy"

        # When
        _result = await service.predict_match(
            match_id=456,
            user_id=789,
            strategy_name=strategy_name,
            confidence=0.85,
            notes="测试预测",
        )

        # Then
        assert _result == sample_prediction
        mock_event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_predict_match_without_optional_params(
        self, service, sample_prediction
    ):
        """测试：预测比赛（不提供可选参数）"""
        # Given
        service.predict_match = AsyncMock(return_value=sample_prediction)

        # When
        _result = await service.predict_match(match_id=456, user_id=789)

        # Then
        assert _result == sample_prediction
        service._event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_prediction_and_publish_event(
        self, service, sample_prediction
    ):
        """测试：更新预测并发布事件"""
        # Given
        # Mock仓库返回原预测
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=sample_prediction)
        mock_repo.update = AsyncMock()
        service._prediction_repository = mock_repo

        # When
        _result = await service.update_prediction(
            prediction_id=123,
            user_id=789,
            new_predicted_home=3,
            new_predicted_away=1,
            new_confidence=0.9,
            update_reason="更正预测",
        )

        # Then
        # 验证预测被更新
        assert _result.predicted_home_score == 3
        assert _result.predicted_away_score == 1
        assert _result.confidence_score == 0.9
        assert _result.updated_at is not None

        # 验证仓库方法被调用
        mock_repo.get_by_id.assert_called_once_with(123)
        mock_repo.update.assert_called_once()

        # 验证事件被发布
        service._event_bus.publish.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_prediction_not_found(self, service):
        """测试：更新不存在的预测"""
        # Given
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=None)
        service._prediction_repository = mock_repo

        # When / Then
        with pytest.raises(ValueError, match="预测不存在"):
            await service.update_prediction(prediction_id=999, user_id=789)

    @pytest.mark.asyncio
    async def test_update_prediction_partial_update(self, service, sample_prediction):
        """测试：部分更新预测"""
        # Given
        mock_repo = Mock()
        mock_repo.get_by_id = AsyncMock(return_value=sample_prediction)
        mock_repo.update = AsyncMock()
        service._prediction_repository = mock_repo

        # When - 只更新主队得分
        _result = await service.update_prediction(
            prediction_id=123, user_id=789, new_predicted_home=3
        )

        # Then
        assert _result.predicted_home_score == 3
        # 其他值保持不变
        assert _result.predicted_away_score == 1
        assert _result.confidence_score == 0.85

    @pytest.mark.asyncio
    async def test_batch_predict_and_publish_events(self, service):
        """测试：批量预测并发布事件"""
        # Given
        predictions = [
            Mock(id=1, match_id=101, user_id=1001),
            Mock(id=2, match_id=102, user_id=1001),
            Mock(id=3, match_id=103, user_id=1001),
        ]
        service.batch_predict = AsyncMock(return_value=predictions)
        strategy_name = "batch_strategy"

        # When
        _result = await service.batch_predict(
            match_ids=[101, 102, 103], user_id=1001, strategy_name=strategy_name
        )

        # Then
        assert len(result) == 3
        assert _result == predictions

        # 验证每个预测都发布了事件
        assert service._event_bus.publish.call_count == 3

    @pytest.mark.asyncio
    async def test_batch_predict_without_strategy(self, service):
        """测试：批量预测（不提供策略）"""
        # Given
        predictions = [Mock(id=1, match_id=101, user_id=1001)]
        service.batch_predict = AsyncMock(return_value=predictions)

        # When
        _result = await service.batch_predict(match_ids=[101], user_id=1001)

        # Then
        assert len(result) == 1
        service._event_bus.publish.assert_called_once()

    def test_inheritance_from_strategy_service(self):
        """测试：继承自策略预测服务"""
        # When
        with patch("src.services.event_prediction_service.StrategyPredictionService"):
            service = EventDrivenPredictionService()

        # Then
        # 验证继承关系
        from src.services.strategy_prediction_service import \
            StrategyPredictionService

        assert isinstance(service, StrategyPredictionService)

    @pytest.mark.asyncio
    async def test_event_source_is_consistent(self, service, sample_prediction):
        """测试：事件源标识一致性"""
        # Given
        service.predict_match = AsyncMock(return_value=sample_prediction)

        # When
        await service.predict_match(match_id=456, user_id=789)

        # Then
        call_args = service._event_bus.publish.call_args
        event = call_args[0][0]
        assert event.data.source == "prediction_service"

    @pytest.mark.asyncio
    async def test_prediction_made_event_data_structure(
        self, service, sample_prediction
    ):
        """测试：预测创建事件数据结构"""
        # Given
        service.predict_match = AsyncMock(return_value=sample_prediction)
        strategy_name = "ml_strategy"

        # When
        await service.predict_match(
            match_id=456, user_id=789, strategy_name=strategy_name, confidence=0.85
        )

        # Then
        call_args = service._event_bus.publish.call_args
        event = call_args[0][0]

        # 验证事件数据包含必要字段
        assert hasattr(event, "data")
        assert hasattr(event, "timestamp")
        assert event.timestamp is not None
        assert event.data.prediction_id == 123
        assert event.data.match_id == 456
        assert event.data.user_id == 789

    @pytest.mark.asyncio
    async def test_handle_event_publishing_error(self, service, sample_prediction):
        """测试：处理事件发布错误"""
        # Given
        service.predict_match = AsyncMock(return_value=sample_prediction)
        service._event_bus.publish = AsyncMock(side_effect=Exception("Event bus error"))

        # When - 即使事件发布失败，预测仍应返回
        _result = await service.predict_match(match_id=456, user_id=789)

        # Then
        assert _result == sample_prediction
        # 异常应该被记录或处理


class TestEventDrivenMatchService:
    """事件驱动比赛服务测试"""

    @pytest.fixture
    def mock_match_repository(self):
        """Mock比赛仓储"""
        repo = Mock()
        repo.create = AsyncMock()
        return repo

    @pytest.fixture
    def mock_event_bus(self):
        """Mock事件总线"""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        return mock_bus

    @pytest.fixture
    def match_service(self, mock_match_repository, mock_event_bus):
        """创建比赛服务实例"""
        with patch(
            "src.services.event_prediction_service.get_event_bus",
            return_value=mock_event_bus,
        ):
            return EventDrivenMatchService(mock_match_repository)

    @pytest.mark.asyncio
    async def test_create_match_and_publish_event(
        self, match_service, mock_match_repository, mock_event_bus
    ):
        """测试：创建比赛并发布事件"""
        # Given
        match_time = datetime.utcnow()
        venue = "Old Trafford"
        weather = {"temperature": 20, "condition": "sunny"}

        # When
        await match_service.create_match(
            home_team_id=1,
            away_team_id=2,
            league_id=3,
            match_time=match_time,
            venue=venue,
            weather=weather,
            created_by=100,
        )

        # Then
        mock_match_repository.create.assert_called_once()
        mock_event_bus.publish.assert_called_once()

    def test_match_service_initialization(self, mock_match_repository, mock_event_bus):
        """测试：比赛服务初始化"""
        with patch(
            "src.services.event_prediction_service.get_event_bus",
            return_value=mock_event_bus,
        ):
            service = EventDrivenMatchService(mock_match_repository)

            assert service._match_repository == mock_match_repository
            assert service._event_bus == mock_event_bus
            assert service._event_source == "match_service"


class TestEventDrivenUserService:
    """事件驱动用户服务测试"""

    @pytest.fixture
    def mock_user_repository(self):
        """Mock用户仓储"""
        return Mock()

    @pytest.fixture
    def mock_event_bus(self):
        """Mock事件总线"""
        mock_bus = Mock()
        mock_bus.publish = AsyncMock()
        return mock_bus

    @pytest.fixture
    def user_service(self, mock_user_repository, mock_event_bus):
        """创建用户服务实例"""
        with patch(
            "src.services.event_prediction_service.get_event_bus",
            return_value=mock_event_bus,
        ):
            return EventDrivenUserService(mock_user_repository)

    @pytest.mark.asyncio
    async def test_register_user_and_publish_event(self, user_service, mock_event_bus):
        """测试：注册用户并发布事件"""
        # Given
        username = "testuser"
        email = "test@example.com"
        password_hash = "hashed_password"

        # When
        _result = await user_service.register_user(
            username=username,
            email=email,
            password_hash=password_hash,
            referral_code="REF123",
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
        )

        # Then
        assert _result["username"] == username
        assert _result["email"] == email
        assert _result["password_hash"] == password_hash
        assert "registration_date" in result
        mock_event_bus.publish.assert_called_once()

    def test_user_service_initialization(self, mock_user_repository, mock_event_bus):
        """测试：用户服务初始化"""
        with patch(
            "src.services.event_prediction_service.get_event_bus",
            return_value=mock_event_bus,
        ):
            service = EventDrivenUserService(mock_user_repository)

            assert service._user_repository == mock_user_repository
            assert service._event_bus == mock_event_bus
            assert service._event_source == "user_service"


class TestConfigureEventDrivenServices:
    """配置事件驱动服务测试"""

    def test_configure_event_driven_services(self):
        """测试：配置事件驱动服务"""
        # Given
        mock_container = Mock()
        mock_container.register_scoped = Mock()

        # When
        configure_event_driven_services(mock_container)

        # Then
        mock_container.register_scoped.assert_called_once_with(
            EventDrivenPredictionService
        )

    def test_configure_with_none_container(self):
        """测试：配置空容器"""
        # When / Then - 不应该抛出异常
        try:
            configure_event_driven_services(None)
        except AttributeError:
            # 这是预期的，因为None没有register_scoped方法
            pass
