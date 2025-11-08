from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import uuid4

"""
基础领域事件
Base Domain Event

定义领域事件的基础结构.
Defines the base structure for domain events.
"""


class DomainEvent(ABC):
    """
    领域事件基类

    所有领域事件都应该继承此类.
    All domain events should inherit from this class.
    """

    def __init__(self, aggregate_id: int | None = None):
        """函数文档字符串"""
        # 添加pass语句
        """
        初始化领域事件

        Args:
            aggregate_id: 聚合根ID
        """
        self.event_id = str(uuid4())
        self.aggregate_id = aggregate_id
        self.occurred_at = datetime.utcnow()
        self.version = 1

    def to_dict(self) -> dict[str, Any]:
        """转换为字典"""
        return {
            "event_id": self.event_id,
            "event_type": self.__class__.__name__,
            "aggregate_id": self.aggregate_id,
            "occurred_at": self.occurred_at.isoformat(),
            "version": self.version,
            "data": self._get_event_data(),
        }

    @abstractmethod
    def _get_event_data(self) -> dict[str, Any]:
        """
        获取事件特定数据

        子类应该重写此方法来提供事件特定的数据.
        Subclasses should override this method to provide event-specific data.
        """
        return {}

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.event_id})"
