# TODO: Consider creating a fixture for 28 repeated Mock creations

# TODO: Consider creating a fixture for 28 repeated Mock creations

from unittest.mock import Mock, patch

"""
预测领域服务测试
Tests for Prediction Domain Service
"""

from datetime import datetime, timedelta

import pytest

from src.domain.events.prediction_events import (PredictionCancelledEvent,
                                                 PredictionCreatedEvent,
                                                 PredictionEvaluatedEvent,
                                                 PredictionExpiredEvent,
                                                 PredictionPointsAdjustedEvent,
                                                 PredictionUpdatedEvent)
from src.domain.models.match import Match, MatchScore, MatchStatus
from src.domain.models.prediction import Prediction, PredictionStatus
from src.domain.services.prediction_service import PredictionDomainService


@pytest.mark.unit
class TestPredictionDomainService:
    """预测领域服务测试"""

    @pytest.fixture
    def service(self):
        """创建服务实例"""
        return PredictionDomainService()

    @pytest.fixture
    def future_match(self):
        """创建未来的比赛"""
        match_date = datetime.utcnow() + timedelta(days=1)
        match = Match(
            home_team_id=1, away_team_id=2, match_date=match_date, season="2023-2024"
        )
        match.id = 100
        return match

    @pytest.fixture
    def past_match(self):
        """创建过去的比赛"""
        match_date = datetime.utcnow() - timedelta(days=1)
        match = Match(
            home_team_id=1, away_team_id=2, match_date=match_date, season="2023-2024"
        )
        match.id = 101
        return match

    @pytest.fixture
    def scheduled_match(self):
        """创建已安排的比赛"""
        match_date = datetime.utcnow() + timedelta(days=1)
        match = Match(
            home_team_id=1, away_team_id=2, match_date=match_date, season="2023-2024"
        )
        match.id = 100
        match.status = MatchStatus.SCHEDULED
        return match

    @pytest.fixture
    def mock_prediction(self):
        """创建Mock预测对象"""
        pred = Mock(spec=Prediction)
        pred.id = 12345
        pred.user_id = 1001
        pred.match_id = 100
        pred.status = PredictionStatus.PENDING
        pred.score = Mock()
        pred.score.predicted_home = 2
        pred.score.predicted_away = 1
        pred.confidence = Mock()
        pred.confidence.score = 0.8
        pred.points = Mock()
        pred.points.total = 10
        pred.cancelled_at = None
        return pred

    def test_create_prediction_should_raise_when_match_in_past(
        self, service, past_match
    ):
        """测试：对过去的比赛进行预测时应抛出错误"""
        # When / Then
        with pytest.raises(ValueError, match="预测必须在比赛开始前提交"):
            service.create_prediction(
                user_id=1001, match=past_match, predicted_home=2, predicted_away=1
            )

    def test_create_prediction_should_raise_when_negative_scores(
        self, service, future_match
    ):
        """测试：预测比分为负数时应抛出错误"""
        # When / Then
        with pytest.raises(ValueError, match="预测比分不能为负数"):
            service.create_prediction(
                user_id=1001, match=future_match, predicted_home=-1, predicted_away=2
            )

    def test_create_prediction_should_raise_when_confidence_out_of_range(
        self, service, future_match
    ):
        """测试：信心度超出范围时应抛出错误"""
        # When / Then
        with pytest.raises(ValueError, match="信心度必须在0-1之间"):
            service.create_prediction(
                user_id=1001,
                match=future_match,
                predicted_home=2,
                predicted_away=1,
                confidence=1.5,
            )

    def test_create_prediction_should_raise_when_match_id_is_none(self, service):
        """测试：比赛ID为空时应抛出错误"""
        # Given
        match = Mock()
        match.id = None
        match.status = MatchStatus.SCHEDULED
        match.match_date = datetime.utcnow() + timedelta(days=1)

        # When / Then
        with pytest.raises(ValueError, match="比赛ID不能为空"):
            service.create_prediction(
                user_id=1001, match=match, predicted_home=2, predicted_away=1
            )

    @patch("src.domain.services.prediction_service.Prediction")
    def test_create_prediction_success(
        self, mock_prediction_class, service, scheduled_match
    ):
        """测试：成功创建预测"""
        # Given
        mock_pred = Mock()
        mock_pred.id = 12345
        mock_pred.make_prediction = Mock()
        mock_prediction_class.return_value = mock_pred

        # When
        _prediction = service.create_prediction(
            user_id=1001,
            match=scheduled_match,
            predicted_home=2,
            predicted_away=1,
            confidence=0.8,
        )

        # Then
        assert _prediction == mock_pred
        mock_pred.make_prediction.assert_called_once_with(
            predicted_home=2, predicted_away=1, confidence=0.8
        )
        assert len(service._events) == 1
        assert isinstance(service._events[0], PredictionCreatedEvent)

    def test_update_prediction_with_valid_data(self, service, mock_prediction):
        """测试：更新预测"""
        # Given
        mock_prediction.status = PredictionStatus.PENDING
        mock_prediction.score = Mock()
        mock_prediction.score.predicted_home = 2
        mock_prediction.score.predicted_away = 1
        mock_prediction.make_prediction = Mock()
        service._events.clear()

        # When
        service.update_prediction(
            _prediction=mock_prediction,
            new_predicted_home=3,
            new_predicted_away=1,
            new_confidence=0.9,
        )

        # Then
        mock_prediction.make_prediction.assert_called_once_with(3, 1, 0.9)
        assert len(service._events) == 1
        assert isinstance(service._events[0], PredictionUpdatedEvent)

    def test_update_prediction_should_raise_when_not_pending(
        self, service, mock_prediction
    ):
        """测试：更新非待定状态的预测时应抛出错误"""
        # Given
        mock_prediction.status = PredictionStatus.EVALUATED

        # When / Then
        with pytest.raises(ValueError, match="只能更新待处理的预测"):
            service.update_prediction(
                _prediction=mock_prediction, new_predicted_home=3, new_predicted_away=1
            )

    def test_update_prediction_should_raise_when_negative_scores(
        self, service, mock_prediction
    ):
        """测试：更新预测时使用负数比分"""
        # Given
        mock_prediction.status = PredictionStatus.PENDING

        # When / Then
        with pytest.raises(ValueError, match="预测比分不能为负数"):
            service.update_prediction(
                _prediction=mock_prediction, new_predicted_home=-1, new_predicted_away=1
            )

    def test_evaluate_prediction(self, service, mock_prediction):
        """测试：评估预测"""
        # Given
        mock_prediction.status = PredictionStatus.PENDING
        mock_prediction.evaluate = Mock()
        mock_prediction.points = Mock()
        mock_prediction.points.total = 10
        mock_prediction.score = Mock()
        mock_prediction.score.is_correct_result = True
        service._events.clear()

        # When
        service.evaluate_prediction(mock_prediction, actual_home=2, actual_away=1)

        # Then
        mock_prediction.evaluate.assert_called_once_with(2, 1, None)
        assert len(service._events) == 1
        assert isinstance(service._events[0], PredictionEvaluatedEvent)

    def test_evaluate_prediction_should_raise_when_not_pending(
        self, service, mock_prediction
    ):
        """测试：评估已评估的预测时应抛出错误"""
        # Given
        mock_prediction.status = PredictionStatus.EVALUATED

        # When / Then
        with pytest.raises(ValueError, match="只能评估待处理的预测"):
            service.evaluate_prediction(mock_prediction, actual_home=2, actual_away=1)

    def test_cancel_prediction(self, service, mock_prediction):
        """测试：取消预测"""
        # Given
        mock_prediction.status = PredictionStatus.PENDING
        mock_prediction.cancel = Mock()
        service._events.clear()

        # When
        service.cancel_prediction(mock_prediction, reason="用户取消")

        # Then
        mock_prediction.cancel.assert_called_once()
        assert len(service._events) == 1
        assert isinstance(service._events[0], PredictionCancelledEvent)

    def test_cancel_prediction_should_raise_when_not_pending(
        self, service, mock_prediction
    ):
        """测试：取消非待定状态的预测时应抛出错误"""
        # Given
        mock_prediction.status = PredictionStatus.EVALUATED

        # When / Then
        with pytest.raises(ValueError, match="只能取消待处理的预测"):
            service.cancel_prediction(mock_prediction, "用户取消")

    def test_expire_prediction(self, service, mock_prediction):
        """测试：使预测过期"""
        # Given
        mock_prediction.status = PredictionStatus.PENDING
        service._events.clear()

        # When
        service.expire_prediction(mock_prediction)

        # Then
        assert mock_prediction.status == PredictionStatus.EXPIRED
        assert mock_prediction.cancelled_at is not None
        assert len(service._events) == 1
        assert isinstance(service._events[0], PredictionExpiredEvent)

    def test_expire_prediction_should_raise_when_not_pending(
        self, service, mock_prediction
    ):
        """测试：过期非待定状态的预测时应抛出错误"""
        # Given
        mock_prediction.status = PredictionStatus.EVALUATED

        # When / Then
        with pytest.raises(ValueError, match="只能使待处理的预测过期"):
            service.expire_prediction(mock_prediction)

    def test_adjust_prediction_points(self, service, mock_prediction):
        """测试：调整预测积分"""
        # Given
        mock_prediction.status = PredictionStatus.EVALUATED
        mock_prediction.points = Mock()
        mock_prediction.points.total = 5
        service._events.clear()

        # When
        service.adjust_prediction_points(
            mock_prediction, new_points=10, adjustment_reason="系统修正"
        )

        # Then
        assert mock_prediction.points.total == 10
        assert len(service._events) == 1
        assert isinstance(service._events[0], PredictionPointsAdjustedEvent)

    def test_adjust_prediction_points_should_raise_when_not_evaluated(
        self, service, mock_prediction
    ):
        """测试：调整未评估的预测积分时应抛出错误"""
        # Given
        mock_prediction.status = PredictionStatus.PENDING

        # When / Then
        with pytest.raises(ValueError, match="只能调整已评估的预测积分"):
            service.adjust_prediction_points(
                mock_prediction, new_points=10, adjustment_reason="系统修正"
            )

    def test_calculate_prediction_confidence(self, service):
        """测试：计算预测信心度"""
        # Given
        user_history = {"accuracy_rate": 0.7}
        match_importance = 0.8

        # When
        confidence = service.calculate_prediction_confidence(
            user_history=user_history, match重要性=match_importance, team_form_diff=0.2
        )

        # Then
        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.5  # 用户准确率高，应该增加信心度

    def test_validate_prediction_rules_valid(self, service, mock_prediction):
        """测试：验证预测规则 - 有效情况"""
        # Given
        mock_prediction.confidence = Mock()
        mock_prediction.confidence.value = Mock()
        mock_prediction.confidence.value.__float__ = Mock(return_value=0.8)
        mock_prediction.score = Mock()
        mock_prediction.score.predicted_home = 2
        mock_prediction.score.predicted_away = 1

        # When
        errors = service.validate_prediction_rules(
            _prediction=mock_prediction,
            user_predictions_today=5,
            max_predictions_per_day=10,
        )

        # Then
        assert len(errors) == 0  # 应该没有错误

    def test_validate_prediction_rules_exceeds_daily_limit(self, service):
        """测试：验证预测规则 - 超出每日限制"""
        # Given
        mock_pred = Mock()
        mock_pred.score = Mock()
        mock_pred.score.predicted_home = 2
        mock_pred.score.predicted_away = 1
        mock_pred.confidence = None

        # When
        errors = service.validate_prediction_rules(
            _prediction=mock_pred, user_predictions_today=10, max_predictions_per_day=10
        )

        # Then
        assert len(errors) > 0
        assert "每日预测次数" in errors[0]

    def test_validate_prediction_rules_negative_scores(self, service):
        """测试：验证预测规则 - 负数比分"""
        # Given
        mock_pred = Mock()
        mock_pred.score = Mock()
        mock_pred.score.predicted_home = -1
        mock_pred.score.predicted_away = 1
        mock_pred.confidence = None

        # When
        errors = service.validate_prediction_rules(
            _prediction=mock_pred, user_predictions_today=5, max_predictions_per_day=10
        )

        # Then
        assert len(errors) > 0
        assert "预测比分不能为负数" in errors[0]

    def test_validate_prediction_rules_invalid_confidence(
        self, service, mock_prediction
    ):
        """测试：验证预测规则 - 无效信心度"""
        # Given
        mock_prediction.confidence = Mock()
        mock_prediction.confidence.value = Mock()
        mock_prediction.confidence.value.__float__ = Mock(return_value=1.5)
        mock_prediction.score = Mock()
        mock_prediction.score.predicted_home = 2
        mock_prediction.score.predicted_away = 1

        # When
        errors = service.validate_prediction_rules(
            _prediction=mock_prediction,
            user_predictions_today=5,
            max_predictions_per_day=10,
        )

        # Then
        assert len(errors) > 0
        assert "信心度必须在0-1之间" in errors[0]

    def test_get_domain_events(self, service):
        """测试：获取领域事件"""
        # Given
        test_event = Mock()
        service._events.append(test_event)

        # When
        events = service.get_domain_events()

        # Then
        assert len(events) == 1
        assert events[0] == test_event
        # 事件列表不应该被清除
        assert len(service._events) == 1

    def test_clear_domain_events(self, service):
        """测试：清除领域事件"""
        # Given
        test_event = Mock()
        service._events.append(test_event)
        assert len(service._events) == 1

        # When
        service.clear_domain_events()

        # Then
        assert len(service._events) == 0

    def test_calculate_prediction_confidence_with_no_history(self, service):
        """测试：计算预测信心度 - 无历史记录"""
        # Given
        user_history = {}
        match_importance = 0.5

        # When
        confidence = service.calculate_prediction_confidence(
            user_history=user_history, match重要性=match_importance
        )

        # Then
        assert 0.0 <= confidence <= 1.0
        assert confidence == 0.5  # 基础信心度

    def test_calculate_prediction_confidence_bounds(self, service):
        """测试：计算预测信心度 - 边界值"""
        # 测试最小值
        confidence = service.calculate_prediction_confidence(
            user_history={"accuracy_rate": 0.0}, match重要性=0.0, team_form_diff=-1.0
        )
        assert confidence >= 0.0

        # 测试最大值
        confidence = service.calculate_prediction_confidence(
            user_history={"accuracy_rate": 1.0}, match重要性=1.0, team_form_diff=1.0
        )
        assert confidence <= 1.0
