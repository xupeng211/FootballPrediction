"""
足球预测系统基础服务模块

定义所有业务服务的基础抽象类。
"""

from abc import ABC, abstractmethod

from src.core import logger


class BaseService(ABC):
    """基础服务抽象类"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logger

    @abstractmethod
    async def initialize(self) -> bool:
        """服务初始化"""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """服务关闭"""
        pass
