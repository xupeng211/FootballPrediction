"""
事件总线实现
Event Bus Implementation

提供事件发布订阅机制
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any

logger = logging.getLogger(__name__)


class Event:
    """事件基类"""

    def __init__(self, event_type: str, data: dict | None = None):
        self.event_type = event_type
        self.data = data or {}
        self.timestamp = asyncio.get_event_loop().time()

    def get_event_type(self) -> str:
        return self.event_type


class EventHandler:
    """事件处理器基类"""

    def __init__(self, name: str):
        self.name = name
        self._subscribed_events: set[str] = set()

    async def handle(self, event: Event) -> None:
        """处理事件"""
        raise NotImplementedError

    def is_subscribed_to(self, event_type: str) -> bool:
        return event_type in self._subscribed_events

    def add_subscription(self, event_type: str, queue: Any) -> None:
        """添加订阅"""
        self._subscribed_events.add(event_type)


class EventBus:
    """事件总线"""

    def __init__(self):
        self._subscribers: dict[str, list[EventHandler]] = {}
        self._queues: dict[str, Any] = {}
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._lock = asyncio.Lock()
        self._filters: dict[EventHandler, dict] = {}
        self._executor = ThreadPoolExecutor(max_workers=10)

    async def start(self) -> None:
        """启动事件总线"""
        async with self._lock:
            if self._running:
                return None
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
                task = asyncio.create_task(self._run_handler_monitor(handler))
                self._tasks.append(task)

    async def stop(self) -> None:
        """停止事件总线"""
        async with self._lock:
            if not self._running:
                return None
            self._running = False

            # 取消所有任务
            for task in self._tasks:
                if not task.done():
                    task.cancel()

            # 等待任务完成
            if self._tasks:
                await asyncio.gather(*self._tasks, return_exceptions=True)

            self._tasks.clear()
            self._queues.clear()
            self._executor.shutdown(wait=True)
            logger.info("EventBus stopped")

    async def publish(self, event: Event) -> None:
        """发布事件"""
        if not self._running:
            logger.warning("EventBus is not running")
            return

        handlers = self._subscribers.get(event.get_event_type(), [])
        if not handlers:
            return

        # 将事件放入队列
        queue = self._queues.get(event.get_event_type())
        if queue:
            await queue.put(event)

    async def subscribe(self, event_type: str, handler: EventHandler, filters: dict | None = None) -> None:
        """订阅事件"""
        async with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []

            if handler not in self._subscribers[event_type]:
                self._subscribers[event_type].append(handler)

                # 添加过滤器
                if filters:
                    self._filters[handler] = filters

                # 如果总线已经在运行, 立即启动处理器
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
        """取消订阅事件"""
        async with self._lock:
            if event_type in self._subscribers and handler in self._subscribers[event_type]:
                self._subscribers[event_type].remove(handler)

                # 移除过滤器
                if handler in self._filters:
                    del self._filters[handler]

                logger.info(f"Handler {handler.name} unsubscribed from {event_type}")

    async def _run_handler(self, handler: EventHandler, event_type: str, queue: Any) -> None:
        """运行事件处理器"""
        while self._running:
            try:
                # 等待事件，设置超时
                event = await asyncio.wait_for(queue.get(), timeout=1.0)

                if self._should_handle(handler, event):
                    await self._handle_event(handler, event)

                queue.task_done()

            except TimeoutError:
                # 超时继续, 保持运行
                continue
            except (
                ValueError,
                TypeError,
                AttributeError,
                KeyError,
                RuntimeError,
            ) as e:
                logger.error(f"Error in handler {handler.name}: {e}", exc_info=True)
                continue
            except asyncio.CancelledError:
                break

    async def _run_handler_monitor(self, handler: EventHandler) -> None:
        """监控处理器状态"""
        while self._running:
            try:
                await asyncio.sleep(5.0)
                # 可以在这里添加健康检查逻辑
            except asyncio.CancelledError:
                break

    async def _handle_event(self, handler: EventHandler, event: Event) -> None:
        """处理事件"""
        try:
            # 检查是否需要在线程池中执行
            if hasattr(handler.handle, "_blocking"):
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(
                    self._executor, handler.handle, event
                )
            else:
                await handler.handle(event)

        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            logger.error(
                f"Handler {handler.name} failed to process event {event.get_event_type()}: {e}",
                exc_info=True,
            )

    def _should_handle(self, handler: EventHandler, event: Event) -> bool:
        """检查处理器是否应该处理事件"""
        # 检查过滤器
        if handler in self._filters:
            filters = self._filters[handler]
            for key, value in filters.items():
                if event.data.get(key) != value:
                    return False
        return True


# 全局事件总线实例
_event_bus: EventBus | None = None


def get_event_bus() -> EventBus:
    """获取事件总线实例"""
    global _event_bus
    if _event_bus is None:
        _event_bus = EventBus()
    return _event_bus


async def start_event_bus() -> None:
    """启动事件总线"""
    bus = get_event_bus()
    await bus.start()


async def stop_event_bus() -> None:
    """停止事件总线"""
    bus = get_event_bus()
    await bus.stop()
