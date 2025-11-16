"""适配器模式基础类
Adapter Pattern Base Classes.

提供适配器模式的基础抽象类和接口。
Provides base abstract classes and interfaces for the adapter pattern.
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class AdapterStatus(Enum):
    """适配器状态枚举."""

    INACTIVE = "inactive"
    ACTIVE = "active"
    ERROR = "error"
    MAINTENANCE = "maintenance"


class Adaptee(ABC):
    """被适配者接口，需要被适配的现有接口."""

    @abstractmethod
    async def get_data(self, request: Any) -> Any:
        """获取原始数据."""
        pass

    @abstractmethod
    async def send_data(self, data: Any) -> bool:
        """发送数据."""
        pass


class Target(ABC):
    """目标接口，客户端期望的接口."""

    @abstractmethod
    async def request(self, data: Any) -> Any:
        """标准请求方法."""
        pass


class BaseAdapter(Adaptee, Target, ABC):
    """基础适配器抽象类."""

    def __init__(self, name: str, status: AdapterStatus = AdapterStatus.INACTIVE):
        self.name = name
        self.status = status
        self._error_count = 0
        self._last_error = None

    async def initialize(self) -> bool:
        """初始化适配器."""
        try:
            success = await self._do_initialize()
            if success:
                self.status = AdapterStatus.ACTIVE
            return success
        except Exception as e:
            self._set_error(e)
            return False

    async def cleanup(self) -> None:
        """清理适配器资源."""
        try:
            await self._do_cleanup()
            self.status = AdapterStatus.INACTIVE
        except Exception as e:
            self._set_error(e)

    @abstractmethod
    async def _do_initialize(self) -> bool:
        """子类实现具体的初始化逻辑."""
        pass

    @abstractmethod
    async def _do_cleanup(self) -> None:
        """子类实现具体的清理逻辑."""
        pass

    def _set_error(self, error: Exception) -> None:
        """设置错误状态."""
        self.status = AdapterStatus.ERROR
        self._last_error = error
        self._error_count += 1

    def get_error_info(self) -> dict:
        """获取错误信息."""
        return {
            "error_count": self._error_count,
            "last_error": str(self._last_error) if self._last_error else None,
            "status": self.status.value,
        }

    def is_healthy(self) -> bool:
        """检查适配器是否健康."""
        return self.status == AdapterStatus.ACTIVE and self._error_count < 5

    def reset_error_count(self) -> None:
        """重置错误计数."""
        self._error_count = 0
        if self.status == AdapterStatus.ERROR:
            self.status = AdapterStatus.INACTIVE


class AdapterError(Exception):
    """适配器异常基类."""

    pass


class AdapterInitializationError(AdapterError):
    """适配器初始化错误."""

    pass


class AdapterConnectionError(AdapterError):
    """适配器连接错误."""

    pass


class AdapterDataError(AdapterError):
    """适配器数据错误."""

    pass


__all__ = [
    "AdapterStatus",
    "Adaptee",
    "Target",
    "BaseAdapter",
    "AdapterError",
    "AdapterInitializationError",
    "AdapterConnectionError",
    "AdapterDataError",
]
