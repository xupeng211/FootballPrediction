"""
事件系统基础类
Event System Base Classes

定义事件和事件处理器的核心接口。
Defines core interfaces for events and event handlers.
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar
import logging


T = TypeVar("T", bound="Event")


class EventData:
    """事件数据基类

    所有事件数据的基类，提供通用的元数据。
    Base class for all event data, providing common metadata.
    """

    def __init__(
        self,
        source: Optional[str] = None,
        version: str = "1.0",
        metadata: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None,
        timestamp: Optional[datetime] = None,
    ):
        """初始化事件数据"""
        self.event_id = event_id or str(uuid.uuid4())
        self.timestamp = timestamp or datetime.utcnow()
        self.source = source
        self.version = version
        self.metadata = metadata or {}


class Event(ABC):
    """事件抽象基类

    定义所有事件必须实现的接口。
    Defines the interface that all events must implement.
    """

    def __init__(self, data: EventData):  # type: ignore
        """初始化事件

        Args:
            data: 事件数据
        """
        self.data = data

    @property
    def data(self) -> EventData:
        """获取事件数据"""
        return self.data

    @property
    def event_id(self) -> str:
        """获取事件ID"""
        return self.data.event_id

    @property
    def timestamp(self) -> datetime:
        """获取事件时间戳"""
        return self.data.timestamp

    @property
    def source(self) -> Optional[str]:
        """获取事件源"""
        return self.data.source

    @property
    def version(self) -> str:
        """获取事件版本"""
        return self.data.version

    @property
    def metadata(self) -> Dict[str, Any]:
        """获取事件元数据"""
        return self.data.metadata

    @classmethod
    @abstractmethod
    def get_event_type(cls) -> str:
        """获取事件类型

        Returns:
            str: 事件类型标识符
        """
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """将事件转换为字典

        Returns:
            Dict[str, Any]: 事件的字典表示
        """
        pass

    @classmethod
    @abstractmethod
    def from_dict(cls: Type[T], data: Dict[str, Any]) -> T:
        """从字典创建事件

        Args:
            data: 事件字典数据

        Returns:
            T: 事件实例
        """
        pass

    def __str__(self) -> str:
        return f"{self.get_event_type()}(id={self.event_id}, ts={self.timestamp})"

    def __repr__(self) -> str:
        return self.__str__()


class EventHandler(ABC):
    """事件处理器抽象基类

    定义事件处理器必须实现的接口。
    Defines the interface that all event handlers must implement.
    """

    def __init__(self, name: Optional[str] = None):  # type: ignore
        """初始化事件处理器

        Args:
            name: 处理器名称
        """
        self.name = name or self.__class__.__name__
        self._subscribed_events: Dict[str, asyncio.Queue] = {}

    @abstractmethod
    async def handle(self, event: Event) -> None:
        """处理事件

        Args:
            event: 要处理的事件
        """
        pass

    @abstractmethod
    def get_handled_events(self) -> list[str]:
        """获取处理器能处理的事件类型

        Returns:
            list[str]: 事件类型列表
        """
        pass

    async def start(self) -> None:
        """启动处理器"""
        pass

    async def stop(self) -> None:
        """停止处理器"""
        # 清理订阅的队列
        for queue in self._subscribed_events.values():
            queue.put_nowait(None)
        self._subscribed_events.clear()

    def add_subscription(self, event_type: str, queue: asyncio.Queue) -> None:
        """添加事件订阅

        Args:
            event_type: 事件类型
            queue: 事件队列
        """
        self._subscribed_events[event_type] = queue

    def remove_subscription(self, event_type: str) -> None:
        """移除事件订阅

        Args:
            event_type: 事件类型
        """
        self._subscribed_events.pop(event_type, None)

    def is_subscribed_to(self, event_type: str) -> bool:
        """检查是否订阅了指定事件类型

        Args:
            event_type: 事件类型

        Returns:
            bool: 是否已订阅
        """
        return event_type in self._subscribed_events

    async def wait_for_events(self, event_type: str) -> None:
        """等待并处理特定类型的事件

        Args:
            event_type: 事件类型
        """
        queue = self._subscribed_events.get(event_type)
        if not queue:
            raise ValueError(f"Not subscribed to event type: {event_type}")

        while True:
            try:
                event = await queue.get()
                if event is None:  # 停止信号
                    break
                await self.handle(event)
                queue.task_done()
            except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
                # 处理错误但继续处理其他事件
                logger = logging.getLogger(__name__)
                logger.info(f"Error handling event {event_type}: {e}")


class EventFilter(ABC):
    """事件过滤器抽象基类

    用于过滤事件，决定是否应该处理某个事件。
    """

    @abstractmethod
    def should_process(self, event: Event) -> bool:
        """判断是否应该处理事件

        Args:
            event: 事件

        Returns:
            bool: 是否应该处理
        """
        pass


class EventTypeFilter(EventFilter):
    """基于事件类型的过滤器"""

    def __init__(self, allowed_types: list[str]):  # type: ignore
        """初始化过滤器

        Args:
            allowed_types: 允许的事件类型列表
        """
        self.allowed_types = set(allowed_types)

    def should_process(self, event: Event) -> bool:
        return event.get_event_type() in self.allowed_types


class EventSourceFilter(EventFilter):
    """基于事件源的过滤器"""

    def __init__(self, allowed_sources: list[str]):  # type: ignore
        """初始化过滤器

        Args:
            allowed_sources: 允许的事件源列表
        """
        self.allowed_sources = set(allowed_sources)

    def should_process(self, event: Event) -> bool:
        return event.source in self.allowed_sources if event.source else False


class CompositeEventFilter(EventFilter):
    """组合过滤器，支持AND和OR逻辑"""

    def __init__(self, filters: list[EventFilter], operator: str = "AND"):  # type: ignore
        """初始化组合过滤器

        Args:
            filters: 子过滤器列表
            operator: 逻辑操作符（"AND" 或 "OR"）
        """
        self.filters = filters
        self.operator = operator.upper()

        if self.operator not in ["AND", "OR"]:
            raise ValueError("Operator must be 'AND' or 'OR'")

    def should_process(self, event: Event) -> bool:
        if not self.filters:
            return True

        if self.operator == "AND":
            return all(f.should_process(event) for f in self.filters)
        else:  # OR
            return any(f.should_process(event) for f in self.filters)
