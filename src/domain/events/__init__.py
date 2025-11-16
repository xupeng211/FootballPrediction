"""
领域事件
Domain Events

定义领域事件类,用于记录和传播领域中的重要事件.
Defines domain event classes for recording and propagating important events in the domain.
"""

# 基础类
from .base import Event, EventData, EventHandler

# 事件总线
from .bus import EventBus, get_event_bus, start_event_bus, stop_event_bus

# 事件处理器
from .handlers import (
    AlertEventHandler,
    AnalyticsEventHandler,
    CacheInvalidationHandler,
    LoggingEventHandler,
    MetricsEventHandler,
    NotificationEventHandler,
    register_default_handlers,
)

# 比赛事件
from .match_events import (
    MatchCancelledEvent,
    MatchFinishedEvent,
    MatchPostponedEvent,
    MatchStartedEvent,
)

# 预测事件
from .prediction_events import (
    PredictionCancelledEvent,
    PredictionCreatedEvent,
    PredictionEvaluatedEvent,
    PredictionExpiredEvent,
    PredictionPointsAdjustedEvent,
    PredictionUpdatedEvent,
)

# 事件数据类型
from .types import (
    MatchCreatedEventData,
    MatchUpdatedEventData,
    PredictionMadeEventData,
)

# 公开的API
__all__ = [
    # 基础类
    "Event",
    "EventHandler",
    "EventData",
    # 事件总线
    "EventBus",
    "get_event_bus",
    "start_event_bus",
    "stop_event_bus",
    # 事件数据类型
    "MatchCreatedEventData",
    "MatchUpdatedEventData",
    "PredictionMadeEventData",
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
    # 事件处理器
    "MetricsEventHandler",
    "LoggingEventHandler",
    "CacheInvalidationHandler",
    "NotificationEventHandler",
    "AnalyticsEventHandler",
    "AlertEventHandler",
    "register_default_handlers",
]
