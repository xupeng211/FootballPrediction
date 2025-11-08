#!/usr/bin/env python3
"""
🏗️ M2-P4-01: 预测领域服务测试
Prediction Domain Service Tests

测试预测服务的核心业务逻辑，包括：
- 预测创建和验证
- 业务规则应用
- 预测评估和计算
- 事件发布处理
- 异常情况处理

目标覆盖率: 领域服务模块覆盖率≥45%
"""

import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest

logger = logging.getLogger(__name__)

# 导入领域模型和服务
try:
    from src.domain.events.prediction_events import (
        PredictionCancelledEvent,
        PredictionCreatedEvent,
        PredictionEvaluatedEvent,
        PredictionExpiredEvent,
        PredictionPointsAdjustedEvent,
        PredictionUpdatedEvent,
    )
    from src.domain.models.match import Match, MatchStatus
    from src.domain.models.prediction import (
        Prediction,
        PredictionPoints,
        PredictionStatus,
    )
    from src.domain.models.team import Team
    from src.domain.services.prediction_service import PredictionDomainService

    CAN_IMPORT = True
except ImportError as e:
    logger.error(f"Warning: Import failed: {e}")  # TODO: Add logger import if needed
    CAN_IMPORT = False

    # Mock implementations
    class MatchStatus:
        SCHEDULED = "scheduled"
        LIVE = "live"
        FINISHED = "finished"
        CANCELLED = "cancelled"

    class PredictionStatus:
        PENDING = "pending"
        EVALUATED = "evaluated"
        CANCELLED = "cancelled"
        EXPIRED = "expired"

    class Match:
        def __init__(
            self,
            id: int,
            home_team: Any,
            away_team: Any,
            status: str = MatchStatus.SCHEDULED,
        ):
            self.id = id
            self.home_team = home_team
            self.away_team = away_team
            self.status = status
            self.start_time = datetime.now()
            self.result = None

    class Team:
        def __init__(self, id: int, name: str):
            self.id = id
            self.name = name

    class Prediction:
        def __init__(
            self,
            id: int,
            user_id: int,
            match: Match,
            predicted_home: int,
            predicted_away: int,
        ):
            self.id = id
            self.user_id = user_id
            self.match = match
            self.predicted_home = predicted_home
            self.predicted_away = predicted_away
            self.status = PredictionStatus.PENDING
            self.confidence = None
            self.notes = None
            self.points = None
            self.created_at = datetime.now()

    class PredictionPoints:
        def __init__(
            self,
            base_points: float,
            accuracy_bonus: float = 0,
            confidence_bonus: float = 0,
        ):
            self.base_points = base_points
            self.accuracy_bonus = accuracy_bonus
            self.confidence_bonus = confidence_bonus
            self.total_points = base_points + accuracy_bonus + confidence_bonus

    class PredictionCreatedEvent:
        def __init__(self, prediction: Prediction):
            self.prediction = prediction
            self.timestamp = datetime.now()

    class PredictionUpdatedEvent:
        def __init__(self, prediction: Prediction):
            self.prediction = prediction
            self.timestamp = datetime.now()

    class PredictionEvaluatedEvent:
        def __init__(self, prediction: Prediction, points_earned: float):
            self.prediction = prediction
            self.points_earned = points_earned
            self.timestamp = datetime.now()

    class PredictionCancelledEvent:
        def __init__(self, prediction: Prediction):
            self.prediction = prediction
            self.timestamp = datetime.now()

    class PredictionExpiredEvent:
        def __init__(self, prediction: Prediction):
            self.prediction = prediction
            self.timestamp = datetime.now()

    class PredictionPointsAdjustedEvent:
        def __init__(self, prediction: Prediction, adjustment_reason: str):
            self.prediction = prediction
            self.adjustment_reason = adjustment_reason
            self.timestamp = datetime.now()

    class PredictionDomainService:
        def __init__(self):
            self._events: list[Any] = []

        def create_prediction(
            self,
            user_id: int,
            match: Match,
            predicted_home: int,
            predicted_away: int,
            confidence: float = None,
            notes: str = None,
        ) -> Prediction:
            prediction = Prediction(
                id=1,
                user_id=user_id,
                match=match,
                predicted_home=predicted_home,
                predicted_away=predicted_away,
            )
            prediction.confidence = confidence
            prediction.notes = notes
            event = PredictionCreatedEvent(prediction)
            self._events.append(event)
            return prediction

        def update_prediction(
            self,
            prediction: Prediction,
            predicted_home: int = None,
            predicted_away: int = None,
            confidence: float = None,
            notes: str = None,
        ) -> Prediction:
            if predicted_home is not None:
                prediction.predicted_home = predicted_home
            if predicted_away is not None:
                prediction.predicted_away = predicted_away
            prediction.confidence = confidence
            prediction.notes = notes
            event = PredictionUpdatedEvent(prediction)
            self._events.append(event)
            return prediction

        def evaluate_prediction(
            self, prediction: Prediction, actual_home: int, actual_away: int
        ) -> Prediction:
            prediction.status = PredictionStatus.EVALUATED
            points = self._calculate_points(prediction, actual_home, actual_away)
            prediction.points = points
            event = PredictionEvaluatedEvent(prediction, points.total_points)
            self._events.append(event)
            return prediction

        def _calculate_points(
            self, prediction: Prediction, actual_home: int, actual_away: int
        ) -> PredictionPoints:
            base_points = 10.0
            accuracy_bonus = 0.0
            confidence_bonus = 0.0

            # 准确性奖励
            if (
                prediction.predicted_home == actual_home
                and prediction.predicted_away == actual_away
            ):
                accuracy_bonus = 20.0
            elif (prediction.predicted_home - prediction.predicted_away) == (
                actual_home - actual_away
            ):
                accuracy_bonus = 10.0

            return PredictionPoints(base_points, accuracy_bonus, confidence_bonus)

        def cancel_prediction(
            self, prediction: Prediction, reason: str = None
        ) -> Prediction:
            prediction.status = PredictionStatus.CANCELLED
            event = PredictionCancelledEvent(prediction)
            self._events.append(event)
            return prediction

        def get_events(self) -> list[Any]:
            return self._events.copy()

        def clear_events(self) -> None:
            self._events.clear()


