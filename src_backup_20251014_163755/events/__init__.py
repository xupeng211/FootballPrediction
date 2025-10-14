"""
事件驱动架构模块
Event-Driven Architecture Module

提供事件系统基础设施，实现松耦合的组件通信。
Provides event system infrastructure for loosely coupled component communication.
"""

from .base import Event, EventHandler, EventData
from .bus import EventBus, get_event_bus, start_event_bus, stop_event_bus
from .types import (
    MatchCreatedEvent,
    MatchUpdatedEvent,
    PredictionMadeEvent,
    PredictionUpdatedEvent,
    UserRegisteredEvent,
    TeamStatsUpdatedEvent,
    MatchCreatedEventData,
    MatchUpdatedEventData,
    PredictionMadeEventData,
    PredictionUpdatedEventData,
    UserRegisteredEventData,
    TeamStatsEventData,
)
from .handlers import (
    MetricsEventHandler,
    LoggingEventHandler,
    CacheInvalidationHandler,
    NotificationEventHandler,
    AnalyticsEventHandler,
    AlertEventHandler,
    register_default_handlers,
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
    # 事件类型
    "MatchCreatedEvent",
    "MatchUpdatedEvent",
    "PredictionMadeEvent",
    "PredictionUpdatedEvent",
    "UserRegisteredEvent",
    "TeamStatsUpdatedEvent",
    # 事件数据类型
    "MatchCreatedEventData",
    "MatchUpdatedEventData",
    "PredictionMadeEventData",
    "PredictionUpdatedEventData",
    "UserRegisteredEventData",
    "TeamStatsEventData",
    # 事件处理器
    "MetricsEventHandler",
    "LoggingEventHandler",
    "CacheInvalidationHandler",
    "NotificationEventHandler",
    "AnalyticsEventHandler",
    "AlertEventHandler",
    "register_default_handlers",
]
