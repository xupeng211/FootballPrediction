"""
观察者模式基础实现
Observer Pattern Base Implementation
"""

from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any


class ObservableEventType(Enum):
    """可观察事件类型枚举"""

    SYSTEM_NOTIFICATION = "system_notification"
    METRICS_UPDATE = "metrics_update"
    ALERT_TRIGGERED = "alert_triggered"
    PERFORMANCE_UPDATE = "performance_update"
    PREDICTION_CREATED = "prediction_created"
    PREDICTION_EVALUATED = "prediction_evaluated"
    MATCH_FINISHED = "match_finished"
    HEALTH_CHECK = "health_check"
    ERROR_OCCURRED = "error_occurred"
    CUSTOM_EVENT = "custom_event"


class ObservableEvent:
    """可观察事件基类"""

    def __init__(self, event_type: str, data: dict[str, Any] | None = None):
        self.event_type = event_type
        self.data = data or {}
        self.timestamp = datetime.utcnow()
        self.event_id = f"{event_type}_{int(self.timestamp.timestamp())}"


class Observer(ABC):
    """观察者抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self.created_at = datetime.utcnow()

    @abstractmethod
    def update(self, subject: "Subject", data: Any | None = None) -> None:
        """接收通知的方法"""

    def __str__(self) -> str:
        return f"Observer({self.name})"


class Subject(ABC):
    """被观察者抽象基类"""

    def __init__(self, name: str):
        self.name = name
        self._observers: list[Observer] = []
        self._event_history: list[ObservableEvent] = []
        self.created_at = datetime.utcnow()

    def attach(self, observer: Observer) -> None:
        """添加观察者"""
        if observer not in self._observers:
            self._observers.append(observer)

    def detach(self, observer: Observer) -> None:
        """移除观察者"""
        if observer in self._observers:
            self._observers.remove(observer)

    def notify(self, data: Any | None = None) -> None:
        """通知所有观察者"""
        event = ObservableEvent(
            event_type=f"{self.name}_notification",
            data={"data": data, "subject": self.name},
        )
        self._event_history.append(event)

        for observer in self._observers:
            try:
                observer.update(self, data)
            except Exception:
                # 记录通知失败但不影响其他观察者
                pass

    def notify_event(self, event: ObservableEvent) -> None:
        """通知特定事件"""
        self._event_history.append(event)

        for observer in self._observers:
            try:
                observer.update(self, event)
            except Exception:
                pass

    def get_observers(self) -> list[Observer]:
        """获取所有观察者"""
        return self._observers.copy()

    def get_event_history(self) -> list[ObservableEvent]:
        """获取事件历史"""
        return self._event_history.copy()

    def clear_history(self) -> None:
        """清空事件历史"""
        self._event_history.clear()

    def __str__(self) -> str:
        return f"Subject({self.name}, {len(self._observers)} observers)"


class EventManager:
    """事件管理器"""

    def __init__(self):
        self._subjects: dict[str, Subject] = {}
        self._global_observers: list[Observer] = []

    def register_subject(self, subject: Subject) -> None:
        """注册被观察者"""
        self._subjects[subject.name] = subject

    def unregister_subject(self, subject_name: str) -> None:
        """注销被观察者"""
        if subject_name in self._subjects:
            del self._subjects[subject_name]

    def get_subject(self, name: str) -> Subject | None:
        """获取被观察者"""
        return self._subjects.get(name)

    def add_global_observer(self, observer: Observer) -> None:
        """添加全局观察者"""
        self._global_observers.append(observer)

    def remove_global_observer(self, observer: Observer) -> None:
        """移除全局观察者"""
        if observer in self._global_observers:
            self._global_observers.remove(observer)

    def broadcast_event(self, event: ObservableEvent) -> None:
        """广播事件到所有观察者"""
        for observer in self._global_observers:
            try:
                observer.update(None, event)
            except Exception:
                pass

    def get_all_subjects(self) -> dict[str, Subject]:
        """获取所有被观察者"""
        return self._subjects.copy()


# 导出的公共接口
__all__ = [
    "ObservableEventType",
    "ObservableEvent",
    "Observer",
    "Subject",
    "EventManager",
]
