"""
适配器注册表
"""

from typing import Dict, Optional, List

try:
    from src.core.exceptions import AdapterError
    from src.adapters.base import Adapter
except ImportError:
    # Fallback classes
    class AdapterError(Exception):
        pass

    class Adapter:
        pass


class AdapterRegistry:
    """适配器注册表"""

    def __init__(self, factory=None):
        """初始化适配器注册表"""
        self.factory = factory or self._create_default_factory()
        self.adapters: Dict[str, Adapter] = {}
        self.groups: Dict[str, List[Adapter]] = {}

    def _create_default_factory(self):
        """创建默认工厂"""
        try:
            from src.adapters.factory_simple import get_global_factory
            return get_global_factory()
        except ImportError:
            return None

    def register(self, name: str, adapter: Adapter, group: Optional[str] = None):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
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

    def unregister(self, name: str):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
        """注销适配器"""
        if name in self.adapters:
            del self.adapters[name]

        # 从组中移除
        for group_name, adapters in self.groups.items():
            self.groups[group_name] = [a for a in adapters if name not in str(type(a))]

    def clear(self):  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解  # TODO: 添加返回类型注解
        """清空注册表"""
        self.adapters.clear()
        self.groups.clear()


# 全局注册表实例
def get_global_registry() -> AdapterRegistry:
    """获取全局注册表"""
    return _global_registry