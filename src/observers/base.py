from typing import Any, Dict, List, Optional, Union
"""
观察者模式基础类
Observer Pattern Base Classes

定义观察者和被观察者的核心接口。
Defines core interfaces for observers and subjects.
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
import logging


T = TypeVar("T")


class ObservableEventType(Enum):
    """可观察事件类型"""

    METRIC_UPDATE = "metric_update"
    SYSTEM_ALERT = "system_alert"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    ERROR_OCCURRED = "error_occurred"
    PREDICTION_COMPLETED = "prediction_completed"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    THRESHOLD_EXCEEDED = "threshold_exceeded"


@dataclass
class ObservableEvent:
    """可观察的事件"""

    event_type: ObservableEventType
    timestamp: datetime = field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict[str, Any])
    severity: str = "info"  # info, warning, error, critical
    tags: Dict[str, str] = field(default_factory=dict[str, Any])

    def __str__(self) -> str:
        return f"{self.event_type.value}[{self.severity}]: {self.source}"


class Observer(ABC):
    """观察者抽象基类

    定义观察者必须实现的接口。
    Defines the interface that all observers must implement.
    """

    def __init__(self, name: str):
        """初始化观察者

        Args:
            name: 观察者名称
        """
        self.name = name
        self._enabled = True
        self._subscription_filters: List[Callable[[ObservableEvent], bool] = []

    @abstractmethod
    async def update(self, event: ObservableEvent) -> None:
        """接收并处理事件通知

        Args:
            event: 被通知的事件
        """
        pass

    @abstractmethod
    def get_observed_event_types(self) -> List[ObservableEventType]:
        """获取观察者感兴趣的事件类型

        Returns:
            List[ObservableEventType]: 事件类型列表
        """
        pass

    def add_filter(self, filter_func: Callable[[ObservableEvent], bool]) -> None:
        """添加事件过滤器

        Args:
            filter_func: 过滤函数，返回True表示需要处理此事件
        """
        self._subscription_filters.append(filter_func)

    def should_handle_event(self, event: ObservableEvent) -> bool:
        """判断是否应该处理事件

        Args:
            event: 事件

        Returns:
            bool: 是否应该处理
        """
        if not self._enabled:
            return False

        # 检查事件类型
        if event.event_type not in self.get_observed_event_types():
            return False

        # 应用过滤器
        for filter_func in self._subscription_filters:
            if not filter_func(event):
                return False

        return True

    def enable(self) -> None:
        """启用观察者"""
        self._enabled = True

    def disable(self) -> None:
        """禁用观察者"""
        self._enabled = False

    def is_enabled(self) -> bool:
        """检查观察者是否启用"""
        return self._enabled

    def get_stats(self) -> Dict[str, Any]:
        """获取观察者统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        return {
            "name": self.name,
            "enabled": self._enabled,
            "filters_count": len(self._subscription_filters),
        }


class Subject(ABC):
    """被观察者抽象基类

    定义被观察者必须实现的接口。
    Defines the interface that all subjects must implement.
    """

    def __init__(self, name: str):
        """初始化被观察者

        Args:
            name: 被观察者名称
        """
        self.name = name
        self._observers: List[Observer] = []
        self._event_history: List[ObservableEvent] = []
        self._max_history_size = 1000
        self._enabled = True

    async def attach(self, observer: Observer) -> None:
        """添加观察者

        Args:
            observer: 要添加的观察者
        """
        if observer not in self._observers:
            self._observers.append(observer)

    async def detach(self, observer: Observer) -> None:
        """移除观察者

        Args:
            observer: 要移除的观察者
        """
        if observer in self._observers:
            self._observers.remove(observer)

    async def notify(self, event: ObservableEvent) -> None:
        """通知所有观察者

        Args:
            event: 要通知的事件
        """
        if not self._enabled:
            return

        # 记录事件历史
        self._record_event(event)

        # 并发通知所有观察者
        tasks = []
        for observer in self._observers:
            if observer.should_handle_event(event):
                tasks.append(self._notify_observer(observer, event))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _notify_observer(
        self, observer: Observer, event: ObservableEvent
    ) -> None:
        """通知单个观察者

        Args:
            observer: 观察者
            event: 事件
        """
        try:
            await observer.update(event)
        except (ValueError, TypeError, AttributeError, KeyError, RuntimeError) as e:
            # 观察者处理失败不应影响其他观察者
            logger = logging.getLogger(__name__)
            logger.info(f"Observer {observer.name} failed to handle event: {e}")

    def _record_event(self, event: ObservableEvent) -> None:
        """记录事件到历史

        Args:
            event: 事件
        """
        self._event_history.append(event)
        # 限制历史记录大小
        if len(self._event_history) > self._max_history_size:
            self._event_history = self._event_history[-self._max_history_size :]

    def get_observers_count(self) -> int:
        """获取观察者数量

        Returns:
            int: 观察者数量
        """
        return len(self._observers)

    def get_observers(self) -> List[Observer]:
        """获取所有观察者

        Returns:
            List[Observer]: 观察者列表
        """
        return self._observers.copy()

    def get_event_history(
        self,
        event_type: Optional[ObservableEventType] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None,
    ) -> List[ObservableEvent]:
        """获取事件历史

        Args:
            event_type: 过滤事件类型
            since: 过滤起始时间
            limit: 返回数量限制

        Returns:
            List[ObservableEvent]: 事件列表
        """
        history = self._event_history

        # 过滤事件类型
        if event_type:
            history = [e for e in history if e.event_type == event_type]

        # 过滤时间
        if since:
            history = [e for e in history if e.timestamp >= since]

        # 限制数量
        if limit:
            history = history[-limit:]

        return history

    def clear_history(self) -> None:
        """清空事件历史"""
        self._event_history.clear()

    def enable(self) -> None:
        """启用通知"""
        self._enabled = True

    def disable(self) -> None:
        """禁用通知"""
        self._enabled = False

    def is_enabled(self) -> bool:
        """检查是否启用"""
        return self._enabled

    def get_stats(self) -> Dict[str, Any]:
        """获取被观察者统计信息

        Returns:
            Dict[str, Any]: 统计信息
        """
        event_counts = {}  # type: ignore
        for event in self._event_history:
            event_counts[event.event_type.value] = (
                event_counts.get(event.event_type.value, 0) + 1
            )

        return {
            "name": self.name,
            "observers_count": len(self._observers),
            "events_count": len(self._event_history),
            "enabled": self._enabled,
            "event_counts": event_counts,
        }


class CompositeObserver(Observer):
    """组合观察者

    可以将多个观察器组合成一个。
    Combines multiple observers into one.
    """

    def __init__(self, name: str, observers: List[Observer] = None):
        """初始化组合观察者

        Args:
            name: 观察者名称
            observers: 子观察者列表
        """
        super().__init__(name)
        self._observers = observers or []

    def add_observer(self, observer: Observer) -> None:
        """添加子观察者"""
        self._observers.append(observer)

    def remove_observer(self, observer: Observer) -> None:
        """移除子观察者"""
        if observer in self._observers:
            self._observers.remove(observer)

    async def update(self, event: ObservableEvent) -> None:
        """通知所有子观察者"""
        tasks = [observer.update(event) for observer in self._observers]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    def get_observed_event_types(self) -> List[ObservableEventType]:
        """合并所有子观察者的事件类型"""
        event_types = set()
        for observer in self._observers:
            event_types.update(observer.get_observed_event_types())
        return list(event_types)
