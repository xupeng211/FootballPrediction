"""
事件总线实现
Event Bus Implementation

提供事件的发布、订阅和路由功能。
Provides event publishing, subscription, and routing functionality.
"""

import asyncio
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional, Type

from .base import Event, EventFilter, EventHandler

logger = logging.getLogger(__name__)


class EventBus:
    """事件总线

    负责事件的发布、订阅和分发。
    Responsible for event publishing, subscription, and distribution.
    """

    def __init__(self, max_workers: int = 10):
        """初始化事件总线

        Args:
            max_workers: 最大工作线程数
        """
        self._subscribers: Dict[str, List[EventHandler]] = defaultdict(list)
        self._filters: Dict[EventHandler, List[EventFilter]] = {}
        self._queues: Dict[str, asyncio.Queue] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._executor = ThreadPoolExecutor(max_workers=max_workers)
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        """启动事件总线"""
        async with self._lock:
            if self._running:
                return

            self._running = True
            logger.info("EventBus started")

            # 启动所有订阅的处理器
            for event_type, handlers in self._subscribers.items():
                for handler in handlers:
                    if not handler.is_subscribed_to(event_type):
                        queue: Any = asyncio.Queue()
                        self._queues[event_type] = queue
                        handler.add_subscription(event_type, queue)

                        task = asyncio.create_task(
                            self._run_handler(handler, event_type, queue)
                        )
                        self._tasks.append(task)

            # 启动所有处理器
            unique_handlers = set()
            for handlers in self._subscribers.values():
                unique_handlers.update(handlers)

            for handler in unique_handlers:
                await handler.start()

    async def stop(self) -> None:
        """停止事件总线"""
        async with self._lock:
            if not self._running:
                return

            self._running = False
            logger.info("Stopping EventBus...")

            # 取消所有任务
            for task in self._tasks:
                task.cancel()

            # 等待任务完成
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

            # 停止所有处理器
            unique_handlers = set()
            for handlers in self._subscribers.values():
                unique_handlers.update(handlers)

            for handler in unique_handlers:
                await handler.stop()

            # 清理资源
            self._executor.shutdown(wait=True)
            self._queues.clear()

            logger.info("EventBus stopped")

    async def subscribe(
        self,
        event_type: str,
        handler: EventHandler,
        filters: Optional[List[EventFilter]] = None,
    ) -> None:
        """订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理器
            filters: 事件过滤器列表
        """
        async with self._lock:
            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

                # 添加过滤器
                if filters:
                    self._filters[handler] = filters

                # 如果总线已经在运行，立即启动处理器
                if self._running and not handler.is_subscribed_to(event_type):
                    queue: Any = asyncio.Queue()
                    self._queues[event_type] = queue
                    handler.add_subscription(event_type, queue)

                    task = asyncio.create_task(
                        self._run_handler(handler, event_type, queue)
                    )
                    self._tasks.append(task)

                logger.info(f"Handler {handler.name} subscribed to {event_type}")

    async def unsubscribe(self, event_type: str, handler: EventHandler) -> None:
        """取消订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理器
        """
        async with self._lock:
            if handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)
                handler.remove_subscription(event_type)

                # 移除过滤器
                if handler in self._filters:
                    del self._filters[handler]

                logger.info(f"Handler {handler.name} unsubscribed from {event_type}")

    async def publish(self, event: Event) -> None:
        """发布事件

        Args:
            event: 要发布的事件
        """
        if not self._running:
            logger.warning(f"EventBus not running. Dropping event: {event}")
            return

        event_type = event.get_event_type()
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug(f"No handlers for event type: {event_type}")
            return

        logger.debug(f"Publishing event {event_type} to {len(handlers)} handlers")

        # 将事件放入队列
        queue = self._queues.get(event_type)
        if queue:
            await queue.put(event)

    async def publish_sync(self, event: Event) -> None:
        """同步发布事件（立即处理）

        Args:
            event: 要发布的事件
        """
        if not self._running:
            logger.warning(f"EventBus not running. Dropping event: {event}")
            return

        event_type = event.get_event_type()
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug(f"No handlers for event type: {event_type}")
            return

        logger.debug(
            f"Publishing event {event_type} synchronously to {len(handlers)} handlers"
        )

        # 立即处理事件
        tasks = []
        for handler in handlers:
            if self._should_handle(handler, event):
                task = asyncio.create_task(self._handle_event(handler, event))
                tasks.append(task)

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _run_handler(
        self, handler: EventHandler, event_type: str, queue: asyncio.Queue
    ) -> None:
        """运行事件处理器

        Args:
            handler: 事件处理器
            event_type: 事件类型
            queue: 事件队列
        """
        try:
            while self._running:
                try:
                    # 等待事件，设置超时以避免永久阻塞
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)

                    if event is None:  # 停止信号
                        break

                    # 检查过滤器
                    if self._should_handle(handler, event):
                        await self._handle_event(handler, event)

                    queue.task_done()

                except asyncio.TimeoutError:
                    # 超时继续，保持运行
                    continue
                except (
                    ValueError,
                    TypeError,
                    AttributeError,
                    KeyError,
                    RuntimeError,
                ) as e:
                    logger.error(f"Error in handler {handler.name}: {e}")

        except asyncio.CancelledError:
            logger.debug(f"Handler {handler.name} task cancelled")
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(f"Fatal error in handler {handler.name}: {e}")

    async def _handle_event(self, handler: EventHandler, event: Event) -> None:
        """处理单个事件

        Args:
            handler: 事件处理器
            event: 事件
        """
        try:
            # 在线程池中执行同步处理器
            if hasattr(handler.handle, "__self__"):
                # 检查是否是异步方法
                if asyncio.iscoroutinefunction(handler.handle):
                    await handler.handle(event)
                else:
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(self._executor, handler.handle, event)
            else:
                await handler.handle(event)

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(
                f"Handler {handler.name} failed to process event {event.get_event_type()}: {e}",
                exc_info=True,
            )

    def _should_handle(self, handler: EventHandler, event: Event) -> bool:
        """检查处理器是否应该处理事件

        Args:
            handler: 事件处理器
            event: 事件

        Returns:
            bool: 是否应该处理
        """
        # 检查处理器是否能处理此事件类型
        handled_events = handler.get_handled_events()
        if event.get_event_type() not in handled_events:
            return False

        # 应用过滤器
        filters = self._filters.get(handler, [])
        for filter_obj in filters:
            if not filter_obj.should_process(event):
                return False

        return True

    def get_subscribers_count(self, event_type: str) -> int:
        """获取事件类型的订阅者数量

        Args:
            event_type: 事件类型

        Returns:
            int: 订阅者数量
        """
        return len(self._subscribers.get(event_type, []))

    def get_all_event_types(self) -> List[str]:
        """获取所有已注册的事件类型

        Returns:
            List[str]: 事件类型列表
        """
        return list(self._subscribers.keys())

    async def clear(self) -> None:
        """清空所有订阅"""
        async with self._lock:
            self._subscribers.clear()
            self._filters.clear()
            logger.info("EventBus cleared")

    def get_stats(self) -> Dict[str, Any]:
        """获取事件总线统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "running": self._running,
            "event_types": len(self._subscribers),
            "total_subscribers": sum(
                len(handlers) for handlers in self._subscribers.values()
            ),
            "active_tasks": len(self._tasks),
            "event_types_list": list(self._subscribers.keys()),
        }


# 全局事件总线实例
_event_bus: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """获取全局事件总线实例

    Returns:
        EventBus: 事件总线实例
    """
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def start_event_bus() -> None:
    """启动全局事件总线"""
    bus = get_event_bus()
    await bus.start()


async def stop_event_bus() -> None:
    """停止全局事件总线"""
    global _event_bus
    if _event_bus:
        await _event_bus.stop()
        _event_bus = None


# 装饰器：自动注册事件处理器
def event_handler(event_types: List[str]):
    """事件处理器装饰器

    Args:
        event_types: 处理的事件类型列表
    """

    def decorator(cls: Type[EventHandler]) -> Type[EventHandler]:
        original_init = cls.__init__

        def __init__(self, *args, **kwargs):
            original_init(self, *args, **kwargs)
            # 自动订阅到事件总线
            bus = get_event_bus()
            for event_type in event_types:
                asyncio.create_task(bus.subscribe(event_type, self))

        cls.__init__ = __init__
        cls._handled_events = event_types

        # 重写get_handled_events方法
        def get_handled_events(self) -> list[str]:
            return event_types

        cls.get_handled_events = get_handled_events

        return cls

    return decorator
