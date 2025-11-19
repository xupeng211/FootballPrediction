from typing import Optional

"""Manager Base Module
管理器基础模块.

提供服务管理的基础类。
"""

from abc import ABC, abstractmethod


class BaseService(ABC):
    """基础服务抽象类."""

    def __init__(self, name: str = None):
        self.name = name or self.__class__.__name__
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化服务."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭服务."""
        pass

    @property
    def initialized(self) -> bool:
        """服务是否已初始化."""
        return self._initialized

    def __str__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"

    def __repr__(self) -> str:
        return self.__str__()


__all__ = [
    "BaseService",
]
