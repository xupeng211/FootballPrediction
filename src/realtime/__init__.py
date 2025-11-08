from .events import (
    AnalyticsEvent,
    EventType,
    MatchEvent,
    OddsEvent,
    PredictionEvent,
    RealtimeEvent,
    SystemAlertEvent,
    create_analytics_updated_event,
    create_match_score_changed_event,
    create_odds_updated_event,
    create_prediction_created_event,
    create_system_alert_event,
    validate_event,
)
from .manager import (
    WebSocketConnection,
    WebSocketManager,
    broadcast_to_all,
    broadcast_to_room,
    get_websocket_manager,
    send_to_user,
)
from .match_service import (
    MatchInfo,
    MatchStatus,
    RealtimeMatchService,
    add_match_to_monitoring,
    get_live_matches,
    get_realtime_match_service,
    update_match_score,
)
from .prediction_service import (
    PredictionStatus,
    PredictionTask,
    RealtimePredictionService,
    get_match_predictions,
    get_prediction_status,
    get_realtime_prediction_service,
    submit_prediction,
)
from .router import router
from .subscriptions import (
    Subscription,
    SubscriptionFilter,
    SubscriptionManager,
    SubscriptionType,
    get_subscription_manager,
    subscribe_to_matches,
    subscribe_to_odds,
    subscribe_to_predictions,
    subscribe_to_system_alerts,
)

"""
实时模块 - 足球预测系统WebSocket实时通信

Realtime Module - Football Prediction System WebSocket Real-time Communication

提供完整的WebSocket实时通信功能,包括:
- WebSocket连接管理
- 事件定义和处理
- 订阅管理
- 实时数据推送
"""

__version__ = "1.0.0"
__author__ = "Football Prediction Team"
__all__ = [
    # 路由
    "router",
    # 连接管理
    "WebSocketManager",
    "WebSocketConnection",
    "get_websocket_manager",
    "send_to_user",
    "broadcast_to_room",
    "broadcast_to_all",
    # 事件系统
    "EventType",
    "RealtimeEvent",
    "PredictionEvent",
    "MatchEvent",
    "OddsEvent",
    "SystemAlertEvent",
    "AnalyticsEvent",
    "create_prediction_created_event",
    "create_match_score_changed_event",
    "create_odds_updated_event",
    "create_system_alert_event",
    "create_analytics_updated_event",
    "validate_event",
    # 订阅管理
    "SubscriptionManager",
    "SubscriptionType",
    "SubscriptionFilter",
    "Subscription",
    "get_subscription_manager",
    "subscribe_to_predictions",
    "subscribe_to_matches",
    "subscribe_to_odds",
    "subscribe_to_system_alerts",
    # 实时预测服务
    "RealtimePredictionService",
    "PredictionTask",
    "PredictionStatus",
    "get_realtime_prediction_service",
    "submit_prediction",
    "get_prediction_status",
    "get_match_predictions",
    # 实时比赛服务
    "RealtimeMatchService",
    "MatchInfo",
    "MatchStatus",
    "get_realtime_match_service",
    "add_match_to_monitoring",
    "update_match_score",
    "get_live_matches",
]
