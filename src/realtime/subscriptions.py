from typing import Set
from typing import Optional
from typing import Any
from typing import List
from typing import Dict
import logging
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum


import asyncio

# 检查比赛ID
# 检查联赛
# 检查用户
# 检查置信度
# 检查事件源
# 检查自定义过滤器
# 检查事件类型
# 应用过滤器
# 启动清理任务
# 创建过滤器
# 创建订阅
# 添加订阅
# 更新事件订阅者索引
# 移除订阅
# 更新事件订阅者索引
# 如果连接没有任何订阅了,清理索引
# 清理事件订阅者索引
# 删除连接的所有订阅
# 检查是否超过非活跃阈值
# 清理没有活跃订阅的连接
# 便捷订阅函数
# 订阅所有比赛事件类型
# 订阅所有赔率事件类型
# 全局订阅管理器实例
# 需要导入asyncio
"""
订阅管理模块 - WebSocket事件订阅
Subscription Management Module - WebSocket Event Subscriptions
管理客户端对特定事件的订阅,支持过滤和路由
Manages client subscriptions to specific events with filtering and routing
"""


class SubscriptionType(str, Enum):
    """订阅类型"""

    SPECIFIC_EVENT = "specific_event"  # 订阅特定事件类型
    MATCH_SPECIFIC = "match_specific"  # 订阅特定比赛的所有事件
    USER_SPECIFIC = "user_specific"  # 订阅特定用户相关事件
    SYSTEM_ALERTS = "system_alerts"  # 订阅系统告警
    ANALYTICS = "analytics"  # 订阅分析数据


@dataclass
class SubscriptionFilter:
    """类文档字符串"""
    pass  # 添加pass语句
    """订阅过滤器"""

    match_ids: Optional[List[int]] = field(default_factory=list)  # 特定比赛ID
    leagues: Optional[List[str]] = field(default_factory=list)  # 特定联赛
    users: Optional[List[str]] = field(default_factory=list)  # 特定用户
    min_confidence: Optional[float] = None  # 最小置信度
    event_sources: Optional[List[str]] = field(default_factory=list)  # 事件源
    custom_filters: Optional[Dict[str, Any]] = field(
        default_factory=dict
    )  # 自定义过滤器

    def matches(self, event_data: Dict[str, Any]) -> bool:
        """检查事件是否匹配过滤器"""
        if self.match_ids and event_data.get("match_id") not in self.match_ids:
            return False
        if self.leagues and event_data.get("league") not in self.leagues:
            return False
        if self.users and event_data.get("user_id") not in self.users:
            return False
        if self.min_confidence is not None:
            confidence = event_data.get("confidence", 0)
            if confidence < self.min_confidence:
                return False
        if self.event_sources and event_data.get("source") not in self.event_sources:
            return False
        if self.custom_filters:
            for key, value in self.custom_filters.items():
                if event_data.get(key) != value:
                    return False
        return True


@dataclass
class Subscription:
    """类文档字符串"""
    pass  # 添加pass语句
    """订阅信息"""

    connection_id: str
    subscription_type: SubscriptionType
    event_types: Set[EventType]
    filters: SubscriptionFilter
    created_at: datetime = field(default_factory=datetime.now)
    last_activity: datetime = field(default_factory=datetime.now)
    is_active: bool = True

    def update_activity(self) -> None:
        """更新最后活动时间"""
        self.last_activity = datetime.now()

    def should_receive_event(self, event: RealtimeEvent) -> bool:
        """检查是否应该接收此事件"""
        if not self.is_active:
            return False
        if event.event_type not in self.event_types:
            return False
        return self.filters.matches(event.data)


