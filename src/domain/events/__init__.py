"""
领域事件
Domain Events

定义领域事件类,用于记录和传播领域中的重要事件.
Defines domain event classes for recording and propagating important events in the domain.
"""

# 注释掉不存在的类
# MatchCancelledEvent,
# MatchFinishedEvent,
# MatchPostponedEvent,
# MatchStartedEvent,
# PredictionCancelledEvent,
# PredictionCreatedEvent,
# PredictionEvaluatedEvent,
# PredictionExpiredEvent,
# PredictionPointsAdjustedEvent,
# PredictionUpdatedEvent,

from .base import Event, EventData, EventHandler
from .bus import EventBus, get_event_bus, start_event_bus, stop_event_bus
from .handlers import (
    AlertEventHandler,
    AnalyticsEventHandler,
    CacheInvalidationHandler,
    LoggingEventHandler,
    MetricsEventHandler,
    NotificationEventHandler,
    register_default_handlers,
)
from .types import (
    MatchCreatedEventData,
    MatchUpdatedEventData,
    PredictionMadeEventData,
)

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
    "",
    # 事件处理器
    "MetricsEventHandler",
    "LoggingEventHandler",
    "CacheInvalidationHandler",
    "NotificationEventHandler",
    "AnalyticsEventHandler",
    "AlertEventHandler",
    "register_default_handlers",
]
