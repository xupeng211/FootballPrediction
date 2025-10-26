"""
基础缓存类
Base Cache Classes
"""

from abc import ABC, abstractmethod
from typing import Any, List, Optional
import logging

class BaseCache(ABC):
    """缓存基础类"""

    def __init__(self):
        """初始化缓存"""
        self.logger = logging.getLogger(f"cache.{self.__class__.__name__}")
        self.cache_enabled = True

    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        pass

    @abstractmethod
    async def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """设置缓存值"""
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """删除缓存"""
        pass

    @abstractmethod
    async def clear(self) -> bool:
        """清空缓存"""
        pass

class CacheKeyManager:
    """缓存键管理器"""

    def __init__(self, prefix: str = "fp"):
        """初始化键管理器

        Args:
            prefix: 键前缀
        """
        self.prefix = prefix

    def make_key(self, *parts: str) -> str:
        """生成缓存键

        Args:
            *parts: 键的组成部分

        Returns:
            缓存键
        """
        return f"{self.prefix}:" + ":".join(parts)

    def parse_key(self, key: str) -> List[str]:
        """解析缓存键

        Args:
            key: 缓存键

        Returns:
            键的组成部分
        """
        return key.split(":")[1:]