class SubscriptionManager:
    """类文档字符串"""
    pass  # 添加pass语句
    """订阅管理器"""

    def __init__(self):
        """函数文档字符串"""
        pass
  # 添加pass语句
        self.subscriptions: Dict[
            str, List[Subscription]
        ] = {}  # connection_id -> subscriptions
        self.event_subscribers: Dict[
            EventType, Set[str]
        ] = {}  # event_type -> connection_ids
        self.logger = logging.getLogger(f"{__name__}.SubscriptionManager")
        asyncio.create_task(self._cleanup_inactive_subscriptions())
        self.logger.info("SubscriptionManager initialized")

    def subscribe(
        self,
        connection_id: str,
        event_type: EventType,
        filters: Optional[Dict[str, Any]] = None,
        subscription_type: SubscriptionType = SubscriptionType.SPECIFIC_EVENT,
    ) -> bool:
        """订阅事件"""
        try:
            filter_obj = SubscriptionFilter(**(filters or {}))
            subscription = Subscription(
                connection_id=connection_id,
                subscription_type=subscription_type,
                event_types={event_type},
                filters=filter_obj,
            )
            if connection_id not in self.subscriptions:
                self.subscriptions[connection_id] = []
            self.subscriptions[connection_id].append(subscription)
            if event_type not in self.event_subscribers:
                self.event_subscribers[event_type] = set()
            self.event_subscribers[event_type].add(connection_id)
            self.logger.info(f"Connection {connection_id} subscribed to {event_type}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to create subscription: {e}")
            return False

    def unsubscribe(self, connection_id: str, event_type: EventType) -> bool:
        """取消订阅事件"""
        if connection_id not in self.subscriptions:
            return False
        original_count = len(self.subscriptions[connection_id])
        self.subscriptions[connection_id] = [
            sub
            for sub in self.subscriptions[connection_id]
            if event_type not in sub.event_types
        ]
        if event_type in self.event_subscribers:
            self.event_subscribers[event_type].discard(connection_id)
        if not self.subscriptions[connection_id]:
            del self.subscriptions[connection_id]
        removed_count = original_count - len(self.subscriptions[connection_id])
        if removed_count > 0:
            self.logger.info(
                f"Connection {connection_id} unsubscribed from {event_type} (removed {removed_count} subscriptions)"
            )
            return True
        return False

    def remove_all_subscriptions(self, connection_id: str) -> None:
        """移除连接的所有订阅"""
        if connection_id not in self.subscriptions:
            return None
        for subscription in self.subscriptions[connection_id]:
            for event_type in subscription.event_types:
                if event_type in self.event_subscribers:
                    self.event_subscribers[event_type].discard(connection_id)
        del self.subscriptions[connection_id]
        self.logger.info(f"Removed all subscriptions for connection {connection_id}")

    def get_subscribers(
        self, event_type: EventType, event_data: Dict[str, Any]
    ) -> List[str]:
        """获取事件的订阅者"""
        if event_type not in self.event_subscribers:
            return []
        subscribers = set()
        for connection_id in self.event_subscribers[event_type]:
            if connection_id in self.subscriptions:
                for subscription in self.subscriptions[connection_id]:
                    if subscription.should_receive_event(
                        RealtimeEvent(
                            event_type=event_type,
                            data=event_data,
                            timestamp=datetime.now(),
                        )
                    ):
                        subscribers.add(connection_id)
                        break
        return list(subscribers)

    def get_connection_subscriptions(self, connection_id: str) -> List[Dict[str, Any]]:
        """获取连接的所有订阅"""
        if connection_id not in self.subscriptions:
            return []
        return [
            {
                "subscription_type": sub.subscription_type.value,
                "event_types": [et.value for et in sub.event_types],
                "filters": {
                    "match_ids": sub.filters.match_ids,
                    "leagues": sub.filters.leagues,
                    "users": sub.filters.users,
                    "min_confidence": sub.filters.min_confidence,
                    "event_sources": sub.filters.event_sources,
                    "custom_filters": sub.filters.custom_filters,
                },
                "created_at": sub.created_at.isoformat(),
                "last_activity": sub.last_activity.isoformat(),
                "is_active": sub.is_active,
            }
            for sub in self.subscriptions[connection_id]
        ]

    def update_subscription_activity(self, connection_id: str) -> None:
        """更新订阅活动时间"""
        if connection_id in self.subscriptions:
            for subscription in self.subscriptions[connection_id]:
                subscription.update_activity()

    def get_total_subscriptions(self) -> int:
        """获取总订阅数"""
        return sum(len(subs) for subs in self.subscriptions.values())

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        event_type_counts = {}
        for subscriptions in self.subscriptions.values():
            for subscription in subscriptions:
                for event_type in subscription.event_types:
                    event_type_counts[event_type.value] = (
                        event_type_counts.get(event_type.value, 0) + 1
                    )
        return {
            "total_connections": len(self.subscriptions),
            "total_subscriptions": self.get_total_subscriptions(),
            "subscriptions_by_event_type": event_type_counts,
            "event_types_supported": len(EventType),
        }

    async def _cleanup_inactive_subscriptions(self) -> None:
        """清理非活跃订阅"""
        while True:
            try:
                await asyncio.sleep(3600)  # 每小时检查一次
                cleanup_time = datetime.now()
                inactive_threshold = 3600  # 1小时非活跃
                connections_to_remove = []
                for connection_id, subscriptions in self.subscriptions.items():
                    active_subscriptions = []
                    for subscription in subscriptions:
                        if (
                            cleanup_time - subscription.last_activity
                        ).total_seconds() > inactive_threshold:
                            subscription.is_active = False
                        else:
                            active_subscriptions.append(subscription)
                    if active_subscriptions:
                        self.subscriptions[connection_id] = active_subscriptions
                    else:
                        connections_to_remove.append(connection_id)
                for connection_id in connections_to_remove:
                    self.remove_all_subscriptions(connection_id)
                if connections_to_remove:
                    self.logger.info(
                        f"Cleaned up {len(connections_to_remove)} inactive connections"
                    )
            except Exception as e:
                self.logger.error(f"Cleanup task error: {e}")


