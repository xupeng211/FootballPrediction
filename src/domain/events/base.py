"""
基础领域事件
Base Domain Event

定义领域事件的基础结构.
Defines the base structure for domain events.
"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import uuid4

# 兼容性别名将在文件末尾定义


class EventData:
    """事件数据容器"""
    def __init__(self, data: dict[str, Any] | None = None):
        self.data = data or {}
        self.timestamp = datetime.utcnow()


class EventHandler(ABC):
    """事件处理器基类"""

    @abstractmethod
    async def handle(self, event: 'DomainEvent') -> None:
        """处理事件"""
        pass


class DomainEvent(ABC):
    """
    领域事件基类

    所有领域事件都应该继承此类.
    All domain events should inherit from this class.
    """

    @abstractmethod
    def get_event_type(self) -> str:
        """获取事件类型 - 子类必须实现"""
        pass

    def __init__(self, aggregate_id: int | None = None):
        """
        初始化领域事件

        Args:
            aggregate_id: 聚合根ID
        """
        self.id = str(uuid4())
        self.aggregate_id = aggregate_id
        self.timestamp = datetime.utcnow()
        self.data: dict[str, Any] = {}

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "type": self.get_event_type(),
            "aggregate_id": self.aggregate_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


# 兼容性别名 - 保持向后兼容
Event = DomainEvent

__all__ = ["Event", "DomainEvent", "EventData", "EventHandler"]
