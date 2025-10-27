"""
领域事件
Domain Events

定义领域事件类，用于记录和传播领域中的重要事件。
Defines domain event classes for recording and propagating important events in the domain.
"""

from .match_events import (MatchCancelledEvent, MatchFinishedEvent,
                           MatchPostponedEvent, MatchStartedEvent)
from .prediction_events import (PredictionCancelledEvent,
                                PredictionCreatedEvent,
                                PredictionEvaluatedEvent,
                                PredictionExpiredEvent,
                                PredictionPointsAdjustedEvent,
                                PredictionUpdatedEvent)

__all__ = [
    # 比赛事件
    "MatchStartedEvent",
    "MatchFinishedEvent",
    "MatchCancelledEvent",
    "MatchPostponedEvent",
    # 预测事件
    "PredictionCreatedEvent",
    "PredictionUpdatedEvent",
    "PredictionEvaluatedEvent",
    "PredictionCancelledEvent",
    "PredictionExpiredEvent",
    "PredictionPointsAdjustedEvent",
]
