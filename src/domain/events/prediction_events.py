"""
预测领域事件
Prediction Domain Events

定义与预测相关的领域事件。
Defines domain events related to predictions.
"""

from typing import Dict, Any, Optional
from .base import DomainEvent


class PredictionCreatedEvent(DomainEvent):
    """预测创建事件"""

    def __init__(
        self,
        prediction_id: int,
        user_id: int,
        match_id: int,
        predicted_home: int,
        predicted_away: int,
        confidence: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(aggregate_id=prediction_id)
        self.prediction_id = prediction_id
        self.user_id = user_id
        self.match_id = match_id
        self.predicted_home = predicted_home
        self.predicted_away = predicted_away
        self.confidence = confidence

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "user_id": self.user_id,
            "match_id": self.match_id,
            "predicted_home": self.predicted_home,
            "predicted_away": self.predicted_away,
            "confidence": self.confidence,
        }


class PredictionUpdatedEvent(DomainEvent):
    """预测更新事件"""

    def __init__(
        self,
        prediction_id: int,
        old_predicted_home: int,
        old_predicted_away: int,
        new_predicted_home: int,
        new_predicted_away: int,
        **kwargs,
    ):
        super().__init__(aggregate_id=prediction_id)
        self.prediction_id = prediction_id
        self.old_predicted_home = old_predicted_home
        self.old_predicted_away = old_predicted_away
        self.new_predicted_home = new_predicted_home
        self.new_predicted_away = new_predicted_away

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "old_prediction": {
                "home": self.old_predicted_home,
                "away": self.old_predicted_away,
            },
            "new_prediction": {
                "home": self.new_predicted_home,
                "away": self.new_predicted_away,
            },
        }


class PredictionEvaluatedEvent(DomainEvent):
    """预测评估事件"""

    def __init__(
        self,
        prediction_id: int,
        actual_home: int,
        actual_away: int,
        is_correct: bool,
        points_earned: Optional[int] = None,
        accuracy_score: Optional[float] = None,
        **kwargs,
    ):
        super().__init__(aggregate_id=prediction_id)
        self.prediction_id = prediction_id
        self.actual_home = actual_home
        self.actual_away = actual_away
        self.is_correct = is_correct
        self.points_earned = points_earned
        self.accuracy_score = accuracy_score

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "actual_score": {"home": self.actual_home, "away": self.actual_away},
            "is_correct": self.is_correct,
            "points_earned": self.points_earned,
            "accuracy_score": self.accuracy_score,
        }


class PredictionCancelledEvent(DomainEvent):
    """预测取消事件"""

    def __init__(
        self,
        prediction_id: int,
        reason: str,
        cancelled_by: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(aggregate_id=prediction_id)
        self.prediction_id = prediction_id
        self.reason = reason
        self.cancelled_by = cancelled_by

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "reason": self.reason,
            "cancelled_by": self.cancelled_by,
        }


class PredictionExpiredEvent(DomainEvent):
    """预测过期事件"""

    def __init__(self, prediction_id: int, match_id: int, expired_at: str, **kwargs):
        super().__init__(aggregate_id=prediction_id)
        self.prediction_id = prediction_id
        self.match_id = match_id
        self.expired_at = expired_at

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "match_id": self.match_id,
            "expired_at": self.expired_at,
        }


class PredictionPointsAdjustedEvent(DomainEvent):
    """预测积分调整事件"""

    def __init__(
        self,
        prediction_id: int,
        user_id: int,
        old_points: int,
        new_points: int,
        adjustment_reason: str,
        **kwargs,
    ):
        super().__init__(aggregate_id=prediction_id)
        self.prediction_id = prediction_id
        self.user_id = user_id
        self.old_points = old_points
        self.new_points = new_points
        self.adjustment_reason = adjustment_reason

    def _get_event_data(self) -> Dict[str, Any]:
        return {
            "prediction_id": self.prediction_id,
            "user_id": self.user_id,
            "old_points": self.old_points,
            "new_points": self.new_points,
            "adjustment_reason": self.adjustment_reason,
            "points_difference": self.new_points - self.old_points,
        }
