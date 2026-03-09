"""
BaseService - 服务基类
======================

V4.46.2: 占位实现，解决 API 启动导入错误

@module services.base_service
@version V4.46.2
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging


class BaseService(ABC):
    """
    服务基类

    所有业务服务应继承此类
    """

    def __init__(self, name: str = "BaseService"):
        self.name = name
        self.logger = logging.getLogger(f"services.{name}")
        self._initialized = False

    @abstractmethod
    async def initialize(self) -> None:
        """初始化服务"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """关闭服务"""
        pass

    def is_initialized(self) -> bool:
        """检查服务是否已初始化"""
        return self._initialized

    async def health_check(self) -> Dict[str, Any]:
        """健康检查"""
        return {
            "name": self.name,
            "status": "healthy" if self._initialized else "not_initialized",
        }


__all__ = ["BaseService"]
