from typing import Any, Dict, List, Optional, Union
"""
领域事件
Domain Events

定义领域事件类，用于记录和传播领域中的重要事件。
Defines domain event classes for recording and propagating important events in the domain.
"""

from .match_events import (
    MatchStartedEvent,
    MatchFinishedEvent,
    MatchCancelledEvent,
    MatchPostponedEvent,
)
from .prediction_events import (
    PredictionCreatedEvent,
    PredictionUpdatedEvent,
    PredictionEvaluatedEvent,
    PredictionCancelledEvent,
    PredictionExpiredEvent,
    PredictionPointsAdjustedEvent,
)
from .prediction_events import (
    PredictionCreatedEvent,
    PredictionEvaluatedEvent,
    PredictionCancelledEvent,
)

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