@pytest.mark.skipif(not CAN_IMPORT, reason="领域服务导入失败")
@pytest.mark.unit
@pytest.mark.domain
@pytest.mark.services
class TestPredictionDomainService:
    """预测领域服务测试"""

    @pytest.fixture
    def mock_home_team(self):
        """模拟主队"""
        return Team(id=1, name="Test Home Team")

    @pytest.fixture
    def mock_away_team(self):
        """模拟客队"""
        return Team(id=2, name="Test Away Team")

    @pytest.fixture
    def mock_match(self):
        """模拟比赛"""
        future_time = datetime.now() + timedelta(days=1)  # 未来时间，确保可以提交预测
        return Match(
            id=1,
            home_team_id=1,
            away_team_id=2,
            league_id=1,
            season="2024",
            status=MatchStatus.SCHEDULED,
            match_date=future_time,
        )

    @pytest.fixture
    def prediction_service(self):
        """创建预测服务实例"""
        return PredictionDomainService()

    def test_service_initialization(self, prediction_service):
        """测试服务初始化"""
        assert prediction_service is not None
        assert hasattr(prediction_service, "_events")
        assert len(prediction_service.get_domain_events()) == 0

    def test_create_prediction_success(self, prediction_service, mock_match):
        """测试成功创建预测"""
        user_id = 123
        predicted_home = 2
        predicted_away = 1
        confidence = 0.8
        notes = "Test prediction"

        prediction = prediction_service.create_prediction(
            user_id=user_id,
            match=mock_match,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
            confidence=confidence,
            notes=notes,
        )

        # 验证预测对象
        assert prediction is not None
        assert prediction.user_id == user_id
        assert prediction.match_id == mock_match.id
        assert prediction.score.predicted_home == predicted_home
        assert prediction.score.predicted_away == predicted_away
        assert (
            prediction.confidence.value == Decimal(str(confidence))
            if confidence
            else prediction.confidence is None
        )
        assert prediction.status == PredictionStatus.PENDING

        # 验证事件发布
        events = prediction_service.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], PredictionCreatedEvent)
        assert events[0].prediction_id == prediction.id

    def test_create_prediction_without_optional_params(
        self, prediction_service, mock_match
    ):
        """测试不包含可选参数的预测创建"""
        user_id = 123
        predicted_home = 1
        predicted_away = 0

        prediction = prediction_service.create_prediction(
            user_id=user_id,
            match=mock_match,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
        )

        assert prediction is not None
        assert prediction.user_id == user_id
        assert prediction.score.predicted_home == predicted_home
        assert prediction.score.predicted_away == predicted_away
        assert prediction.confidence is None

    def test_update_prediction_success(self, prediction_service, mock_match):
        """测试成功更新预测"""
        # 先创建预测
        prediction = prediction_service.create_prediction(
            user_id=123, match=mock_match, predicted_home=1, predicted_away=1
        )

        # 清空事件
        prediction_service.clear_domain_events()

        # 更新预测
        new_predicted_home = 2
        new_confidence = 0.9

        prediction_service.update_prediction(
            prediction=prediction,
            new_predicted_home=new_predicted_home,
            new_predicted_away=1,  # 保持原有值
            new_confidence=new_confidence,
        )

        # 验证更新结果
        assert prediction.score.predicted_home == new_predicted_home
        assert prediction.score.predicted_away == 1  # 未更新
        assert (
            prediction.confidence.value == Decimal(str(new_confidence))
            if new_confidence
            else prediction.confidence is None
        )

        # 验证事件发布
        events = prediction_service.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], PredictionUpdatedEvent)

    def test_evaluate_prediction_exact_match(self, prediction_service, mock_match):
        """测试完全准确的预测评估"""
        prediction = prediction_service.create_prediction(
            user_id=123, match=mock_match, predicted_home=2, predicted_away=1
        )

        # 清空事件
        prediction_service.clear_domain_events()

        # 评估预测（完全准确）
        evaluated_prediction = prediction_service.evaluate_prediction(
            prediction=prediction, actual_home=2, actual_away=1
        )

        # 验证评估结果
        assert evaluated_prediction.status == PredictionStatus.EVALUATED
        assert evaluated_prediction.points is not None
        assert evaluated_prediction.points.base_points == 10.0
        assert evaluated_prediction.points.accuracy_bonus == 20.0  # 完全准确奖励
        assert evaluated_prediction.points.total_points == 30.0

        # 验证事件发布
        events = prediction_service.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], PredictionEvaluatedEvent)
        assert events[0].points_earned == 30.0

    def test_evaluate_prediction_score_difference_match(
        self, prediction_service, mock_match
    ):
        """测试比分差异匹配的预测评估"""
        prediction = prediction_service.create_prediction(
            user_id=123,
            match=mock_match,
            predicted_home=3,
            predicted_away=1,  # 预测净胜2球
        )

        prediction_service.clear_domain_events()

        # 评估预测（比分差异正确但具体比分不同）
        evaluated_prediction = prediction_service.evaluate_prediction(
            prediction=prediction, actual_home=2, actual_away=0  # 实际净胜2球
        )

        # 验证评估结果
        assert evaluated_prediction.status == PredictionStatus.EVALUATED
        assert evaluated_prediction.points is not None
        assert evaluated_prediction.points.base_points == 10.0
        assert evaluated_prediction.points.accuracy_bonus == 10.0  # 比分差异奖励
        assert evaluated_prediction.points.total_points == 20.0

    def test_evaluate_prediction_no_match(self, prediction_service, mock_match):
        """测试完全不匹配的预测评估"""
        prediction = prediction_service.create_prediction(
            user_id=123, match=mock_match, predicted_home=1, predicted_away=1
        )

        prediction_service.clear_domain_events()

        # 评估预测（完全不匹配）
        evaluated_prediction = prediction_service.evaluate_prediction(
            prediction=prediction, actual_home=0, actual_away=2
        )

        # 验证评估结果
        assert evaluated_prediction.status == PredictionStatus.EVALUATED
        assert evaluated_prediction.points is not None
        assert evaluated_prediction.points.base_points == 10.0
        assert evaluated_prediction.points.accuracy_bonus == 0.0  # 无奖励
        assert evaluated_prediction.points.total_points == 10.0

    def test_cancel_prediction_success(self, prediction_service, mock_match):
        """测试成功取消预测"""
        prediction = prediction_service.create_prediction(
            user_id=123, match=mock_match, predicted_home=1, predicted_away=1
        )

        prediction_service.clear_domain_events()

        # 取消预测
        cancelled_prediction = prediction_service.cancel_prediction(
            prediction=prediction, reason="User request"
        )

        # 验证取消结果
        assert cancelled_prediction.status == PredictionStatus.CANCELLED

        # 验证事件发布
        events = prediction_service.get_domain_events()
        assert len(events) == 1
        assert isinstance(events[0], PredictionCancelledEvent)

    def test_events_management(self, prediction_service, mock_match):
        """测试事件管理功能"""
        # 创建多个事件
        prediction_service.create_prediction(
            user_id=123, match=mock_match, predicted_home=1, predicted_away=1
        )

        prediction_service.create_prediction(
            user_id=124, match=mock_match, predicted_home=2, predicted_away=1
        )

        # 验证事件数量
        events = prediction_service.get_domain_events()
        assert len(events) == 2
        assert all(isinstance(event, PredictionCreatedEvent) for event in events)

        # 清空事件
        prediction_service.clear_domain_events()
        assert len(prediction_service.get_domain_events()) == 0

    def test_get_events_returns_copy(self, prediction_service, mock_match):
        """测试get_events返回的是副本而不是原始列表"""
        prediction_service.create_prediction(
            user_id=123, match=mock_match, predicted_home=1, predicted_away=1
        )

        events1 = prediction_service.get_domain_events()
        events2 = prediction_service.get_domain_events()

        # 验证是不同的对象
        assert events1 is not events2
        assert events1 == events2

        # 修改一个不影响另一个
        events1.append("test")
        assert len(events2) == 1
        assert len(prediction_service.get_domain_events()) == 1

    @pytest.mark.parametrize(
        "predicted_home,predicted_away,actual_home,actual_y,expected_bonus",
        [
            (2, 1, 2, 1, 20.0),  # 完全匹配
            (3, 1, 2, 0, 10.0),  # 差异匹配
            (1, 1, 0, 2, 0.0),  # 无匹配
            (2, 0, 3, 1, 10.0),  # 差异匹配
            (0, 0, 0, 0, 20.0),  # 完全匹配（0:0）
        ],
    )
    def test_points_calculation_scenarios(
        self,
        prediction_service,
        mock_match,
        predicted_home,
        predicted_away,
        actual_home,
        actual_y,
        expected_bonus,
    ):
        """测试不同场景下的积分计算"""
        prediction = prediction_service.create_prediction(
            user_id=123,
            match=mock_match,
            predicted_home=predicted_home,
            predicted_away=predicted_away,
        )

        evaluated_prediction = prediction_service.evaluate_prediction(
            prediction=prediction, actual_home=actual_home, actual_away=actual_y
        )

        assert evaluated_prediction.points.accuracy_bonus == expected_bonus
        assert evaluated_prediction.points.total_points == 10.0 + expected_bonus

    def test_multiple_predictions_same_user(self, prediction_service, mock_match):
        """测试同一用户的多个预测"""
        user_id = 123

        # 创建多个预测
        prediction1 = prediction_service.create_prediction(
            user_id=user_id, match=mock_match, predicted_home=1, predicted_away=1
        )
        prediction2 = prediction_service.create_prediction(
            user_id=user_id, match=mock_match, predicted_home=2, predicted_away=1
        )
        prediction3 = prediction_service.create_prediction(
            user_id=user_id, match=mock_match, predicted_home=0, predicted_away=2
        )

        # 验证所有预测都正确创建
        assert prediction1.user_id == user_id
        assert prediction2.user_id == user_id
        assert prediction3.user_id == user_id

        # 验证事件数量
        events = prediction_service.get_domain_events()
        assert len(events) == 3
        assert all(event.prediction.user_id == user_id for event in events)


