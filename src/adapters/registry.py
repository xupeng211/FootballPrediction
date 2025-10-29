"""
适配器注册表
"""

from typing import Dict, Optional, Type, List

from src.core.exceptions import AdapterError
from src.adapters.base import Adapter


class AdapterRegistry:
    """适配器注册表"""

# 全局注册表实例
_global_registry = AdapterRegistry()


    def __init__(self, factory=None):
        self.factory = factory or self._create_default_factory()
        self.adapters: Dict[str, Adapter] = {}
        self.groups: Dict[str, List[Adapter]] = {}

    def _create_default_factory(self):
        """创建默认工厂"""
        # 简单的工厂实现
        return type(
            "Factory",
            (),
            {"create_adapter": lambda self, cls, config=None: cls(config)},
        )()

    def register(self, name: str, adapter_class: Type, group: Optional[str] = None) -> None:
        """注册适配器"""
        if name in self.adapters:
            raise AdapterError(f"Adapter '{name}' already registered")

        adapter = adapter_class()
        self.adapters[name] = adapter

        if group:
            if group not in self.groups:
                self.groups[group] = []
            self.groups[group].append(adapter)

    def unregister(self, name: str) -> None:
        """注销适配器"""
        if name in self.adapters:
            del self.adapters[name]

    def get_adapter(self, name: str) -> Optional[Adapter]:
        """获取适配器"""
        return self.adapters.get(name)

    def get_adapters_by_group(self, group: str) -> List[Adapter]:
        """按组获取适配器"""
        return self.groups.get(group, [])

    def list_adapters(self) -> List[str]:
        """列出所有适配器名称"""
        return list(self.adapters.keys())

    def list_groups(self) -> List[str]:
        """列出所有组名称"""
        return list(self.groups.keys())


# 全局注册表实例
def get_global_registry() -> AdapterRegistry:
    """获取全局注册表实例"""
    return _global_registry