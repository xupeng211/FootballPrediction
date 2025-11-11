"""
适配器注册表模块
BaseAdapter Registry Module

提供适配器的注册、查找和管理功能。
Provides adapter registration, lookup, and management functionality.
"""

# 导入基础类
from .base import BaseAdapter

# 尝试导入工厂，避免循环导入
try:
    from .factory_simple import get_global_factory
except ImportError:

    def get_global_factory():
        return None


class BaseAdapterError(Exception):
    """适配器错误"""

    pass


class BaseAdapterRegistry:
    """适配器注册表"""

    def __init__(self, factory=None):
        """初始化适配器注册表"""
        self.factory = factory or self._create_default_factory()
        self.adapters: dict[str, BaseAdapter] = {}
        self.groups: dict[str, list[BaseAdapter]] = {}

    def _create_default_factory(self):
        """创建默认工厂"""
        try:
            return get_global_factory()
        except ImportError:
            return None

    def register(
        self, name: str, adapter: BaseAdapter, group: str | None = None
    ) -> None:
        """注册适配器"""
        self.adapters[name] = adapter
        if group:
            if group not in self.groups:
                self.groups[group] = []
            self.groups[group].append(adapter)

    def get_adapter(self, name: str) -> BaseAdapter:
        """获取适配器"""
        if name not in self.adapters:
            raise BaseAdapterError(f"BaseAdapter '{name}' not found")
        return self.adapters[name]

    def get_group(self, group: str) -> list[BaseAdapter]:
        """获取适配器组"""
        return self.groups.get(group, [])


# 全局注册表实例
_global_registry = BaseAdapterRegistry()


def get_global_registry() -> BaseAdapterRegistry:
    """获取全局注册表"""
    return _global_registry


__all__ = [
    "BaseAdapterError",
    "BaseAdapterRegistry",
    "get_global_registry",
]
