"""
足球预测系统基础服务类
"""

from src.core import logger


class BaseService:
    """足球预测系统基础服务类"""

    def __init__(self, name: str):
        self.name = name
        self.logger = logger

    async def initialize(self) -> bool:
        """服务初始化"""
        self.logger.info(f"正在初始化 {self.name}")
        return True

    async def shutdown(self) -> None:
        """服务关闭"""
        self.logger.info(f"正在关闭 {self.name}")
