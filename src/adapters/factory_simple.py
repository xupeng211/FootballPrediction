"""简单的适配器工厂实现
Simple BaseAdapter Factory Implementation.

提供轻量级的适配器创建和管理功能。
Provides lightweight adapter creation and management functionality.
"""

from typing import Any

# 导入基础类
from .base import BaseAdapter

# 尝试导入BaseAdapterError，如果失败则创建
try:
    from .registry import BaseAdapterError
except ImportError:

    class BaseAdapterError(Exception):
        """适配器错误."""

        pass


class BaseAdapterFactory:
    """适配器工厂类."""

    def __init__(self):
        """初始化工厂."""
        self.adapters: dict[str[BaseAdapter]] = {}
        self.singletons: dict[str, BaseAdapter] = {}

    def register_adapter(self, name: str, adapter_class: type[BaseAdapter]) -> None:
        """注册适配器类."""
        self.adapters[name] = adapter_class

    def create_adapter(
        self, name: str, config: dict[str, Any] | None = None, singleton: bool = True
    ) -> BaseAdapter:
        """创建适配器实例."""
        if name not in self.adapters:
            raise BaseAdapterError(f"BaseAdapter '{name}' not registered")

        if singleton and name in self.singletons:
            return self.singletons[name]

        adapter_class = self.adapters[name]
        adapter = adapter_class(config or {})

        if singleton:
            self.singletons[name] = adapter

        return adapter


class BaseAdapterNames:
    """预定义的适配器名称常量."""

    HTTP = "http"
    DATABASE = "database"
    CACHE = "cache"
    MESSAGE_QUEUE = "message_queue"
    FILE_STORAGE = "file_storage"


# 全局工厂实例
_global_factory = BaseAdapterFactory()


def get_adapter(
    name: str, config: dict[str, Any] | None = None, singleton: bool = True
) -> BaseAdapter:
    """获取适配器实例(便捷函数).

    Args:
        name: 适配器名称
        config: 配置参数
        singleton: 是否单例
    Returns:
        适配器实例
    """
    return _global_factory.create_adapter(name, config, singleton)


def get_global_factory() -> BaseAdapterFactory:
    """获取全局工厂实例."""
    return _global_factory


__all__ = [
    "BaseAdapterFactory",
    "BaseAdapterError",
    "BaseAdapterNames",
    "get_adapter",
    "get_global_factory",
]