def subscribe_to_predictions(
    connection_id: str,
    match_ids: Optional[List[int]] = None,
    min_confidence: Optional[float] = None,
) -> bool:
    """订阅预测事件"""
    filters = {}
    if match_ids:
        filters["match_ids"] = match_ids
    if min_confidence:
        filters["min_confidence"] = min_confidence
    manager = get_subscription_manager()
    return manager.subscribe(
        connection_id,
        EventType.PREDICTION_CREATED,
        filters,
        SubscriptionType.SPECIFIC_EVENT,
    )


def subscribe_to_matches(
    connection_id: str,
    match_ids: Optional[List[int]] = None,
    leagues: Optional[List[str]] = None,
) -> bool:
    """订阅比赛事件"""
    filters = {}
    if match_ids:
        filters["match_ids"] = match_ids
    if leagues:
        filters["leagues"] = leagues
    manager = get_subscription_manager()
    success = True
    match_events = [
        EventType.MATCH_STARTED,
        EventType.MATCH_SCORE_CHANGED,
        EventType.MATCH_STATUS_CHANGED,
        EventType.MATCH_ENDED,
    ]
    for event_type in match_events:
        if not manager.subscribe(
            connection_id, event_type, filters, SubscriptionType.MATCH_SPECIFIC
        ):
            success = False
    return success


def subscribe_to_odds(
    connection_id: str,
    match_ids: Optional[List[int]] = None,
    bookmakers: Optional[List[str]] = None,
) -> bool:
    """订阅赔率事件"""
    filters = {}
    if match_ids:
        filters["match_ids"] = match_ids
    if bookmakers:
        filters["custom_filters"] = {"bookmakers": bookmakers}
    manager = get_subscription_manager()
    success = True
    odds_events = [EventType.ODDS_UPDATED, EventType.ODDS_SIGNIFICANT_CHANGE]
    for event_type in odds_events:
        if not manager.subscribe(
            connection_id, event_type, filters, SubscriptionType.SPECIFIC_EVENT
        ):
            success = False
    return success


def subscribe_to_system_alerts(
    connection_id: str, severity_levels: Optional[List[str]] = None
) -> bool:
    """订阅系统告警"""
    filters = {}
    if severity_levels:
        filters["custom_filters"] = {"severity_levels": severity_levels}
    manager = get_subscription_manager()
    return manager.subscribe(
        connection_id, EventType.SYSTEM_ALERT, filters, SubscriptionType.SYSTEM_ALERTS
    )


_global_subscription_manager: Optional[SubscriptionManager] = None


def get_subscription_manager() -> SubscriptionManager:
    """获取全局订阅管理器"""
    global _global_subscription_manager
    if _global_subscription_manager is None:
        _global_subscription_manager = SubscriptionManager()
    return _global_subscription_manager
