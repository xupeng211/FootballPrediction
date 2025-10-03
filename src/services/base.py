from abc import ABC, abstractmethod
import logging
import os

"""
足球预测系统基础服务模块

定义所有业务服务的基础抽象类。
"""

class BaseService:
    """基础服务类"""
    def __init__(self, name: str = os.getenv("BASE_STR_12")):
        self.name = name
        self.logger = logging.getLogger(name)
        self._running = True
    async def initialize(self) -> bool:
        """服务初始化"""
        return True
    async def shutdown(self) -> None:
        """服务关闭"""
        self._running = False
    def start(self) -> bool:
        """启动服务"""
        self._running = True
        return True
    def stop(self) -> bool:
        """停止服务"""
        self._running = False
        return True
    def get_status(self) -> str:
        """获取服务状态"""
        return "running" if self._running else "stopped"
class AbstractBaseService(ABC):
    """抽象基础服务类 - 供需要强制实现的服务继承"""
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
    @abstractmethod
    async def initialize(self) -> bool:
        """服务初始化"""
    @abstractmethod
    async def shutdown(self) -> None:
        """服务关闭"""