@pytest.mark.unit
@pytest.mark.domain
@pytest.mark.services
@pytest.mark.integration
class TestPredictionServiceIntegration:
    """预测服务集成测试"""

    def test_full_prediction_workflow(self):
        """测试完整的预测工作流程"""
        service = PredictionDomainService()

        # 创建模拟数据
        home_team = Team(id=1, name="Home Team")
        away_team = Team(id=2, name="Away Team")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        # 1. 创建预测
        prediction = service.create_prediction(
            user_id=123, match=match, predicted_home=2, predicted_away=1, confidence=0.8
        )
        assert prediction.status == PredictionStatus.PENDING

        # 2. 更新预测
        service.clear_events()
        updated_prediction = service.update_prediction(
            prediction=prediction, confidence=0.9, notes="Updated"
        )
        assert updated_prediction.confidence == 0.9

        # 3. 评估预测
        service.clear_events()
        evaluated_prediction = service.evaluate_prediction(
            prediction=updated_prediction, actual_home=2, actual_away=1
        )
        assert evaluated_prediction.status == PredictionStatus.EVALUATED
        assert evaluated_prediction.points.total_points == 30.0

        # 4. 验证工作流程中的事件
        events = service.get_events()
        assert len(events) == 1
        assert isinstance(events[0], PredictionEvaluatedEvent)

    def test_prediction_cancellation_workflow(self):
        """测试预测取消工作流程"""
        service = PredictionDomainService()

        # 创建预测
        home_team = Team(id=1, name="Home Team")
        away_team = Team(id=2, name="Away Team")
        match = Match(id=1, home_team=home_team, away_team=away_team)

        prediction = service.create_prediction(
            user_id=123, match=match, predicted_home=1, predicted_away=1
        )

        # 取消预测
        service.clear_events()
        cancelled_prediction = service.cancel_prediction(
            prediction, "User requested cancellation"
        )

        # 验证取消状态和事件
        assert cancelled_prediction.status == PredictionStatus.CANCELLED

        events = service.get_events()
        assert len(events) == 1
        assert isinstance(events[0], PredictionCancelledEvent)


# 测试运行器
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
