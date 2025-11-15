"""
事件处理器模块
Event Handlers Module

定义各种领域事件的处理器
Defines handlers for various domain events.
"""

import logging
from datetime import datetime
from typing import Any

from .base import DomainEvent, EventHandler

logger = logging.getLogger(__name__)


class MetricsEventHandler(EventHandler):
    """指标事件处理器"""

    def __init__(self):
        self.metrics_count = 0
        self.metrics: dict[str, Any] = {}

    async def handle(self, event: DomainEvent) -> None:
        """处理指标事件"""
        self.metrics_count += 1
        event_type = event.get_event_type()

        # 记录事件指标
        if event_type not in self.metrics:
            self.metrics[event_type] = 0
        self.metrics[event_type] += 1

        logger.debug(
            f"MetricsEventHandler: Processed {event_type} event (#{self.metrics_count})"
        )


class LoggingEventHandler(EventHandler):
    """日志事件处理器"""

    def __init__(self, log_level: int = logging.INFO):
        self.log_level = log_level
        self.events_processed = 0

    async def handle(self, event: DomainEvent) -> None:
        """处理日志事件"""
        self.events_processed += 1
        event_data = event.to_dict()

        logger.log(
            self.log_level,
            f"LoggingEventHandler: {event.get_event_type()} - {event_data}",
        )


class CacheInvalidationHandler(EventHandler):
    """缓存失效事件处理器"""

    def __init__(self):
        self.invalidated_keys: list[str] = []
        self.invalidation_count = 0

    async def handle(self, event: DomainEvent) -> None:
        """处理缓存失效事件"""
        self.invalidation_count += 1
        event_type = event.get_event_type()

        # 生成缓存键
        cache_key = f"{event_type}:{event.aggregate_id}"
        self.invalidated_keys.append(cache_key)

        logger.info(f"CacheInvalidationHandler: Invalidated cache key {cache_key}")


class NotificationEventHandler(EventHandler):
    """通知事件处理器"""

    def __init__(self):
        self.notifications_sent = 0
        self.notification_queue: list[dict[str, Any]] = []

    async def handle(self, event: DomainEvent) -> None:
        """处理通知事件"""
        self.notifications_sent += 1

        notification = {
            "event_type": event.get_event_type(),
            "event_id": event.id,
            "aggregate_id": event.aggregate_id,
            "timestamp": event.timestamp,
            "processed_at": datetime.utcnow(),
        }

        self.notification_queue.append(notification)

        logger.info(
            f"NotificationEventHandler: Queued notification for {event.get_event_type()}"
        )


class AnalyticsEventHandler(EventHandler):
    """分析事件处理器"""

    def __init__(self):
        self.analytics_data: dict[str, Any] = {}
        self.events_tracked = 0

    async def handle(self, event: DomainEvent) -> None:
        """处理分析事件"""
        self.events_tracked += 1
        event_type = event.get_event_type()

        # 跟踪分析数据
        if event_type not in self.analytics_data:
            self.analytics_data[event_type] = {
                "count": 0,
                "first_occurrence": datetime.utcnow(),
                "last_occurrence": None,
            }

        self.analytics_data[event_type]["count"] += 1
        self.analytics_data[event_type]["last_occurrence"] = datetime.utcnow()

        logger.debug(f"AnalyticsEventHandler: Tracked {event_type} event")


class AlertEventHandler(EventHandler):
    """警报事件处理器"""

    def __init__(self):
        self.alerts_triggered = 0
        self.alert_conditions: dict[str, Any] = {
            "error_threshold": 10,
            "warning_threshold": 5,
        }
        self.alert_history: list[dict[str, Any]] = []

    async def handle(self, event: DomainEvent) -> None:
        """处理警报事件"""
        event_type = event.get_event_type()

        # 检查是否需要触发警报
        if self._should_trigger_alert(event_type):
            self.alerts_triggered += 1

            alert = {
                "event_type": event_type,
                "event_id": event.id,
                "triggered_at": datetime.utcnow(),
                "severity": self._get_alert_severity(event_type),
            }

            self.alert_history.append(alert)

            logger.warning(f"AlertEventHandler: Triggered alert for {event_type}")

    def _should_trigger_alert(self, event_type: str) -> bool:
        """判断是否应该触发警报"""
        # 简单的警报逻辑：错误事件总是触发警报
        if "error" in event_type.lower() or "failed" in event_type.lower():
            return True

        # 其他事件的警报逻辑可以根据需要扩展
        return False

    def _get_alert_severity(self, event_type: str) -> str:
        """获取警报严重程度"""
        if "critical" in event_type.lower():
            return "CRITICAL"
        elif "error" in event_type.lower():
            return "ERROR"
        elif "warning" in event_type.lower():
            return "WARNING"
        else:
            return "INFO"


# 事件处理器注册函数
def register_default_handlers(event_bus) -> None:
    """注册默认的事件处理器"""
    from .bus import EventBus

    if not isinstance(event_bus, EventBus):
        raise TypeError("event_bus must be an instance of EventBus")

    # 创建处理器实例
    metrics_handler = MetricsEventHandler()
    logging_handler = LoggingEventHandler()
    cache_handler = CacheInvalidationHandler()
    notification_handler = NotificationEventHandler()
    analytics_handler = AnalyticsEventHandler()
    alert_handler = AlertEventHandler()

    # 注册处理器到事件总线
    # 这里可以根据具体的事件类型进行更精确的注册
    # 目前为所有事件类型注册通用处理器

    event_types = [
        "match_created",
        "match_updated",
        "match_cancelled",
        "match_finished",
        "prediction_made",
        "prediction_evaluated",
        "prediction_cancelled",
        "error_occurred",
        "system_alert",
    ]

    for event_type in event_types:
        event_bus.subscribe(event_type, metrics_handler.handle)
        event_bus.subscribe(event_type, logging_handler.handle)
        event_bus.subscribe(event_type, cache_handler.handle)
        event_bus.subscribe(event_type, notification_handler.handle)
        event_bus.subscribe(event_type, analytics_handler.handle)
        event_bus.subscribe(event_type, alert_handler.handle)

    logger.info("Default event handlers registered successfully")


# 便捷函数
def create_metrics_handler() -> MetricsEventHandler:
    """创建指标事件处理器"""
    return MetricsEventHandler()


def create_logging_handler(log_level: int = logging.INFO) -> LoggingEventHandler:
    """创建日志事件处理器"""
    return LoggingEventHandler(log_level)


def create_cache_invalidation_handler() -> CacheInvalidationHandler:
    """创建缓存失效事件处理器"""
    return CacheInvalidationHandler()


def create_notification_handler() -> NotificationEventHandler:
    """创建通知事件处理器"""
    return NotificationEventHandler()


def create_analytics_handler() -> AnalyticsEventHandler:
    """创建分析事件处理器"""
    return AnalyticsEventHandler()


def create_alert_handler() -> AlertEventHandler:
    """创建警报事件处理器"""
    return AlertEventHandler()


# 导出的公共接口
__all__ = [
    "MetricsEventHandler",
    "LoggingEventHandler",
    "CacheInvalidationHandler",
    "NotificationEventHandler",
    "AnalyticsEventHandler",
    "AlertEventHandler",
    "register_default_handlers",
    "create_metrics_handler",
    "create_logging_handler",
    "create_cache_invalidation_handler",
    "create_notification_handler",
    "create_analytics_handler",
    "create_alert_handler",
]
