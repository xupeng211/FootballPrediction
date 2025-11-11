"""
事件总线模块
Event Bus Module

提供领域事件的发布和订阅功能
Provides domain event publishing and subscription functionality.
"""

from typing import Dict, List, Callable, Any
from abc import ABC, abstractmethod
import asyncio
import logging
from dataclasses import dataclass

from .base import DomainEvent

logger = logging.getLogger(__name__)


class EventBus:
    """简单的事件总线实现"""

    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._middleware: List[Callable] = []

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """订阅事件"""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """取消订阅事件"""
        if event_type in self._handlers:
            try:
                self._handlers[event_type].remove(handler)
            except ValueError:
                pass

    def publish(self, event: DomainEvent) -> None:
        """发布事件"""
        event_type = event.get_event_type()
        handlers = self._handlers.get(event_type, [])

        # 执行中间件
        for middleware in self._middleware:
            middleware(event)

        # 执行处理器
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")

    async def publish_async(self, event: DomainEvent) -> None:
        """异步发布事件"""
        event_type = event.get_event_type()
        handlers = self._handlers.get(event_type, [])

        # 执行中间件
        for middleware in self._middleware:
            if asyncio.iscoroutinefunction(middleware):
                await middleware(event)
            else:
                middleware(event)

        # 执行处理器
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Event handler error for {event_type}: {e}")

    def add_middleware(self, middleware: Callable) -> None:
        """添加中间件"""
        self._middleware.append(middleware)


# 全局事件总线实例
event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取全局事件总线实例"""
    return event_bus


# 便捷函数
def subscribe(event_type: str, handler: Callable) -> None:
    """订阅事件的便捷函数"""
    event_bus.subscribe(event_type, handler)


def publish(event: DomainEvent) -> None:
    """发布事件的便捷函数"""
    event_bus.publish(event)


def publish_async(event: DomainEvent) -> None:
    """异步发布事件的便捷函数"""
    return event_bus.publish_async(event)


# 测试支持
@dataclass
class TestEvent(DomainEvent):
    """测试事件"""

    def get_event_type(self) -> str:
        return "test_event"


# 添加缺失的函数
def start_event_bus():
    """启动事件总线的便捷函数"""
    global event_bus
    if not event_bus:
        event_bus = EventBus()
    return event_bus


def stop_event_bus():
    """停止事件总线的便捷函数"""
    global event_bus
    if event_bus:
        event_bus._handlers.clear()
        event_bus._middleware.clear()
        logger.info("EventBus stopped")


# 导出的公共接口
__all__ = [
    "EventBus",
    "get_event_bus",
    "event_bus",
    "subscribe",
    "publish",
    "publish_async",
    "start_event_bus",
    "TestEvent"
]