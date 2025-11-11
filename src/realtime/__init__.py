"""
实时模块 - 足球预测系统WebSocket实时通信

Realtime Module - Football Prediction System WebSocket Real-time Communication

提供完整的WebSocket实时通信功能,包括:
- WebSocket连接管理
- 事件定义和处理
- 订阅管理
- 实时数据推送
"""

from .subscriptions import SubscriptionManager

# 导入实时事件相关类
try:
    from .events import (
        AnalyticsEvent,
        EventType,
        MatchEvent,
        OddsEvent,
        PredictionEvent,
        RealtimeEvent,
        SystemAlertEvent,
        create_analytics_updated_event,
    )
except ImportError:
    AnalyticsEvent = None
    EventType = None
    MatchEvent = None
    OddsEvent = None
    PredictionEvent = None
    RealtimeEvent = None
    SystemAlertEvent = None
    create_analytics_updated_event = None

__all__ = [
    # 订阅管理
    "SubscriptionManager",
    # 事件类型
    "AnalyticsEvent",
    "EventType",
    "MatchEvent",
    "OddsEvent",
    "PredictionEvent",
    "RealtimeEvent",
    "SystemAlertEvent",
    # 事件创建函数
    "create_analytics_updated_event",
]
