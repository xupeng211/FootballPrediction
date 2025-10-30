"""
适配器注册表
"""

from typing import Dict, Optional, List

from src.core.exceptions import AdapterError
from src.adapters.base import Adapter


class AdapterRegistry:
    """类文档字符串"""
    pass  # 添加pass语句
    """适配器注册表"""

    def __init__(self, factory=None):
    """函数文档字符串"""
    pass  # 添加pass语句
        self.factory = factory or self._create_default_factory()
        self.adapters: Dict[str, Adapter] = {}
        self.groups: Dict[str, List[Adapter]] = {}

    def _create_default_factory(self):
    """函数文档字符串"""
    pass  # 添加pass语句
        """创建默认工厂"""
        # 简单的工厂实现
        return type(
            "Factory",
            (),
            {"create_adapter": lambda self, cls, config=None: cls(config)},
        )()

    def register(
        self, name: str, adapter: Adapter, group: Optional[str] = None
    ):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
        """注册适配器"""
        self.adapters[name] = adapter
        if group:
            if group not in self.groups:
                self.groups[group] = []
            self.groups[group].append(adapter)

    def get_adapter(self, name: str) -> Adapter:
        """获取适配器"""
        if name not in self.adapters:
            raise AdapterError(f"Adapter '{name}' not found")
        return self.adapters[name]

    def get_group(self, group: str) -> List[Adapter]:
        """获取适配器组"""
        return self.groups.get(group, [])

    def list_adapters(self) -> List[str]:
        """列出所有适配器名称"""
        return list(self.adapters.keys())


# 全局注册表实例
_global_registry = AdapterRegistry()


def get_global_registry() -> AdapterRegistry:
    """获取全局注册表"""
    return _global_registry
